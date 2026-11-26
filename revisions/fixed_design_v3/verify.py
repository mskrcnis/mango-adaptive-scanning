"""Independent artifact and numerical audit of the fixed-design study.

This module does not fit predictors, select models for deployment, or load
external outcomes. Selection verification reconstructs the entire declared
finite search from saved design-only OOF predictions.
"""
import json
import os
import subprocess
import sys
from itertools import combinations, permutations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# These are independent audit formulas from v2, not its fitting/reporting code.
from revisions.methodology_v2.verify import metric, apply, visited, paired_direct
from revisions.methodology_v2 import verify as previous_audit

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ROOT = HERE.parents[1]
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
        detail += "; max finite difference %.12g" % (np.max(np.abs(a[finite] - b[finite])) if finite.any() else 0.)
    return check(name, good, detail)


def compare(name, actual, expected):
    for key, value in expected.items():
        if key not in actual:
            check(name + "/" + key, False, "missing field")
        else:
            close(name + "/" + key, np.nan if actual[key] is None else actual[key], value)


def mask_columns(masks, order):
    lookup = {tuple(row): index for index, row in enumerate(masks)}
    result = []
    for depth in range(2, 9):
        row = np.zeros(8, dtype=bool)
        row[list(order[:depth])] = True
        result.append(lookup[tuple(row)])
    return result


def catalog_order(centers):
    result = [0, 7]
    while len(result) < 8:
        candidates = [(min(abs(centers[j] - centers[k]) for k in result), -centers[j], -j, j)
                      for j in range(8) if j not in result]
        result.append(max(candidates)[-1])
    return result


def selection_checks(selection, predictions, y, masks, centers, tag):
    masks = np.asarray(masks, dtype=bool)
    expected_masks = set()
    for n in range(7):
        for subset in combinations(range(1, 7), n):
            row = np.zeros(8, dtype=bool)
            row[[0, 7] + list(subset)] = True
            expected_masks.add(tuple(row))
    check(tag + "/all64_masks", masks.shape == (64, 8) and set(map(tuple, masks)) == expected_masks)
    error = predictions - np.asarray(y)[:, None]
    mse = np.mean(error ** 2, axis=0)
    close(tag + "/all64_design_mse", selection["mask_mse"], mse, atol=1e-12, rtol=1e-12)
    for depth in range(2, 9):
        candidates = [i for i, row in enumerate(masks) if row.sum() == depth]
        candidates.sort(key=lambda i: (mse[i], tuple(np.flatnonzero(masks[i]))))
        chosen = selection["by_depth"][str(depth)]
        check(tag + "/best_subset_%d" % depth, chosen == candidates[0])
        margin = mse[candidates[1]] - mse[candidates[0]] if len(candidates) > 1 else None
        actual = selection["by_depth_second_best_mse_margin"][str(depth)]
        check(tag + "/subset_margin_%d" % depth, actual is None) if margin is None else close(tag + "/subset_margin_%d" % depth, actual, margin)
    expected = []
    for suffix in permutations(range(1, 7)):
        order = (0, 7) + suffix
        columns = mask_columns(masks, order)
        expected.append((float(np.sum(mse[columns[:-1]])), order, columns))
    expected.sort(key=lambda row: (row[0], row[1]))
    saved = {tuple(row["order"]): row for row in selection["order_scores"]}
    check(tag + "/all720_orders", len(saved) == 720 and set(saved) == {x[1] for x in expected})
    if len(saved) == 720:
        close(tag + "/all720_order_scores", [saved[row[1]]["score"] for row in expected], [row[0] for row in expected], atol=1e-12, rtol=1e-12)
        check(tag + "/all720_prefix_indices", all(saved[row[1]]["path_indices"] == row[2] for row in expected))
        close(tag + "/all720_depth_scores", [saved[row[1]]["depth_mse"] for row in expected], [mse[row[2]] for row in expected], atol=1e-12, rtol=1e-12)
    check(tag + "/global_optimal_order_and_tie", tuple(selection["order"]) == expected[0][1])
    check(tag + "/selected_prefix_indices", list(selection["path_indices"]) == expected[0][2])
    compare(tag + "/order_summary", selection, {"order_score": expected[0][0], "second_best_order_score": expected[1][0],
            "order_margin": expected[1][0] - expected[0][0], "n_candidate_orders": 720,
            "exact_best_order_ties": sum(row[0] == expected[0][0] for row in expected)})
    check(tag + "/second_best_order", tuple(selection["second_best_order"]) == expected[1][1])
    catalog = catalog_order(centers)
    columns = mask_columns(masks, catalog)
    check(tag + "/catalog_order", list(selection["catalog_order"]) == catalog)
    check(tag + "/catalog_columns", list(selection["catalog_path_indices"]) == columns)
    close(tag + "/catalog_score", selection["catalog_order_score"], np.sum(mse[columns[:-1]]))
    check(tag + "/selected_order_legal", sorted(selection["order"]) == list(range(8)) and list(selection["order"][:2]) == [0, 7])


def crossfit_checks(crossfit, groups, tag):
    groups = np.asarray(groups).astype(str)
    check(tag + "/LOPO_fold_count", crossfit["n_folds"] == len(set(groups)) == crossfit["n_groups"])
    close(tag + "/n_scans", crossfit["n"], len(groups), atol=0, rtol=0)
    fold_ids = np.asarray(crossfit["fold_ids"])
    coverage = np.zeros(len(groups), int)
    for fold in crossfit["provenance"]:
        tr = np.asarray(fold["fit_local_row_ids"], dtype=int)
        va = np.asarray(fold["target_local_row_ids"], dtype=int)
        coverage[va] += 1
        check(tag + "/fold%d/row_partition" % fold["fold"], not set(tr) & set(va) and set(tr) | set(va) == set(range(len(groups))))
        check(tag + "/fold%d/target_single_population" % fold["fold"], len(set(groups[va])) == 1)
        check(tag + "/fold%d/group_isolation" % fold["fold"], not set(groups[tr]) & set(groups[va]))
        check(tag + "/fold%d/group_provenance" % fold["fold"], set(groups[tr]) == set(fold["fit_groups"]) and set(groups[va]) == set(fold["target_groups"]))
        check(tag + "/fold%d/row_provenance" % fold["fold"], np.all(fold_ids[va] == fold["fold"]) and fold["n_fit"] == len(tr) and fold["n_target"] == len(va))
    close(tag + "/OOF_exact_once_coverage", coverage, np.ones(len(groups)), atol=0, rtol=0)
    for family in ("pls", "ridge"):
        predictions = crossfit["predictions"][family]
        check(tag + "/" + family + "/prediction_shape_finite", predictions.shape == (len(groups), 64) and np.isfinite(predictions).all())


def checkpoint(p, name, dependency):
    path = OUT / "checkpoints" / (name + ".joblib")
    metadata = json.loads(path.with_suffix(".json").read_text())
    check(name + "/complete", metadata.get("status") == "complete")
    check(name + "/dependency", metadata.get("dependency") == dependency)
    check(name + "/sha256", metadata.get("sha256") == p.digest(path))
    return joblib.load(path)


def preservation(p):
    script = "import json; from revisions.fixed_design_v3.pipeline import verify_preservation; print(json.dumps(verify_preservation()))"
    run = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT), text=True, check=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    result = json.loads(run.stdout)
    check("prior_versions/unchanged", result["passed"], result.get("changed"))
    expected = json.loads((HERE / "prior_versions_preservation.json").read_text())["sha256"]
    additions = sorted({str(f.relative_to(ROOT)) for f in p.protected_files()} - set(expected))
    check("prior_versions/no_new_files", not additions, additions)
    return result


def guard_checks():
    # Separate short-lived processes: never weaken an installed fitting guard.
    for stage in ("design", "evaluate"):
        script = """import json
from revisions.fixed_design_v3 import pipeline as p
p.install_guard(STAGE)
targets=['data/sealed/external_labels.csv','data/processed/external_features.csv','results/external_metrics.csv']
if STAGE == 'design':
    targets.append(str(p.source_path(1,'swap_mid')))
denied=[]
for target in targets:
    try:
        with open(target,'rb'):
            raise RuntimeError('Forbidden file opened')
    except PermissionError:
        denied.append(target)
try:
    with open('mango/models.py','r+'):
        raise RuntimeError('Protected source opened for writing')
except PermissionError:
    denied.append('protected_write')
print(json.dumps(denied))
""".replace("STAGE", repr(stage))
        run = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT), text=True, check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        denied = json.loads(run.stdout)
        check("guard/" + stage + "/denied_reads_and_protected_write", len(denied) == (5 if stage == "design" else 4))
    design_audit = json.loads((OUT / "design_read_audit.json").read_text())
    evaluation_audit = json.loads((OUT / "evaluation_read_audit.json").read_text())
    check("guard/design_read_audit", design_audit["source_prediction_reads"] is False and
          all("external" not in x.lower() and "sealed" not in Path(x).parts and
              not x.startswith("revisions/methodology_v2/results/") for x in design_audit["paths"]))
    check("guard/evaluation_read_audit", evaluation_audit["external_reads"] is False and
          all("external" not in x.lower() and "sealed" not in Path(x).parts for x in evaluation_audit["paths"]))


def design_case_checks(p, design, assignment, frame, bank, dependency, tag):
    role_keys = {"fit": "fit_row_ids", "design": "bank_design_row_ids", "cal": "calibration_row_ids", "valid": "validation_row_ids"}
    groups, row_sets = [], []
    for role, key in role_keys.items():
        ids = list(design["role_row_ids"][role])
        check(tag + "/" + role + "/saved_assignment_order", ids == assignment[key])
        check(tag + "/" + role + "/unique_ids", len(ids) == len(set(ids)))
        actual_groups = set(frame.loc[ids, "group"])
        check(tag + "/" + role + "/group_provenance", actual_groups == set(design["role_groups"][role]))
        groups.append(actual_groups)
        row_sets.append(set(ids))
    check(tag + "/four_roles_group_disjoint", all(not groups[i] & groups[j] for i in range(4) for j in range(i + 1, 4)))
    check(tag + "/complete_development_partition", set.union(*row_sets) == set(frame.index))
    check(tag + "/bank_indices", list(design["bank_indices"]) == list(p.BANKS[bank]))
    ids = list(design["design_row_ids"])
    check(tag + "/design_row_order", ids == assignment["bank_design_row_ids"])
    check(tag + "/design_groups", list(design["design_groups"]) == frame.loc[ids, "group"].tolist())
    close(tag + "/design_assays", design["design_y"], frame.loc[ids, "DM"])
    close(tag + "/design_seasons", design["design_seasons"], frame.loc[ids, "season"], atol=0, rtol=0)
    check(tag + "/held_season_excluded_design", assignment["held_season"] not in set(design["design_seasons"]))
    crossfit = design["crossfit"]
    crossfit_checks(crossfit, design["design_groups"], tag + "/crossfit")
    for fold in crossfit["provenance"]:
        f = fold["fold"]
        value = checkpoint(p, "designfold_s%d_%s_%d" % (assignment["held_season"], bank, f),
                           p.canonical_hash([dependency, "designfold", assignment["held_season"], bank, f]))
        check(tag + "/fold%d/checkpoint_row_ids" % f,
              value["fit_local_row_ids"] == fold["fit_local_row_ids"] and value["target_local_row_ids"] == fold["target_local_row_ids"])
        for family in ("pls", "ridge"):
            close(tag + "/fold%d/%s_prediction_assignment" % (f, family),
                  value["predictions"][family], crossfit["predictions"][family][fold["target_local_row_ids"]], atol=0, rtol=0)
    for family in ("pls", "ridge"):
        selection_checks(design["selections"][family], crossfit["predictions"][family],
                         design["design_y"], crossfit["masks"], design["centers_nm"], tag + "/" + family)


def evaluation_case_checks(p, case, source, design, tag):
    check(tag + "/source_masks", np.array_equal(case["masks"], source["masks"]) and
          np.array_equal(case["masks"], design["crossfit"]["masks"]))
    check(tag + "/bank_indices", list(case["bank_indices"]) == list(source["bank_indices"]) == list(design["bank_indices"]))
    check(tag + "/families_PLS_ridge_only", set(case["families"]) == {"pls", "ridge"})
    for split, role in (("train", "fit"), ("cal", "cal"), ("valid", "valid")):
        a, b = case["data"][split], source["data"][split]
        check(tag + "/" + split + "/source_ids", np.array_equal(a["row_ids"], b["row_ids"]) and
              np.array_equal(a["row_ids"], design["role_row_ids"][role]))
        check(tag + "/" + split + "/source_groups", np.array_equal(a["groups"], b["groups"]))
        for name in ("y", "rich"):
            close(tag + "/" + split + "/source_" + name, a[name], b[name], atol=0, rtol=0)
        close(tag + "/" + split + "/source_full_features", case["full_features"][split], b["features"][:, -1, :], atol=0, rtol=0)
    outcomes = {}
    for family in ("pls", "ridge"):
        item = case["families"][family]
        selected = design["selections"][family]
        expected_subsets = [selected["by_depth"][str(d)] for d in range(2, 9)]
        check(tag + "/" + family + "/selected_fixed_masks", item["selected_subsets"] == expected_subsets)
        for split in case["data"]:
            close(tag + "/" + family + "/" + split + "/fixed_subset_source_predictions",
                  item["fixed_subset_paths"][split], source["families"][family]["all_predictions"][split][:, expected_subsets], atol=0, rtol=0)
        for variant in ("catalog", "designed"):
            value = item["orders"][variant]
            order = selected["catalog_order"] if variant == "catalog" else selected["order"]
            indices = mask_columns(case["masks"], order)
            check(tag + "/" + family + "/" + variant + "/order", list(value["order"]) == list(order))
            check(tag + "/" + family + "/" + variant + "/prefix_indices", list(value["path_indices"]) == indices)
            adapter_data = {}
            for split, info in case["data"].items():
                full = case["full_features"][split]
                features = []
                for column in indices:
                    mask = case["masks"][column]
                    features.append(np.column_stack([np.where(mask, full[:, :8], 0.), np.broadcast_to(mask, (len(full), 8))]))
                features = np.stack(features, axis=1)
                close(tag + "/" + family + "/" + variant + "/" + split + "/masked_features",
                      p.features_from_full(full, case["masks"], indices), features, atol=0, rtol=0)
                close(tag + "/" + family + "/" + variant + "/" + split + "/source_predictions",
                      value["paths"][split], source["families"][family]["all_predictions"][split][:, indices], atol=0, rtol=0)
                close(tag + "/" + family + "/" + variant + "/" + split + "/same_family_endpoint",
                      value["paths"][split][:, -1], source["families"][family]["all_predictions"][split][:, -1], atol=0, rtol=0)
                if variant == "catalog":
                    close(tag + "/" + family + "/" + split + "/catalog_source_features", features, source["data"][split]["features"], atol=0, rtol=0)
                adapter_data[split] = dict(info, features=features)
            # Reuse independent audit equations, not the fitted stopping evaluator.
            adapter = {"data": adapter_data, "families": {family: value}}
            previous_audit.CHECKS.clear()
            outcomes[(family, variant)] = previous_audit._stopping_checks(adapter, family, tag + "/" + family + "/" + variant)
            CHECKS.extend(previous_audit.CHECKS)
            previous_audit.CHECKS.clear()
    return outcomes


EXPORT_KEYS = ["held_season", "bank", "family", "variant", "objective", "operating_point"]


def expected_export_policies(case, outcomes):
    result = {}
    y, rich = case["data"]["valid"]["y"], case["data"]["valid"]["rich"]
    for family in ("pls", "ridge"):
        for variant in ("catalog", "designed"):
            for (objective, point), value in outcomes[(family, variant)].items():
                result[(family, variant, objective, point)] = value
        fixed = case["families"][family]["fixed_subset_paths"]["valid"]
        for depth in range(2, 9):
            prediction, pulses = fixed[:, depth - 2], np.full(len(y), depth)
            result[(family, "selected_subset", "fixed_length", "depth_%d" % depth)] = (
                prediction, pulses, metric(y, prediction, pulses, fixed[:, -1], rich))
    return result


def export_checks(case, expected, metric_groups, prediction_groups, curve_groups, tag):
    held, bank = case["held_season"], case["bank"]
    info = case["data"]["valid"]
    for (family, variant, objective, point), (prediction, pulses, stats) in expected.items():
        key = (held, bank, family, variant, objective, point)
        m, q = metric_groups.get(key), prediction_groups.get(key)
        name = tag + "/" + "/".join((family, variant, objective, point))
        if not check(name + "/export_present", m is not None and len(m) == 1 and q is not None):
            continue
        check(name + "/row_set", len(q) == len(info["row_ids"]) and set(q.row_id) == set(info["row_ids"]))
        q = q.set_index("row_id").loc[info["row_ids"]]
        check(name + "/row_groups", q.group.tolist() == list(info["groups"]))
        endpoint = case["families"][family]["fixed_subset_paths"]["valid"][:, -1]
        for field, wanted in (("y", info["y"]), ("prediction", prediction), ("pulses", pulses),
                              ("bank_prediction", endpoint), ("rich_prediction", info["rich"])):
            close(name + "/prediction_export/" + field, q[field], wanted)
        compare(name + "/metrics", m.iloc[0].to_dict(), stats)
        compare(name + "/metrics_from_export", m.iloc[0].to_dict(),
                metric(q.y.to_numpy(), q.prediction.to_numpy(), q.pulses.to_numpy(),
                       q.bank_prediction.to_numpy(), q.rich_prediction.to_numpy()))
        if point in ("scientific", "engineering"):
            frozen = case["families"][family]["orders"][variant]["stopping"]["selections"][objective][point]
            compare(name + "/frozen_threshold", m.iloc[0].to_dict(),
                    {"threshold": frozen["threshold"], "threshold_index": frozen["threshold_index"]})
        if point == "engineering":
            screen = stats["mean_pulses"] <= 6 and stats["rmsep_increase_vs_bank"] <= .25
            for field, wanted in (("evaluation_engineering_pass", screen),
                                  ("calibration_engineering_feasible", frozen["feasible"])):
                actual = m.iloc[0].get(field)
                check(name + "/" + field + "/present_boolean", isinstance(actual, (bool, np.bool_)))
                check(name + "/" + field + "/correct", isinstance(actual, (bool, np.bool_)) and actual == wanted)
    for family in ("pls", "ridge"):
        for variant in ("catalog", "designed"):
            item = case["families"][family]["orders"][variant]
            for split in ("cal", "valid"):
                info = case["data"][split]
                path = item["paths"][split]
                for objective in ("two_reference", "single_reference"):
                    probability = item["probabilities"][split][objective]
                    reference = path[:, -1] if objective == "two_reference" else info["rich"]
                    labels = np.abs(info["y"][:, None] - path[:, :-1]) - np.abs(info["y"] - reference)[:, None] > .5
                    for index, threshold in enumerate(np.linspace(0, 1, 21)):
                        prediction, pulses, selected = apply(path, probability, threshold)
                        stats = dict(metric(info["y"], prediction, pulses, path[:, -1], info["rich"]),
                                     **visited(probability, labels, selected), threshold=threshold, threshold_index=index)
                        key = (held, bank, family, variant, objective, split, index)
                        row = curve_groups.get(key)
                        name = tag + "/" + "/".join((family, variant, objective, split)) + "/curve_%d" % index
                        if check(name + "/present", row is not None and len(row) == 1):
                            compare(name, row.iloc[0].to_dict(), stats)


def comma_numbers(value, dtype=int):
    return [dtype(x) for x in str(value).split(",")]


def design_export_checks(design, held, bank, subset_groups, order_groups, chosen_groups, tag):
    masks = design["crossfit"]["masks"]
    centers = np.asarray(design["centers_nm"])
    for family in ("pls", "ridge"):
        selection = design["selections"][family]
        name = tag + "/" + family
        subsets = subset_groups[(held, bank, family)].set_index("mask_index")
        check(name + "/64_exported_mask_rows", len(subsets) == 64 and set(subsets.index) == set(range(64)))
        for j, mask in enumerate(masks):
            row = subsets.loc[j]
            observed = np.flatnonzero(mask).tolist()
            check(name + "/mask%d/indices" % j, comma_numbers(row["indices"]) == observed)
            close(name + "/mask%d/centers" % j, comma_numbers(row["centers_nm"], float), centers[observed], atol=0, rtol=0)
            compare(name + "/mask%d/stats" % j, row.to_dict(),
                    {"depth": int(mask.sum()), "mse": selection["mask_mse"][j], "rmsep": np.sqrt(selection["mask_mse"][j])})
            check(name + "/mask%d/selected" % j, row["selected"] == (selection["by_depth"][str(int(mask.sum()))] == j))
        orders = order_groups[(held, bank, family)]
        actual = {tuple(comma_numbers(row.order)): row for row in orders.itertuples(index=False)}
        wanted = {tuple(row["order"]): row for row in selection["order_scores"]}
        check(name + "/720_exported_order_rows", len(orders) == len(actual) == 720 and set(actual) == set(wanted))
        close(name + "/720_exported_order_scores", [actual[k].score for k in sorted(wanted)],
              [wanted[k]["score"] for k in sorted(wanted)])
        check(name + "/720_exported_order_prefixes", all(comma_numbers(actual[k].path_indices) == wanted[k]["path_indices"] for k in wanted))
        check(name + "/720_exported_order_selection", all(actual[k].selected == (list(k) == selection["order"]) for k in wanted))
        chosen = chosen_groups[(held, bank, family)].iloc[0]
        check(name + "/chosen_order", comma_numbers(chosen.order) == selection["order"])
        close(name + "/chosen_order_centers", comma_numbers(chosen.order_nm, float), centers[selection["order"]], atol=0, rtol=0)
        close(name + "/catalog_centers", comma_numbers(chosen.catalog_order_nm, float), centers[selection["catalog_order"]], atol=0, rtol=0)
        compare(name + "/chosen_summary", chosen.to_dict(), {"order_margin": selection["order_margin"],
                "order_score": selection["order_score"], "catalog_order_score": selection["catalog_order_score"],
                "n_design_groups": design["crossfit"]["n_groups"], "n_design_scans": design["crossfit"]["n"]})
        for depth in (4, 6):
            chosen_mask = masks[selection["by_depth"][str(depth)]]
            close(name + "/chosen_fixed%d_centers" % depth, comma_numbers(chosen["selected_%d_nm" % depth], float), centers[chosen_mask], atol=0, rtol=0)
            close(name + "/chosen_ordered%d_centers" % depth, comma_numbers(chosen["ordered_%d_nm" % depth], float), centers[selection["order"][:depth]], atol=0, rtol=0)
            close(name + "/chosen_fixed%d_margin" % depth, chosen["subset_%d_margin" % depth], selection["by_depth_second_best_mse_margin"][str(depth)])


def comparison_checks(case, expected, comparison_groups, tag):
    held, bank = case["held_season"], case["bank"]
    info = case["data"]["valid"]
    y, groups = info["y"], info["groups"]
    for family in ("pls", "ridge"):
        specifications = []
        for depth in (4, 6):
            point = "depth_%d" % depth
            b = (family, "catalog", "fixed_length", point)
            specifications += [
                ("designed_fixed_minus_catalog", point, (family, "designed", "fixed_length", point), b),
                ("selected_subset_minus_catalog", point, (family, "selected_subset", "fixed_length", point), b)]
        for point, depth in (("scientific", 4), ("engineering", 6)):
            a = (family, "designed", "two_reference", point)
            specifications += [
                ("two_minus_single", point, a, (family, "designed", "single_reference", point)),
                ("adaptive_minus_selected_subset", point, a, (family, "selected_subset", "fixed_length", "depth_%d" % depth))]
        for name, point, ka, kb in specifications:
            a, b = expected[ka], expected[kb]
            record = comparison_groups[(held, bank, family, name, point)].iloc[0].to_dict()
            wanted = {"n_groups": len(set(groups)), "delta_rmsep": np.sqrt(np.mean((a[0] - y) ** 2)) - np.sqrt(np.mean((b[0] - y) ** 2)),
                      "delta_pulses": np.mean(a[1] - b[1]),
                      "budget_comparable": abs(np.mean(a[1] - b[1])) <= .25}
            prefix = tag + "/" + family + "/comparison/" + name + "/" + point
            compare(prefix + "/point", record, wanted)
            primary = bank == "swap_mid" and family == "pls" and (
                name in ("designed_fixed_minus_catalog", "selected_subset_minus_catalog") or
                (name == "two_minus_single" and point == "scientific"))
            if primary:
                compare(prefix + "/expanded_row_bootstrap", record, paired_direct(groups, y, a[0], b[0], a[1], b[1]))


def verify():
    from . import pipeline as p
    CHECKS.clear()
    prior = preservation(p)
    software_path = OUT / "software_tests.json"
    software = json.loads(software_path.read_text()) if software_path.exists() else {}
    check("software_tests/saved_pass_evidence", software.get("passed") is True and
          software.get("exit_code") == 0 and software.get("tests_passed", 0) > 0)
    check("software_tests/current_test_source", software.get("test_source_sha256") ==
          p.digest(HERE / "test_design.py"))
    registration = json.loads((OUT / "registration.json").read_text())
    dependency = registration["dependency"]
    check("registration/self_hash", dependency == p.canonical_hash(registration["dependencies"]))
    check("registration/current_dependencies", registration["dependencies"] == p.dependencies())
    check("registration/six_cases", registration["cases"] == [list(x) for x in p.CASES])
    check("registration/no_external", registration["external_evaluation"] is False)
    lock = json.loads((OUT / "design_lock.json").read_text())
    names = {"results/checkpoints/design_s%d_%s.joblib" % (held, bank) for held, bank in p.CASES}
    check("lock/exact_six_design_names", set(lock["design_sha256"]) == names)
    check("lock/registration_dependency", lock["registration_dependency"] == dependency)
    check("lock/completed_before_evaluation", lock["completed_all_designs_before_evaluation"] is True)
    check("lock/no_external", lock["external_evaluation"] is False)
    for name, digest in lock["design_sha256"].items():
        check("lock/" + name, p.digest(HERE / name) == digest)
    guard_checks()
    frame = pd.read_csv(ROOT / "data/processed/development.csv", float_precision="round_trip").set_index("row_id")
    check("development/data_scope", len(frame) == 10243 and frame.index.is_unique and set(frame.season) == {1, 2, 3})
    assignments = {f["held_season"]: f for f in json.loads((ROOT / "results/fold_assignments.json").read_text())}
    metrics = pd.read_csv(OUT / "metrics.csv", float_precision="round_trip")
    predictions = pd.read_csv(OUT / "predictions.csv.gz", float_precision="round_trip")
    curves = pd.read_csv(OUT / "threshold_curves.csv", float_precision="round_trip")
    subsets = pd.read_csv(OUT / "design_subsets.csv", float_precision="round_trip")
    orders = pd.read_csv(OUT / "design_orders.csv", float_precision="round_trip")
    chosen = pd.read_csv(OUT / "selected_designs.csv", float_precision="round_trip")
    comparisons = pd.read_csv(OUT / "comparisons.csv", float_precision="round_trip")
    curve_keys = ["held_season", "bank", "family", "variant", "objective", "split", "threshold_index"]
    check("exports/metric_unique_keys", not metrics.duplicated(EXPORT_KEYS).any())
    check("exports/prediction_unique_keys", not predictions.duplicated(EXPORT_KEYS + ["row_id"]).any())
    check("exports/curve_unique_keys", not curves.duplicated(curve_keys).any())
    check("exports/metric_count", len(metrics) == 348)
    check("exports/prediction_count", len(predictions) == 1188188)
    check("exports/curve_count", len(curves) == 2016)
    design_keys = ["held_season", "bank", "family"]
    comparison_keys = design_keys + ["comparison", "operating_point"]
    check("exports/design_subsets_count_unique", len(subsets) == 768 and not subsets.duplicated(design_keys + ["mask_index"]).any())
    check("exports/design_orders_count_unique", len(orders) == 8640 and not orders.duplicated(design_keys + ["order"]).any())
    check("exports/selected_design_count_unique", len(chosen) == 12 and not chosen.duplicated(design_keys).any())
    check("exports/comparison_count_unique", len(comparisons) == 96 and not comparisons.duplicated(comparison_keys).any())
    metric_groups = {key: value for key, value in metrics.groupby(EXPORT_KEYS)}
    prediction_groups = {key: value for key, value in predictions.groupby(EXPORT_KEYS)}
    curve_groups = {key: value for key, value in curves.groupby(curve_keys)}
    subset_groups = {key: value for key, value in subsets.groupby(design_keys)}
    order_groups = {key: value for key, value in orders.groupby(design_keys)}
    chosen_groups = {key: value for key, value in chosen.groupby(design_keys)}
    comparison_groups = {key: value for key, value in comparisons.groupby(comparison_keys)}
    summaries = []
    for held, bank in p.CASES:
        tag = "s%d_%s" % (held, bank)
        design = checkpoint(p, "design_" + tag, p.canonical_hash([dependency, "design", held, bank]))
        check(tag + "/design_held_season", design["held_season"] == held)
        design_case_checks(p, design, assignments[held], frame, bank, dependency, tag + "/design")
        design_export_checks(design, held, bank, subset_groups, order_groups, chosen_groups, tag + "/design_export")
        case = checkpoint(p, "evaluation_" + tag,
                          p.canonical_hash([dependency, "evaluation", held, bank, p.canonical_hash(lock)]))
        check(tag + "/case_identity", case["held_season"] == held and case["bank"] == bank)
        source_path = p.source_path(held, bank)
        check(tag + "/source_hash", case["source_sha256"] == p.digest(source_path) ==
              registration["dependencies"][str(source_path.relative_to(ROOT))])
        check(tag + "/design_lock_hash", case["design_lock_sha256"] == p.digest(OUT / "design_lock.json"))
        source = joblib.load(source_path)
        outcomes = evaluation_case_checks(p, case, source, design, tag)
        expected = expected_export_policies(case, outcomes)
        export_checks(case, expected, metric_groups, prediction_groups, curve_groups, tag)
        comparison_checks(case, expected, comparison_groups, tag)
        summaries.append({"case": tag, "design_scans": len(design["design_y"]),
                          "design_groups": len(set(design["design_groups"])),
                          "validation_scans": len(case["data"]["valid"]["y"])})
    result = {"passed": all(x["passed"] for x in CHECKS), "n_checks": len(CHECKS),
              "failed_checks": [x for x in CHECKS if not x["passed"]], "checks": CHECKS,
              "cases": summaries, "prior_versions_preservation": prior,
              "registration_dependency": dependency, "verification_source_sha256": p.digest(__file__),
              "inherited_audit_source_sha256": p.digest(previous_audit.__file__),
              "software_tests": software,
              "primary_ci_reconstruction": "15 expanded-row paired population bootstraps: both fixed-budget contrasts at four/six readings and designed two-minus-single scientific, primary PLS bank, all three held seasons.",
              "scope": "Development only; no fitting or external outcome access. Exact search and evaluated policies reconstructed independently."}
    p.atomic_json(OUT / "verification.json", result)
    resume_path = OUT / "resume_verification.json"
    resume = json.loads(resume_path.read_text()) if resume_path.exists() else {}
    resume_line = (
        "Completed full resume: all %d snapshot scientific/model/report/figure files remained byte-identical (results/resume_verification.json)."
        % resume["files_checked"]
        if resume.get("passed") is True and not resume.get("changed") and resume.get("files_checked", 0) > 0
        else "Full resume verification is pending; numerical verification alone does not establish resume preservation."
    )
    report = [
        "# Fixed-design v3: independent verification", "",
        "**%s:** %s numerical/artifact checks; %d failures." %
        ("PASS" if result["passed"] else "FAIL", format(len(CHECKS), ","), len(result["failed_checks"])), "",
        "- All six design cases and six evaluation cases checked, including all 48 LOPO fold checkpoints and dependency hashes.",
        "- Independently reconstructed every 64-mask search and 720-order search for both predictor families, including exact tie breaks.",
        "- Checked all 768 exported mask rows, 8,640 order rows and 12 chosen designs against the saved search.",
        "- Reconstructed all 348 policy metric rows, 1,188,188 per-scan predictions and 2,016 threshold-curve rows.",
        "- All 96 paired comparison point estimates checked; 15 primary intervals reconstructed by expanding sampled populations into actual paired rows.",
        "- All %d protected v1/v2 files remain unchanged. Guards reject external data, premature v2 result reads and writes to prior versions." % prior["files"],
        "- Separate synthetic software suite: %d tests passed with exit code %s; saved root execution evidence is in results/software_tests.json. This numerical verifier does not rerun that suite." %
        (software.get("tests_passed", 0), software.get("exit_code", "missing")),
        "", resume_line, "",
        "These checks establish computational consistency and the declared data separation. The results remain exploratory because development seasons were reused; the intervals do not include repeated design selection or future-season uncertainty.",
        "", "Machine-readable evidence: results/verification.json. Source: verify.py.", "",
    ]
    path = HERE / "verification_report.md"
    temporary = path.with_suffix(".md.tmp")
    temporary.write_text("\n".join(report))
    temporary.replace(path)
    print(json.dumps({k: result[k] for k in ("passed", "n_checks", "failed_checks")}, indent=2))
    if not result["passed"]:
        raise AssertionError("Fixed design v3 verification failed; see results/verification.json")
    return result


if __name__ == "__main__":
    verify()
