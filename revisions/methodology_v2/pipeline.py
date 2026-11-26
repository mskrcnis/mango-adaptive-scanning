"""Development-only matched-subset experiment; never calls the v1 workflow."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from mango.data import load_development
from mango.models import PLSReference, observed_input, partial_predict, predict_rich
from mango.optics import channel_matrix, get_catalog
from mango.state import atomic_json, canonical_hash, digest
from mango.training import reachable_masks

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"
READ_PATHS = set()
GUARD_INSTALLED = False
FAMILIES = ("mlp_hybrid", "pls", "ridge")
CASES = [(season, bank, seed) for season in (1, 2, 3)
         for bank, seeds in (("swap_mid", (42, 7, 99)), ("uniform", (42,)))
         for seed in seeds]


def event(message):
    HERE.mkdir(parents=True, exist_ok=True)
    with (HERE / "RUN_STATUS.md").open("a") as stream:
        stream.write("\n- %s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S %z"), message))
    print(message, flush=True)


def install_guard():
    """Log data opens and deny external features, labels, and scored results."""
    global GUARD_INSTALLED
    if GUARD_INSTALLED:
        return
    def hook(name, args):
        if name != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            return
        parts = relative.parts
        if not parts or parts[0] not in ("data", "results"):
            return
        if ("sealed" in parts or "external" in path.name.lower()
                or (parts[0] == "results" and "checkpoints" not in parts)):
            raise PermissionError("Revision may not read external/v1 scored data: " + str(relative))
        READ_PATHS.add(str(relative))
    sys.addaudithook(hook)
    GUARD_INSTALLED = True


def protected_files():
    result = []
    for name in ("data", "results", "mango", "config", "docs", "figures", "manuscript", "tests"):
        result.extend(p for p in (ROOT / name).rglob("*") if p.is_file()
                      and "__pycache__" not in p.parts)
    result.extend(p for p in ROOT.iterdir() if p.is_file() and p.name != "RUN_STATUS.md")
    return sorted(result)


def preservation_snapshot():
    path = HERE / "v1_preservation.json"
    if not path.exists():
        hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected_files()}
        atomic_json(path, {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                           "sha256": hashes, "exclusion": "RUN_STATUS.md append-only; runtime caches"})
    return json.loads(path.read_text())


def verify_preservation():
    expected = json.loads((HERE / "v1_preservation.json").read_text())["sha256"]
    bad = [name for name, value in expected.items()
           if not (ROOT / name).exists() or digest(ROOT / name) != value]
    return {"files": len(expected), "changed_or_missing": bad, "passed": not bad}


def dependencies():
    names = ["pipeline.py", "stopping.py", "protocol.md"]
    core = ["mango/models.py", "mango/data.py", "mango/optics.py", "mango/training.py",
            "data/processed/development.csv", "data/processed/metadata.csv",
            "data/catalog/catalog.json", "data/manifest.json", "results/fold_assignments.json"]
    payload = {name: digest(HERE / name) for name in names}
    payload.update({name: digest(ROOT / name) for name in core})
    for p in sorted((ROOT / "data/catalog").rglob("*.csv")):
        payload[str(p.relative_to(ROOT))] = digest(p)
    for season, bank, seed in CASES:
        name = "results/checkpoints/model_season%d_%s_seed%d.joblib" % (season, bank, seed)
        payload[name] = digest(ROOT / name)
    return payload


def checkpoint(name, fingerprint, fn):
    target = OUT / "checkpoints" / (name + ".joblib")
    record = target.with_suffix(".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    if record.exists() and target.exists():
        old = json.loads(record.read_text())
        if (old.get("status") == "complete" and old.get("dependency") == fingerprint
                and old.get("sha256") == digest(target)):
            event("Reused " + name)
            return joblib.load(target)
    started = time.perf_counter()
    atomic_json(record, {"status": "running", "dependency": fingerprint})
    event("Started " + name)
    try:
        result = fn()
        temporary = target.with_suffix(".joblib.tmp")
        joblib.dump(result, temporary, compress=3)
        os.replace(str(temporary), str(target))
        atomic_json(record, {"status": "complete", "dependency": fingerprint,
                            "seconds": time.perf_counter() - started, "sha256": digest(target)})
        event("Completed %s in %.1fs" % (name, time.perf_counter() - started))
        return result
    except BaseException as exc:
        atomic_json(record, {"status": "failed", "dependency": fingerprint, "error": repr(exc)})
        event("FAILED " + name + ": " + repr(exc))
        raise


class SubsetRegressors:
    """One fold-local model per mask. No unobserved column enters predict."""
    def __init__(self, family, masks):
        if family not in ("pls", "ridge"):
            raise ValueError(family)
        self.family = family
        self.masks = np.asarray(masks, dtype=bool)
        if self.masks.ndim != 2 or not self.masks[-1].all():
            raise ValueError("Last mask must be the full bank")

    def fit(self, x, y):
        x, y = np.asarray(x), np.asarray(y)
        self.models = []
        for mask in self.masks:
            model = (PLSReference(min(6, int(mask.sum()))) if self.family == "pls"
                     else make_pipeline(StandardScaler(), Ridge(alpha=10.0)))
            self.models.append(model.fit(x[:, mask], y))
        return self

    def predict(self, x):
        x = np.asarray(x)
        return np.column_stack([model.predict(x[:, mask]).ravel()
                                for mask, model in zip(self.masks, self.models)])

    def predict_observed(self, values, mask):
        values, mask = np.atleast_2d(values), np.asarray(mask, dtype=bool)
        if mask.ndim == 1:
            mask = np.broadcast_to(mask, values.shape)
        if values.shape != mask.shape:
            raise ValueError("values/mask shape mismatch")
        lookup = {tuple(m): i for i, m in enumerate(self.masks)}
        out = np.empty(len(values))
        for m in np.unique(mask, axis=0):
            ids = np.flatnonzero(np.all(mask == m, axis=1))
            if not np.isfinite(values[ids][:, m]).all():
                raise ValueError("Observed values must be finite")
            out[ids] = self.models[lookup[tuple(m)]].predict(values[ids][:, m]).ravel()
        return out


def fixed_order(centers):
    centers = np.asarray(centers)
    if len(np.unique(centers)) != len(centers) or np.any(np.diff(centers) <= 0):
        raise ValueError("Distinct increasing centers required")
    order = [0, len(centers) - 1]
    while len(order) < len(centers):
        available = [j for j in range(len(centers)) if j not in order]
        order.append(min(available, key=lambda j: (
            -float(np.min(np.abs(centers[j] - centers[order]))), float(centers[j]), j)))
    return order


def path_indices(masks, order):
    lookup = {tuple(m): i for i, m in enumerate(masks)}
    result = []
    for depth in range(2, len(order) + 1):
        mask = np.zeros(len(order), dtype=bool)
        mask[order[:depth]] = True
        result.append(lookup[tuple(mask)])
    return np.asarray(result)


def endpoint_components(y, mlp7, pls7, pls8):
    errors = [np.abs(np.asarray(y) - np.asarray(p)) for p in (mlp7, pls7, pls8)]
    return {"total": errors[0] - errors[2], "estimator": errors[0] - errors[1],
            "measurement": errors[1] - errors[2]}


def validate_case(data, bundle, held):
    if set(data.seasons) != {1, 2, 3}:
        raise AssertionError("Only all three development seasons are permitted")
    mapping = {str(row): i for i, row in enumerate(data.row_ids)}
    fit = np.asarray([mapping[str(row)] for row in bundle["fit_row_ids"]])
    cal = np.asarray([mapping[str(row)] for row in bundle["calibration_row_ids"]])
    valid = np.flatnonzero(data.seasons == held)
    groups = [set(data.groups[ids]) for ids in (fit, cal, valid)]
    assert not any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3))
    design = np.setdiff1d(np.arange(len(data)), np.concatenate([fit, cal, valid]))
    assert not set(data.groups[design]) & set.union(*groups)
    assert np.array_equal(bundle["oof"]["groups"], data.groups[fit])
    assert np.allclose(bundle["oof"]["y"], data.y[fit], atol=1e-6, rtol=0)
    fold_ids = bundle["oof"]["fold_ids"]
    assert len(fold_ids) == len(fit) and set(fold_ids) == {0, 1, 2}
    for fold in bundle["oof"]["folds"]:
        target = fold_ids == fold["fold"]
        train_groups = set(data.groups[fit[~target]])
        target_groups = set(data.groups[fit[target]])
        assert not train_groups & target_groups
        assert train_groups == set(fold["fit_groups"])
        assert target_groups == set(fold["target_groups"])
    return fit, cal, valid


def observed_path(scaler, x, masks, indices):
    return np.stack([observed_input(scaler, x, np.broadcast_to(masks[j], x.shape))
                     for j in indices], axis=1)


def build_linear(data, channels, bundle, held, bank, dep):
    fit, cal, valid = validate_case(data, bundle, held)
    x = channels[:, bundle["bank_indices"]].astype(np.float32)
    y = data.y.astype(np.float32)
    masks = bundle["masks"]
    fold_ids = bundle["oof"]["fold_ids"]
    predictions = {family: {"train": np.empty((len(fit), len(masks)))}
                   for family in ("pls", "ridge")}
    full_models = {}
    provenance = []
    for fold in (0, 1, 2, "full"):
        tr = fit if fold == "full" else fit[fold_ids != fold]
        va = np.concatenate([cal, valid]) if fold == "full" else fit[fold_ids == fold]
        def fit_one():
            models = {family: SubsetRegressors(family, masks).fit(x[tr], y[tr])
                      for family in ("pls", "ridge")}
            return {"models": models, "predictions": {k: m.predict(x[va]) for k, m in models.items()},
                    "fit_row_ids": data.row_ids[tr], "target_row_ids": data.row_ids[va]}
        value = checkpoint("linear_s%d_%s_%s" % (held, bank, fold),
                           canonical_hash([dep, held, bank, fold]), fit_one)
        assert np.array_equal(value["fit_row_ids"], data.row_ids[tr])
        assert np.array_equal(value["target_row_ids"], data.row_ids[va])
        for family in ("pls", "ridge"):
            if fold == "full":
                predictions[family]["cal"] = value["predictions"][family][:len(cal)]
                predictions[family]["valid"] = value["predictions"][family][len(cal):]
                full_models[family] = value["models"][family]
            else:
                predictions[family]["train"][fold_ids == fold] = value["predictions"][family]
        provenance.append({"fold": fold, "fit_groups": sorted(set(data.groups[tr])),
                           "target_groups": sorted(set(data.groups[va])),
                           "fit_row_ids": data.row_ids[tr].tolist(),
                           "target_row_ids": data.row_ids[va].tolist()})
    # v1 saved OOF bank predictions are float32; this rerun retains float64.
    endpoint_difference = float(np.max(np.abs(predictions["pls"]["train"][:, -1]
                                             - bundle["oof"]["bank_predictions"])))
    assert endpoint_difference < 1e-5, endpoint_difference
    assert np.allclose(predictions["pls"]["valid"][:, -1],
                       bundle["bank_predictor"].predict(x[valid]), rtol=0, atol=1e-10)
    return {"predictions": predictions, "models": full_models, "provenance": provenance,
            "fit_row_ids": bundle["fit_row_ids"], "calibration_row_ids": bundle["calibration_row_ids"],
            "fold_ids": fold_ids, "bank_indices": bundle["bank_indices"],
            "oof_endpoint_max_float32_difference": endpoint_difference}


def build_case(data, channels, bundle, linear, held, bank, seed):
    from .stopping import fit_stopping, predict_probabilities
    fit, cal, valid = validate_case(data, bundle, held)
    for field in ("fit_row_ids", "calibration_row_ids", "bank_indices"):
        assert np.array_equal(linear[field], bundle[field]), "Seed-dependent " + field
    assert np.array_equal(linear["fold_ids"], bundle["oof"]["fold_ids"]), "Seed-dependent OOF folds"
    masks = bundle["masks"]
    x = channels[:, bundle["bank_indices"]].astype(np.float32)
    centers = [get_catalog()[j]["center_nm"] for j in bundle["bank_indices"]]
    order = fixed_order(centers)
    indices = path_indices(masks, order)
    splits = {"train": fit, "cal": cal, "valid": valid}
    record = {"held_season": held, "bank": bank, "seed": seed, "bank_indices": bundle["bank_indices"],
              "centers_nm": centers, "order": order, "path_indices": indices, "masks": masks,
              "split_groups": {k: sorted(set(data.groups[v])) for k, v in splits.items()},
              "data": {}, "families": {}}
    mlp = {"train": bundle["oof"]["partial_predictions"].astype(float).copy()}
    for split, ids in splits.items():
        if split != "train":
            mlp[split] = np.column_stack([
                partial_predict(bundle, x[ids], np.broadcast_to(mask, x[ids].shape))
                for mask in masks])
        # Exact common endpoint; old OOF predictions were rounded to float32.
        mlp[split][:, -1] = linear["predictions"]["pls"][split][:, -1]
        rich = (bundle["oof"]["rich_predictions"].astype(float) if split == "train"
                else predict_rich(bundle, data.X[ids].astype(np.float32)))
        record["data"][split] = {"row_ids": data.row_ids[ids], "groups": data.groups[ids],
                                  "y": data.y[ids], "rich": rich,
                                  "features": observed_path(bundle["scaler"], x[ids], masks, indices)}
    for family in FAMILIES:
        all_predictions = mlp if family == "mlp_hybrid" else linear["predictions"][family]
        paths = {k: v[:, indices] for k, v in all_predictions.items()}
        a, b = record["data"]["train"], record["data"]["cal"]
        stopping = fit_stopping(a["features"], paths["train"], paths["train"][:, -1],
                               a["rich"], a["y"], b["features"], paths["cal"],
                               paths["cal"][:, -1], b["rich"], b["y"],
                               train_groups=data.groups[fit], cal_groups=data.groups[cal], seed=seed)
        probabilities = {split: {objective: predict_probabilities(stopping, info["features"], objective)
                                for objective in ("two_reference", "single_reference")}
                         for split, info in record["data"].items() if split != "train"}
        record["families"][family] = {"all_predictions": all_predictions, "paths": paths,
                                      "stopping": stopping, "probabilities": probabilities}
    return record


def run_all(limit=None):
    OUT.mkdir(parents=True, exist_ok=True)
    preservation_snapshot()
    deps = dependencies()
    dependency = canonical_hash(deps)
    registration = {"dependencies": deps, "dependency": dependency, "cases": CASES,
                    "protocol": "protocol.md", "external_evaluation": False}
    lock = OUT / "registration.json"
    if lock.exists() and json.loads(lock.read_text())["dependency"] != dependency:
        archive = OUT / "attempts"
        archive.mkdir(exist_ok=True)
        (archive / ("registration_%d.json" % time.time())).write_bytes(lock.read_bytes())
    atomic_json(lock, registration)
    install_guard()
    torch.set_num_threads(2)
    cases = CASES if limit is None else CASES[:limit]
    with threadpool_limits(limits=2):
        data = load_development()
        channels = channel_matrix(data.X, data.wavelengths)
        assert len(data) == 10243 and set(data.seasons) == {1, 2, 3}
        linear_cache = {}
        for held, bank, seed in cases:
            bundle_path = ROOT / ("results/checkpoints/model_season%d_%s_seed%d.joblib" % (held, bank, seed))
            bundle = joblib.load(bundle_path)
            key = (held, bank)
            if key not in linear_cache:
                linear_cache[key] = build_linear(data, channels, bundle, held, bank, dependency)
            linear = linear_cache[key]
            checkpoint("case_s%d_%s_seed%d" % (held, bank, seed),
                       canonical_hash([dependency, held, bank, seed]),
                       lambda: build_case(data, channels, bundle, linear, held, bank, seed))
        atomic_json(OUT / "read_audit.json", {"allowed_data_paths_read": sorted(READ_PATHS),
                                            "external_access_denied": True, "seasons": [1, 2, 3]})
    event("All requested cases completed; reporting/verification are separate stages.")
    return len(cases)
