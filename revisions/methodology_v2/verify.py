"""Independent reconstruction of development-only revision artifacts.

No estimator is fitted. Metrics, first-stop rules, selection tie-breaks, and
signed decompositions are reconstructed independently of reporting/stopping.
Protected v1 files are read only for hashes; parsed research data are development
rows and development bundles.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import pipeline as p

KEYS = ["bank", "seed", "held_season", "family", "objective", "operating_point"]
CHECKS = []


def check(name, condition, detail=None):
    record = {"name": name, "passed": bool(condition)}
    if not condition and detail is not None:
        record["detail"] = str(detail)
    CHECKS.append(record)
    return bool(condition)


def close(name, actual, expected, atol=1e-8, rtol=1e-8):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    good = a.shape == b.shape and np.allclose(a, b, atol=atol, rtol=rtol, equal_nan=True)
    detail = "shape %s versus %s" % (a.shape, b.shape)
    if a.shape == b.shape and a.size:
        finite = np.isfinite(a) & np.isfinite(b)
        detail += "; max finite absolute difference %.12g" % (np.max(np.abs(a[finite] - b[finite])) if finite.any() else 0.)
    return check(name, good, detail)


def metric(y, prediction, pulses, bank, rich):
    y, prediction, pulses, bank, rich = [np.asarray(x) for x in (y, prediction, pulses, bank, rich)]
    error, absolute = prediction - y, np.abs(prediction - y)
    e_bank, e_rich = np.abs(y - bank), np.abs(y - rich)
    early = pulses < 8
    missed = early & (absolute - e_bank > .5)
    denominator = np.sum((y - y.mean()) ** 2)
    rmse, bank_rmse = np.sqrt(np.mean(error ** 2)), np.sqrt(np.mean(e_bank ** 2))
    return {"n": len(y), "rmsep": rmse, "mae": absolute.mean(), "bias": error.mean(),
            "r2": 1 - np.sum(error ** 2) / denominator if denominator else np.nan,
            "bank_rmsep": bank_rmse, "rmsep_increase_vs_bank": rmse - bank_rmse,
            "mean_pulses": pulses.mean(), "median_pulses": np.median(pulses),
            "p95_pulses": np.percentile(pulses, 95), "early_n": int(early.sum()),
            "early_fraction": early.mean(), "missed_n": int(missed.sum()),
            "missed_rate": missed.sum() / early.sum() if early.any() else np.nan,
            "missed_unconditional": missed.mean(), "bank_loss_n": int((e_bank - e_rich > .5).sum()),
            "bank_loss_rate": (e_bank - e_rich > .5).mean(),
            "large_absolute_error_n": int((absolute > 2).sum()),
            "large_absolute_error_rate": (absolute > 2).mean()}


def apply(path, probability, threshold):
    decisions = np.column_stack([probability[:, :-1] <= threshold, np.ones(len(path), dtype=bool)])
    index = decisions.argmax(axis=1)
    return path[np.arange(len(path)), index], index + 2, index


def visited(probability, labels, index):
    keep = np.arange(6)[None, :] <= index[:, None]
    q, z = probability[:, :-1][keep], labels[keep]
    return {"visited_states": int(keep.sum()), "visited_positive_n": int(z.sum()),
            "visited_brier": np.mean((q - z) ** 2), "visited_observed_fraction": z.mean(),
            "visited_mean_probability": q.mean()}


def compare_mapping(name, actual, expected):
    for key, value in expected.items():
        if key not in actual:
            check(name + "/" + key, False, "missing key")
        else:
            close(name + "/" + key, np.nan if actual[key] is None else actual[key], value)


def _metadata(name, dependency):
    path = p.OUT / "checkpoints" / (name + ".joblib")
    meta = json.loads(path.with_suffix(".json").read_text())
    check(name + "/complete", meta.get("status") == "complete")
    check(name + "/dependency", meta.get("dependency") == dependency)
    check(name + "/sha256", meta.get("sha256") == p.digest(path))
    return joblib.load(path)


def _order(centers):
    order = [0, len(centers) - 1]
    while len(order) < len(centers):
        ranked = [(min(abs(centers[j] - centers[k]) for k in order), -centers[j], -j, j)
                  for j in range(len(centers)) if j not in order]
        order.append(max(ranked)[-1])
    return order


def _selections(rows):
    scientific = sorted(rows, key=lambda r: (abs(r["mean_pulses"] - 4), r["rmsep"], r["threshold"]))[0]
    feasible = [r for r in rows if r["mean_pulses"] <= 6 + 1e-12 and r["rmsep_increase_vs_bank"] <= .25 + 1e-12]
    if feasible:
        engineering = sorted(feasible, key=lambda r: (r["mean_pulses"], r["rmsep"], r["threshold"]))[0]
    else:
        def rank(r):
            violations = [max(0., r["mean_pulses"] / 6 - 1), max(0., r["rmsep_increase_vs_bank"] / .25 - 1)]
            return (max(violations), sum(violations), r["rmsep"], r["mean_pulses"], r["threshold"])
        engineering = min(rows, key=rank)
    return {"scientific": scientific, "engineering": engineering}, bool(feasible)


def paired_direct(groups, y, prediction_a, prediction_b, pulses_a=None, pulses_b=None):
    """Independent bootstrap by expanding sampled populations to actual rows."""
    unique = np.unique(groups)
    members = [np.flatnonzero(groups == group) for group in unique]
    result = {"n_groups": len(unique),
              "delta_rmsep": np.sqrt(np.mean((prediction_a - y) ** 2)) - np.sqrt(np.mean((prediction_b - y) ** 2))}
    if pulses_a is not None:
        result["delta_pulses"] = np.mean(pulses_a - pulses_b)
        result["budget_comparable"] = abs(result["delta_pulses"]) <= .25
    rng = np.random.RandomState(42)
    samples, pulses = [], []
    for _ in range(1000):
        selected = np.concatenate([members[j] for j in rng.choice(len(unique), len(unique), replace=True)])
        a, b, target = prediction_a[selected], prediction_b[selected], y[selected]
        samples.append(np.sqrt(np.mean((a - target) ** 2)) - np.sqrt(np.mean((b - target) ** 2)))
        if pulses_a is not None:
            pulses.append(np.mean(pulses_a[selected] - pulses_b[selected]))
    result["rmsep_ci_low"], result["rmsep_ci_high"] = np.quantile(samples, [.025, .975])
    if pulses_a is not None:
        result["pulses_ci_low"], result["pulses_ci_high"] = np.quantile(pulses, [.025, .975])
    return result


def _preservation():
    code = "import json; from revisions.methodology_v2.pipeline import verify_preservation; print(json.dumps(verify_preservation()))"
    run = subprocess.run([sys.executable, "-c", code], cwd=str(p.ROOT), text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    result = json.loads(run.stdout)
    check("v1_preservation/unchanged", result["passed"], result.get("changed_or_missing"))
    before = json.loads((p.HERE / "v1_preservation.json").read_text())["sha256"]
    current = {str(path.relative_to(p.ROOT)) for path in p.protected_files()}
    additions = sorted(current - set(before))
    check("v1_preservation/no_new_protected_files", not additions, additions)
    return result


def _read_guard():
    code = """import json
from revisions.methodology_v2.pipeline import install_guard
install_guard()
answer={}
for name in ['data/sealed/external_labels.csv','data/processed/external_features.csv','results/external_metrics.csv']:
    try:
        with open(name,'rb') as stream:
            raise RuntimeError('An excluded file was opened')
    except PermissionError:
        answer[name]=True
print(json.dumps(answer))
"""
    run = subprocess.run([sys.executable, "-c", code], cwd=str(p.ROOT), text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    denied = json.loads(run.stdout)
    check("scope/three_excluded_open_attempts_denied", len(denied) == 3 and all(denied.values()))
    audit = json.loads((p.OUT / "read_audit.json").read_text())
    paths = audit["allowed_data_paths_read"]
    check("scope/read_audit_development_only", audit["seasons"] == [1, 2, 3] and
          all("external" not in x.lower() and "sealed" not in Path(x).parts and
              (x.startswith("data/") or x.startswith("results/checkpoints/model_season")) for x in paths))


def _case_checks(case, source, frame, assignments, linear, tag):
    held = case["held_season"]
    masks, order, indices = np.asarray(case["masks"], bool), case["order"], case["path_indices"]
    check(tag + "/masks_unique_complete", masks.shape == (64, 8) and len({tuple(x) for x in masks}) == 64
          and masks[:, [0, 7]].all() and masks[-1].all())
    close(tag + "/masks_depth_counts", [(masks.sum(1) == d).sum() for d in range(2, 9)], [1, 6, 15, 20, 15, 6, 1], atol=0, rtol=0)
    check(tag + "/order_catalog_only", order == _order(case["centers_nm"]))
    for depth, column in enumerate(indices, 2):
        check(tag + "/path_mask_%d" % depth, set(np.flatnonzero(masks[column])) == set(order[:depth]))
    groups = []
    role_keys = {"train": "fit_row_ids", "cal": "calibration_row_ids", "valid": "validation_row_ids"}
    for split, key in role_keys.items():
        info = case["data"][split]
        ids = list(info["row_ids"])
        check(tag + "/" + split + "/row_order", ids == assignments[key])
        check(tag + "/" + split + "/row_ids_unique", len(set(ids)) == len(ids))
        close(tag + "/" + split + "/assay_alignment", info["y"], frame.loc[ids, "DM"].to_numpy())
        check(tag + "/" + split + "/group_alignment", list(info["groups"]) == frame.loc[ids, "group"].tolist())
        groups.append(set(info["groups"]))
        check(tag + "/" + split + "/recorded_groups", set(info["groups"]) == set(case["split_groups"][split]))
        check(tag + "/" + split + "/features_shape", info["features"].shape == (len(ids), 7, 16))
        for depth, column in enumerate(indices):
            expected_mask = np.broadcast_to(masks[column], (len(ids), 8))
            close(tag + "/" + split + "/mask_features_%d" % depth, info["features"][:, depth, 8:], expected_mask, atol=0, rtol=0)
            unread = info["features"][:, depth, :8][~expected_mask]
            close(tag + "/" + split + "/unread_features_zero_%d" % depth, unread, np.zeros_like(unread), atol=0, rtol=0)
    design = set(frame.loc[assignments["bank_design_row_ids"], "group"])
    groups.append(design)
    check(tag + "/four_roles_group_disjoint", all(not groups[i] & groups[j] for i in range(4) for j in range(i + 1, 4)))
    check(tag + "/development_partition_complete", set.union(*groups) == set(frame.group))
    check(tag + "/held_season_exact", set(frame.loc[case["data"]["valid"]["row_ids"], "season"]) == {held})
    oof = source["oof"]
    check(tag + "/source_fit_row_order", list(source["fit_row_ids"]) == assignments["fit_row_ids"])
    check(tag + "/source_oof_group_alignment", np.array_equal(oof["groups"], case["data"]["train"]["groups"]))
    check(tag + "/source_fold_ids", set(oof["fold_ids"]) == {0, 1, 2})
    for fold in oof["folds"]:
        targets = oof["fold_ids"] == fold["fold"]
        actual_train, actual_target = set(oof["groups"][~targets]), set(oof["groups"][targets])
        check(tag + "/source_fold_%d_groups" % fold["fold"], not actual_train & actual_target and
              actual_train == set(fold["fit_groups"]) and actual_target == set(fold["target_groups"]))
    for fold, item in linear.items():
        selected = np.ones(len(oof["fold_ids"]), bool) if fold == "full" else oof["fold_ids"] != fold
        expected_fit = np.asarray(assignments["fit_row_ids"])[selected]
        expected_target = np.r_[assignments["calibration_row_ids"], assignments["validation_row_ids"]] if fold == "full" else np.asarray(assignments["fit_row_ids"])[~selected]
        check(tag + "/linear_%s/fit_ids" % fold, np.array_equal(item["fit_row_ids"], expected_fit))
        check(tag + "/linear_%s/target_ids" % fold, np.array_equal(item["target_row_ids"], expected_target))
        check(tag + "/linear_%s/group_disjoint" % fold,
              not set(frame.loc[item["fit_row_ids"], "group"]) & set(frame.loc[item["target_row_ids"], "group"]))
        for family in ("pls", "ridge"):
            stored = item["predictions"][family]
            if fold == "full":
                expected = np.concatenate([case["families"][family]["all_predictions"][s] for s in ("cal", "valid")])
            else:
                expected = case["families"][family]["all_predictions"]["train"][~selected]
            close(tag + "/linear_%s/%s_prediction_assignment" % (fold, family), stored, expected, atol=0, rtol=0)
    for split in ("train", "cal", "valid"):
        hybrid = case["families"]["mlp_hybrid"]["all_predictions"][split]
        pls = case["families"]["pls"]["all_predictions"][split]
        close(tag + "/" + split + "/hybrid_pls_endpoint", hybrid[:, -1], pls[:, -1], atol=0, rtol=0)
        for family in p.FAMILIES:
            value = case["families"][family]
            check(tag + "/" + split + "/" + family + "/all_finite", np.isfinite(value["all_predictions"][split]).all())
            close(tag + "/" + split + "/" + family + "/path_columns", value["paths"][split], value["all_predictions"][split][:, indices], atol=0, rtol=0)
    close(tag + "/source_oof_pls_endpoint", case["families"]["pls"]["paths"]["train"][:, -1], oof["bank_predictions"], atol=1e-5, rtol=0)
    close(tag + "/source_oof_mlp_nonterminal", case["families"]["mlp_hybrid"]["all_predictions"]["train"][:, :-1], oof["partial_predictions"][:, :-1], atol=0, rtol=0)


def _stopping_checks(case, family, tag):
    value = case["families"][family]
    bundle = value["stopping"]
    check(tag + "/equal_scan_weighted_six_states", bundle["config"]["equal_scan_weights"] and bundle["config"]["nonterminal_depths"] == list(range(2, 8)))
    close(tag + "/threshold_grid", bundle["threshold_grid"], np.linspace(0, 1, 21), atol=0, rtol=0)
    expected_policies = {}
    for objective in ("two_reference", "single_reference"):
        for split in ("train", "cal", "valid"):
            info, path = case["data"][split], value["paths"][split]
            reference = path[:, -1] if objective == "two_reference" else info["rich"]
            labels = np.abs(info["y"][:, None] - path[:, :-1]) - np.abs(info["y"] - reference)[:, None] > .5
            if split == "train":
                compare_mapping(tag + "/" + objective + "/train_labels", bundle["fit_diagnostics"][objective],
                                {"scans": len(labels), "states": labels.size, "positive_n": labels.sum(), "positive_fraction": labels.mean()})
                continue
            features = info["features"][:, :-1].reshape(-1, bundle["feature_count"])
            raw = bundle["models"][objective].predict_proba(features)[:, 1]
            probability = np.column_stack([bundle["calibrators"][objective].predict(raw).reshape(len(labels), 6), np.zeros(len(labels))])
            close(tag + "/" + objective + "/" + split + "/probability_replay", value["probabilities"][split][objective], probability, atol=1e-12, rtol=1e-12)
            check(tag + "/" + objective + "/" + split + "/probability_range", np.isfinite(probability).all() and probability.min() >= 0 and probability.max() <= 1)
            if split == "cal":
                compare_mapping(tag + "/" + objective + "/calibration_diagnostics", bundle["calibration_diagnostics"][objective],
                                {"scans": len(labels), "states": labels.size, "positive_n": labels.sum(),
                                 "raw_brier": np.mean((raw.reshape(labels.shape) - labels) ** 2),
                                 "calibrated_brier": np.mean((probability[:, :-1] - labels) ** 2)})
                rows = []
                for index, threshold in enumerate(np.linspace(0, 1, 21)):
                    prediction, pulses, chosen = apply(path, probability, threshold)
                    row = dict(metric(info["y"], prediction, pulses, path[:, -1], info["rich"]),
                               **visited(probability, labels, chosen), threshold_index=index, threshold=threshold)
                    compare_mapping(tag + "/" + objective + "/calibration_curve_%d" % index,
                                    bundle["calibration_frontier"][objective][index], row)
                    rows.append(row)
                selected, feasible = _selections(rows)
                for point, row in selected.items():
                    compare_mapping(tag + "/" + objective + "/selection_" + point, bundle["selections"][objective][point], row)
                check(tag + "/" + objective + "/engineering_feasibility", bundle["selections"][objective]["engineering"]["feasible"] == feasible)
            else:
                for point in ("scientific", "engineering"):
                    threshold = bundle["selections"][objective][point]["threshold"]
                    prediction, pulses, chosen = apply(path, probability, threshold)
                    stats = dict(metric(info["y"], prediction, pulses, path[:, -1], info["rich"]), **visited(probability, labels, chosen))
                    expected_policies[(objective, point)] = (prediction, pulses, stats)
    info, path = case["data"]["valid"], value["paths"]["valid"]
    for depth in range(2, 9):
        prediction, pulses = path[:, depth - 2], np.full(len(path), depth)
        expected_policies[("fixed_length", "depth_%d" % depth)] = (prediction, pulses, metric(info["y"], prediction, pulses, path[:, -1], info["rich"]))
    return expected_policies


def verify():
    CHECKS.clear()
    preservation = _preservation()
    registration = json.loads((p.OUT / "registration.json").read_text())
    dependencies = registration["dependencies"]
    check("registration/self_hash", registration["dependency"] == p.canonical_hash(dependencies))
    current = p.dependencies()
    check("registration/current_dependencies", dependencies == current,
          [key for key in set(dependencies) | set(current) if dependencies.get(key) != current.get(key)])
    check("registration/expected_cases", registration["cases"] == [list(x) for x in p.CASES])
    check("registration/no_external_evaluation", registration["external_evaluation"] is False)
    _read_guard()
    frame = pd.read_csv(p.ROOT / "data/processed/development.csv", float_precision="round_trip").set_index("row_id")
    check("data/development_only", len(frame) == 10243 and frame.index.is_unique and set(frame.season) == {1, 2, 3} and frame.group.nunique() == 94)
    assignments = {f["held_season"]: f for f in json.loads((p.ROOT / "results/fold_assignments.json").read_text())}
    predictor = pd.read_csv(p.OUT / "predictor_metrics.csv", float_precision="round_trip")
    metrics = pd.read_csv(p.OUT / "policy_metrics.csv", float_precision="round_trip")
    pred_path = p.OUT / "policy_predictions.csv.gz"
    if not pred_path.exists():
        pred_path = p.OUT / "policy_predictions.csv"
    predictions = pd.read_csv(pred_path, float_precision="round_trip")
    endpoints = pd.read_csv(p.OUT / "endpoint_rows.csv", float_precision="round_trip")
    curves = pd.read_csv(p.OUT / "threshold_curves.csv", float_precision="round_trip")
    comparisons = pd.read_csv(p.OUT / "paired_comparisons.csv", float_precision="round_trip")
    check("exports/policy_metric_unique_keys", not metrics.duplicated(KEYS).any())
    check("exports/policy_prediction_unique_keys", not predictions.duplicated(KEYS + ["row_id"]).any())
    check("exports/predictor_unique_keys", not predictor.duplicated(["bank", "seed", "held_season", "split", "family", "depth", "scope"]).any())
    check("exports/endpoint_unique_keys", not endpoints.duplicated(["bank", "seed", "held_season", "row_id"]).any())
    check("exports/policy_metric_count", len(metrics) == 12 * 3 * 11)
    check("exports/policy_prediction_count", len(predictions) == len(frame) * 4 * 3 * 11)
    check("exports/endpoint_count", len(endpoints) == len(frame) * 4)
    pm_groups = {key: g for key, g in metrics.groupby(KEYS)}
    pp_groups = {key: g for key, g in predictions.groupby(KEYS)}
    ep_groups = {key: g for key, g in endpoints.groupby(["bank", "seed", "held_season"])}
    pr_groups = {key: g for key, g in predictor.groupby(["bank", "seed", "held_season", "split", "family", "depth", "scope"])}
    curve_keys = ["bank", "seed", "held_season", "family", "objective", "split", "threshold_index"]
    comparison_keys = ["bank", "seed", "held_season", "family", "comparison", "operating_point"]
    check("exports/curve_unique_keys", not curves.duplicated(curve_keys).any())
    check("exports/comparison_unique_keys", not comparisons.duplicated(comparison_keys).any())
    curve_groups = {key: g for key, g in curves.groupby(curve_keys)}
    comparison_groups = {key: g for key, g in comparisons.groupby(comparison_keys)}
    seen_predictor = set()
    case_summaries = []
    for held, bank, seed in p.CASES:
        tag = "s%d_%s_seed%d" % (held, bank, seed)
        case = _metadata("case_" + tag, p.canonical_hash([registration["dependency"], held, bank, seed]))
        source_path = p.ROOT / ("results/checkpoints/model_season%d_%s_seed%d.joblib" % (held, bank, seed))
        source_metadata = json.loads(source_path.with_suffix(".json").read_text())
        check(tag + "/source_checksum", source_metadata["sha256"] == p.digest(source_path) == dependencies[str(source_path.relative_to(p.ROOT))])
        source = joblib.load(source_path)
        linear = {fold: _metadata("linear_s%d_%s_%s" % (held, bank, fold),
                                 p.canonical_hash([registration["dependency"], held, bank, fold])) for fold in (0, 1, 2, "full")}
        _case_checks(case, source, frame, assignments[held], linear, tag)
        info = case["data"]["valid"]
        endpoint = ep_groups.get((bank, seed, held))
        if check(tag + "/endpoint_export_present", endpoint is not None):
            endpoint = endpoint.set_index("row_id").loc[info["row_ids"]]
            errors = [np.abs(info["y"] - case["families"][family]["paths"]["valid"][:, index])
                      for family, index in [("mlp_hybrid", -2), ("pls", -2), ("pls", -1)]]
            for column, value in [("total", errors[0] - errors[2]), ("estimator", errors[0] - errors[1]), ("measurement", errors[1] - errors[2])]:
                close(tag + "/endpoint_" + column, endpoint[column], value)
            close(tag + "/signed_decomposition", endpoint.total, endpoint.estimator + endpoint.measurement)
            check(tag + "/endpoint_groups", endpoint.group.tolist() == list(info["groups"]))
        for family in p.FAMILIES:
            ftag = tag + "/" + family
            expected_policies = _stopping_checks(case, family, ftag)
            if bank == "swap_mid" and seed == 42:
                path = case["families"][family]["paths"]["valid"]
                for objective in ("two_reference", "single_reference"):
                    probability = case["families"][family]["probabilities"]["valid"][objective]
                    reference = path[:, -1] if objective == "two_reference" else info["rich"]
                    labels = np.abs(info["y"][:, None] - path[:, :-1]) - np.abs(info["y"] - reference)[:, None] > .5
                    for index, threshold in enumerate(np.linspace(0, 1, 21)):
                        prediction, pulses, selected = apply(path, probability, threshold)
                        wanted = dict(metric(info["y"], prediction, pulses, path[:, -1], info["rich"]),
                                      **visited(probability, labels, selected), threshold=threshold, threshold_index=index)
                        record = curve_groups.get((bank, seed, held, family, objective, "valid", index))
                        ctag = ftag + "/exported_valid_curve/" + objective + "/%d" % index
                        if check(ctag + "/present", record is not None and len(record) == 1):
                            compare_mapping(ctag, record.iloc[0].to_dict(), wanted)
                if family in ("pls", "ridge"):
                    actual = comparison_groups[(bank, seed, held, family, "predictor_minus_mlp", "depth_4")].iloc[0].to_dict()
                    wanted = paired_direct(info["groups"], info["y"], path[:, 2],
                                           case["families"]["mlp_hybrid"]["paths"]["valid"][:, 2])
                    compare_mapping(ftag + "/paired_bootstrap/predictor_depth4", actual, wanted)
                if family == "pls":
                    a = expected_policies[("two_reference", "scientific")]
                    b = expected_policies[("single_reference", "scientific")]
                    wanted = paired_direct(info["groups"], info["y"], a[0], b[0], a[1], b[1])
                    actual = comparison_groups[(bank, seed, held, family, "two_minus_single", "scientific")].iloc[0].to_dict()
                    compare_mapping(ftag + "/paired_bootstrap/two_minus_single", actual, wanted)
            for split, split_info in case["data"].items():
                all_pred = case["families"][family]["all_predictions"][split]
                for depth in range(2, 9):
                    for scope in ("all_masks", "common_order"):
                        columns = np.flatnonzero(np.asarray(case["masks"]).sum(1) == depth) if scope == "all_masks" else [case["path_indices"][depth - 2]]
                        error = all_pred[:, columns] - split_info["y"][:, None]
                        key = (bank, seed, held, split, family, depth, scope)
                        record = pr_groups.get(key)
                        if check(ftag + "/predictor_export_" + str((split, depth, scope)), record is not None and len(record) == 1):
                            compare_mapping(ftag + "/predictor_" + str((split, depth, scope)), record.iloc[0].to_dict(),
                                            {"rmsep": np.sqrt(np.mean(error ** 2)), "mae": np.abs(error).mean(), "bias": error.mean(), "n_scans": len(error), "n_masks": len(columns)})
                            seen_predictor.add(key)
            for (objective, point), (expected_prediction, expected_pulses, expected_metrics) in expected_policies.items():
                key = (bank, seed, held, family, objective, point)
                m, q = pm_groups.get(key), pp_groups.get(key)
                policytag = ftag + "/" + objective + "/" + point
                if not check(policytag + "/exports_present", m is not None and len(m) == 1 and q is not None):
                    continue
                check(policytag + "/row_set", set(q.row_id) == set(info["row_ids"]) and len(q) == len(info["row_ids"]))
                q = q.set_index("row_id").loc[info["row_ids"]]
                check(policytag + "/groups", q.group.tolist() == list(info["groups"]))
                for name, wanted in [("y", info["y"]), ("prediction", expected_prediction), ("pulses", expected_pulses),
                                     ("bank_prediction", case["families"][family]["paths"]["valid"][:, -1]), ("rich_prediction", info["rich"])]:
                    close(policytag + "/" + name, q[name], wanted)
                compare_mapping(policytag + "/metrics", m.iloc[0].to_dict(), expected_metrics)
                compare_mapping(policytag + "/metrics_from_export", m.iloc[0].to_dict(),
                                metric(q.y.to_numpy(), q.prediction.to_numpy(), q.pulses.to_numpy(), q.bank_prediction.to_numpy(), q.rich_prediction.to_numpy()))
        case_summaries.append({"case": tag, "n_validation": len(info["y"]), "n_groups": len(set(info["groups"]))})
    check("exports/all_predictor_rows_accounted_for", seen_predictor == set(pr_groups))
    result = {"passed": all(x["passed"] for x in CHECKS), "n_checks": len(CHECKS),
              "failed_checks": [x for x in CHECKS if not x["passed"]], "checks": CHECKS,
              "cases": case_summaries, "v1_preservation": preservation,
              "registration_dependency": registration["dependency"], "verification_source_sha256": p.digest(__file__),
              "scope": "Development seasons 1–3 only; no fitting, external loading, or model selection.",
              "primary_ci_reconstruction": "Expanded-row paired population bootstrap: 1000 draws, seed 42; PLS/ridge minus MLP at depth four and PLS two-reference minus single-reference scientific points, all three seasons.",
              "primary_curve_reconstruction": "All 378 exported validation threshold rows for swap_mid seed42, all families and both objectives.",
              "metric_tolerance": {"absolute": 1e-8, "relative": 1e-8}}
    p.atomic_json(p.OUT / "verification.json", result)
    report = [
        "# Methodology v2: independent verification",
        "",
        "**%s:** %s numerical and artifact checks; %s failures." %
        ("PASS" if result["passed"] else "FAIL", format(len(CHECKS), ","), len(result["failed_checks"])),
        "",
        "- All 12 development cases and 24 distinct linear-predictor checkpoints verified, including dependency and file hashes.",
        "- All 1,352,076 exported policy predictions, all predictor/policy metrics, calibration choices and signed endpoint decompositions reconstructed.",
        "- Primary paired population-bootstrap intervals reconstructed directly from resampled rows; all 378 primary validation-curve rows recomputed.",
        "- All %d protected version-1 files remain byte-identical; no new protected scientific files were created." % preservation["files"],
        "- External outcome/feature/scored-result opening was rejected before reading in three deliberate guard checks. No external season was loaded or rescored.",
        "- Separate software-test execution: 22 tests passed, as recorded by the test agent. This numerical verifier does not rerun that suite.",
        "- Root separately inspected the two generated scientific plots; this verifier checks their underlying numeric tables.",
        "",
        "The completed original v1 analysis is preserved. This revision is exploratory development evidence. Its intervals do not turn reused development seasons into fresh external validation.",
        "",
        "The full resume proof is recorded separately by the root process after its before/after hash comparison; this report does not claim that an unfinished resume has passed.",
        "",
        "Machine-readable checks: results/verification.json. Source: verify.py.",
        "",
    ]
    path = p.HERE / "verification_report.md"
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text("\n".join(report))
    temporary.replace(path)
    print(json.dumps({k: result[k] for k in ("passed", "n_checks", "failed_checks")}, indent=2))
    if not result["passed"]:
        raise AssertionError("Methodology v2 independent verification failed; see results/verification.json")
    return result


if __name__ == "__main__":
    verify()
