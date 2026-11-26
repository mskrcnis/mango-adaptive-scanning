"""Reporting-only evidence from saved development checkpoints."""
import gzip
import io
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .pipeline import HERE, OUT, CASES, FAMILIES, endpoint_components, event
from .stopping import evaluate_stopping


def write_bytes(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != value:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(value)
        temporary.replace(path)


def csv(path, frame, compressed=False):
    value = frame.to_csv(index=False, float_format="%.12g").encode()
    if compressed:
        value = gzip.compress(value, mtime=0)
    write_bytes(path, value)


def metrics(y, pred):
    errors = np.asarray(pred) - np.asarray(y)[:, None]
    return {"rmsep": float(np.sqrt(np.mean(errors**2))), "mae": float(np.mean(np.abs(errors))),
            "bias": float(np.mean(errors))}


def paired_bootstrap(groups, y, prediction_a, prediction_b, pulses_a=None, pulses_b=None):
    """Pairs remain aligned; each draw resamples complete harvest populations."""
    unique, inverse = np.unique(groups, return_inverse=True)
    point = float(np.sqrt(np.mean((prediction_a-y)**2)) - np.sqrt(np.mean((prediction_b-y)**2)))
    result = {"n_groups": len(unique), "delta_rmsep": point}
    if pulses_a is not None:
        result["delta_pulses"] = float(np.mean(pulses_a-pulses_b))
        result["budget_comparable"] = abs(result["delta_pulses"]) <= .25
    if len(unique) < 5:
        result.update(rmsep_ci_low=None, rmsep_ci_high=None)
        return result
    count = np.bincount(inverse)
    sq_a = np.bincount(inverse, weights=(prediction_a-y)**2)
    sq_b = np.bincount(inverse, weights=(prediction_b-y)**2)
    draws = np.random.RandomState(42).randint(0, len(unique), (1000, len(unique)))
    n = count[draws].sum(1)
    delta = np.sqrt(sq_a[draws].sum(1)/n) - np.sqrt(sq_b[draws].sum(1)/n)
    result["rmsep_ci_low"], result["rmsep_ci_high"] = np.percentile(delta, [2.5, 97.5]).tolist()
    if pulses_a is not None:
        pulse = np.bincount(inverse, weights=pulses_a-pulses_b)
        result["pulses_ci_low"], result["pulses_ci_high"] = np.percentile(
            pulse[draws].sum(1)/n, [2.5, 97.5]).tolist()
    return result


def endpoint_summary(groups, values):
    unique, inverse = np.unique(groups, return_inverse=True)
    result = {"n_groups": len(unique), "n": len(groups)}
    count = np.bincount(inverse)
    draws = np.random.RandomState(42).randint(0, len(unique), (1000, len(unique)))
    for key, value in values.items():
        result[key + "_mean"] = float(value.mean())
        summed = np.bincount(inverse, weights=value)
        if len(unique) >= 5:
            interval = np.percentile(summed[draws].sum(1)/count[draws].sum(1), [2.5,97.5])
            result[key + "_ci_low"], result[key + "_ci_high"] = interval.tolist()
    return result


def report():
    predictor, policy, curves, predictions, endpoints, decompositions, comparisons = [], [], [], [], [], [], []
    fit_diagnostics = []
    for held, bank, seed in CASES:
        case = joblib.load(OUT / "checkpoints" / ("case_s%d_%s_seed%d.joblib" % (held, bank, seed)))
        base = {"held_season": held, "bank": bank, "seed": seed}
        data = case["data"]["valid"]
        y, groups = data["y"], data["groups"]
        outcomes = {}
        for family in FAMILIES:
            item = case["families"][family]
            for split, info in case["data"].items():
                matrix = item["all_predictions"][split]
                for depth in range(2, 9):
                    mask_ids = np.flatnonzero(case["masks"].sum(1) == depth)
                    for scope, ids in (("all_masks", mask_ids), ("common_order", [case["path_indices"][depth-2]])):
                        predictor.append(dict(base, split=split, family=family, depth=depth, scope=scope,
                                              n_scans=len(info["y"]), n_masks=len(ids),
                                              **metrics(info["y"], matrix[:, ids])))
            path = item["paths"]["valid"]
            evaluated = evaluate_stopping(item["stopping"], data["features"], path, path[:, -1],
                                          data["rich"], y)
            outcomes[family] = evaluated
            policy.extend(dict(base, family=family, **row) for row in
                          evaluated["records"] + evaluated["fixed_length_controls"])
            for objective, rows in evaluated["frontiers"].items():
                curves.extend(dict(base, family=family, split="valid", **row) for row in rows)
            for objective, rows in item["stopping"]["calibration_frontier"].items():
                curves.extend(dict(base, family=family, split="cal", **row) for row in rows)
                fit_diagnostics.append(dict(base, family=family, objective=objective,
                                            **item["stopping"]["fit_diagnostics"][objective]))
            for key, selected in evaluated["policies"].items():
                objective, point = key.split("|")
                if objective == "fixed_length":
                    point = "depth_" + point
                frame = pd.DataFrame({"row_id": data["row_ids"], "group": groups, "y": y,
                                      "prediction": selected["predictions"], "pulses": selected["pulses"],
                                      "bank_prediction": path[:, -1], "rich_prediction": data["rich"]})
                for name, value in dict(base, family=family, objective=objective, operating_point=point).items():
                    frame[name] = value
                predictions.append(frame)
            pol = evaluated["policies"]
            for point in ("scientific", "engineering"):
                a, b = pol["two_reference|"+point], pol["single_reference|"+point]
                comparisons.append(dict(base, family=family, comparison="two_minus_single",
                    operating_point=point, **paired_bootstrap(groups, y, a["predictions"], b["predictions"],
                                                              a["pulses"], b["pulses"])))
                fixed = pol["fixed_length|4"]
                comparisons.append(dict(base, family=family, comparison="two_minus_fixed4",
                    operating_point=point, **paired_bootstrap(groups, y, a["predictions"], fixed["predictions"],
                                                              a["pulses"], fixed["pulses"])))
        for family in ("pls", "ridge"):
            for depth in (4, 7):
                a = case["families"][family]["paths"]["valid"][:, depth-2]
                b = case["families"]["mlp_hybrid"]["paths"]["valid"][:, depth-2]
                comparisons.append(dict(base, family=family, comparison="predictor_minus_mlp",
                    operating_point="depth_"+str(depth), **paired_bootstrap(groups,y,a,b)))
        mlp, pls = [case["families"][f]["paths"]["valid"] for f in ("mlp_hybrid","pls")]
        components = endpoint_components(y, mlp[:, -2], pls[:, -2], pls[:, -1])
        frame = pd.DataFrame(dict(row_id=data["row_ids"], group=groups, **components))
        for name,value in base.items():
            frame[name] = value
        endpoints.append(frame)
        decompositions.append(dict(base, **endpoint_summary(groups, components)))
    predictor, policy, curves, comparisons = map(pd.DataFrame, (predictor,policy,curves,comparisons))
    csv(OUT / "predictor_metrics.csv", predictor)
    csv(OUT / "policy_metrics.csv", policy)
    csv(OUT / "threshold_curves.csv", curves)
    csv(OUT / "policy_predictions.csv.gz", pd.concat(predictions,ignore_index=True), compressed=True)
    csv(OUT / "endpoint_rows.csv", pd.concat(endpoints,ignore_index=True))
    csv(OUT / "endpoint_summary.csv", pd.DataFrame(decompositions))
    csv(OUT / "paired_comparisons.csv", comparisons)
    write_bytes(OUT / "fit_diagnostics.json", (json.dumps(fit_diagnostics,indent=2,sort_keys=True)+"\n").encode())
    make_figures(predictor, policy, curves, pd.DataFrame(decompositions))
    make_report(predictor, policy, comparisons, pd.DataFrame(decompositions))
    event("Reporting complete: all 12 cases, exact-subset comparisons and frozen stopping decisions.")


def save_figure(fig, name):
    for extension in ("png", "pdf"):
        buffer = io.BytesIO()
        kwargs = {"dpi": 180} if extension == "png" else {"metadata": {"CreationDate": None, "ModDate": None}}
        fig.savefig(buffer, format=extension, bbox_inches="tight", **kwargs)
        write_bytes(HERE / "figures" / (name+"."+extension), buffer.getvalue())


def make_figures(predictor, policy, curves, endpoints):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10, "axes.spines.top":False, "axes.spines.right":False})
    colors = {"mlp_hybrid":"#bc4b30", "pls":"#1b6c8e", "ridge":"#5d8237"}
    labels = {"mlp_hybrid":"Masked MLP → PLS at 8", "pls":"Subset PLS", "ridge":"Subset ridge"}
    fig, axes = plt.subplots(1,3,figsize=(12,3.5),sharex=True,sharey=True)
    for held, ax in enumerate(axes,1):
        rows = predictor[(predictor.bank=="swap_mid") & (predictor.seed==42) &
                         (predictor.split=="valid") & (predictor.scope=="common_order") &
                         (predictor.held_season==held)]
        for family in FAMILIES:
            r=rows[rows.family==family].sort_values("depth")
            ax.plot(r.depth,r.rmsep,"o-",color=colors[family],label=labels[family])
        ax.set(title="Held development season %d"%held,xlabel="Simulated readings",xticks=range(2,9))
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Dry-matter RMSEP (percentage points)")
    axes[1].legend(loc="upper center",bbox_to_anchor=(.5,-.24),ncol=3,frameon=False)
    fig.suptitle("Identical subsets and order • primary bank, seed 42",y=1.03)
    save_figure(fig,"predictors_by_depth");plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,3.5),sharex=True,sharey=True)
    for held,ax in enumerate(axes,1):
        rows=curves[(curves.bank=="swap_mid") & (curves.seed==42) & (curves.split=="valid") &
                    (curves.family=="pls") & (curves.held_season==held)]
        for objective,label,color in (("two_reference","Bank-reference stop","#1b6c8e"),
                                      ("single_reference","Rich-reference stop","#bc4b30")):
            r=rows[rows.objective==objective]
            ax.plot(r.mean_pulses,r.rmsep,".-",label=label,color=color)
            p=policy[(policy.bank=="swap_mid") & (policy.seed==42) & (policy.held_season==held) &
                     (policy.family=="pls") & (policy.objective==objective) & (policy.operating_point=="scientific")].iloc[0]
            ax.scatter([p.mean_pulses],[p.rmsep],s=85,marker="*",color=color,zorder=4)
        r=policy[(policy.bank=="swap_mid") & (policy.seed==42) & (policy.held_season==held) &
                 (policy.family=="pls") & (policy.objective=="fixed_length")].sort_values("fixed_depth")
        ax.plot(r.mean_pulses,r.rmsep,"s--",label="Fixed lengths",color="#666666")
        ax.set(title="Held development season %d"%held,xlabel="Mean simulated readings",xticks=range(2,9))
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Dry-matter RMSEP (percentage points)")
    axes[1].legend(loc="upper center",bbox_to_anchor=(.5,-.24),ncol=3,frameon=False)
    fig.suptitle("PLS stopping-only comparison • stars: calibration-selected four-reading targets",y=1.03)
    save_figure(fig,"stopping_frontiers");plt.close(fig)


def make_report(predictor, policy, comparisons, endpoint):
    p=predictor[(predictor.bank=="swap_mid") & (predictor.seed==42) & (predictor.split=="valid") &
                (predictor.scope=="common_order") & (predictor.depth==4)]
    lines=["# Development-only methodology revision: results",
           "", "All three development seasons were evaluated with the other seasons supplying fitting, bank-design and calibration groups. This revision follows inspection of version 1, including its external findings; it is exploratory. Seasons 4 and 5 were not loaded or rescored. Version 1 remains the completed original analysis.",
           "", "## Decision from this bounded round", "",
           "The controlled results do not establish the masked MLP as the main cause of the earlier accuracy gap. At four identical readings, replacing it with PLS or ridge does not improve the primary common-order point estimates in any held season; all paired 95% intervals include zero. Averaging over every reachable four-channel subset gives small, mixed changes. The earlier comparison against a different fixed four-channel bank therefore cannot be attributed to predictor family alone.",
           "", "Most of the mean seventh-to-eighth improvement persists when both predictions use PLS. The estimator-switch concern was worth testing, but it accounts for only part of this pipeline's endpoint gain. This conclusion is conditional on the registered order, which reads centers 720, 940, 820, 890, 760, 780, 800 and 910 nm in the primary bank. Wavelength spacing was chosen for assay independence, not predictive optimality; these results do not rule out a better development-designed fixed subset or order.",
           "", "The isolated bank-reference stopping objective shows no demonstrated practical advantage in this round. Its primary target-budget comparisons remain budget-incomparable in all three held seasons, and its engineering points fail at least one prototype condition in every season. No revised model is promoted. Preserve the evaluation framework; prioritize a separately registered, design-group-only fixed-subset/order study before adding controller complexity. New independent seasonal and physical measurements remain necessary.",
           "", "## Matched prediction at exactly four readings", "",
           "These are the same channel subsets, acquisition order, fitting rows and held scans. RMSEP is in dry-matter percentage points. PLS and ridge hyperparameters were fixed before this round.",
           "", "| Held development season | Masked MLP | Subset PLS | Subset ridge |",
           "|---|---:|---:|---:|"]
    for held in (1,2,3):
        row=p[p.held_season==held].set_index("family")
        lines.append("| %d | %.4f | %.4f | %.4f |"%(held,*[row.loc[f,"rmsep"] for f in FAMILIES]))
    lines += ["", "The full-mask MLP entry is the existing hybrid's PLS dispatch; it is not a trained full-mask MLP result. All-mask summaries pool squared errors over scans and equally weighted masks at each depth; they are distinct from the common-order results above.",
              "", "## What accounts for the seventh-to-eighth improvement?", "",
              "Signed mean reductions in absolute error: estimator replacement at seven readings plus the final measurement within the PLS family. Negative components are retained. These quantify this fitted pipeline and cannot establish irreducible optical information.",
              "", "| Held season | Total hybrid improvement | MLP7 → PLS7 | PLS7 → PLS8 |",
              "|---|---:|---:|---:|"]
    for _,r in endpoint[(endpoint.bank=="swap_mid") & (endpoint.seed==42)].iterrows():
        lines.append("| %d | %.4f | %.4f | %.4f |"%(r.held_season,r.total_mean,r.estimator_mean,r.measurement_mean))
    lines += ["", "The endpoint explanation changes for the independent uniform bank:", "",
              "| Held season | Total hybrid improvement | MLP7 → PLS7 | PLS7 → PLS8 |",
              "|---|---:|---:|---:|"]
    for _,r in endpoint[(endpoint.bank=="uniform") & (endpoint.seed==42)].iterrows():
        lines.append("| %d | %.4f | %.4f | %.4f |"%(r.held_season,r.total_mean,r.estimator_mean,r.measurement_mean))
    lines += ["", "For this bank/order, the final measurement slightly worsens mean absolute error within PLS, while replacing the estimator accounts for the positive hybrid endpoint improvement. Neither bank's decomposition should be generalized to an untested bank or order.",
              "", "## Stopping objective with predictor and acquisition order fixed", "",
              "Primary analysis uses the consistent subset-PLS predictor. Separate logistic heads see identical acquired readings and masks, and use identical training effort. Each threshold is selected exclusively on its outer training-side calibration groups. A positive budget difference means the bank-reference objective spends more.",
              "", "| Held season | Bank-reference RMSEP / readings | Rich-reference RMSEP / readings | RMSEP difference [95% group CI] | Budget comparable? |",
              "|---|---:|---:|---:|---|"]
    for held in (1,2,3):
        rows=policy[(policy.bank=="swap_mid") & (policy.seed==42) & (policy.held_season==held) &
                    (policy.family=="pls") & (policy.operating_point=="scientific")].set_index("objective")
        a,b=rows.loc["two_reference"],rows.loc["single_reference"]
        c=comparisons[(comparisons.bank=="swap_mid") & (comparisons.seed==42) &
                      (comparisons.held_season==held) & (comparisons.family=="pls") &
                      (comparisons.comparison=="two_minus_single") &
                      (comparisons.operating_point=="scientific")].iloc[0]
        lines.append("| %d | %.4f / %.3f | %.4f / %.3f | %.4f [%.4f, %.4f] | %s |"%
                     (held,a.rmsep,a.mean_pulses,b.rmsep,b.mean_pulses,c.delta_rmsep,
                      c.rmsep_ci_low,c.rmsep_ci_high,"Yes" if c.budget_comparable else "No"))
    lines += ["", "Budget comparability requires an achieved mean-reading gap ≤0.25. Confidence intervals resample complete harvest populations (1000 draws); they describe sampled populations within a season, not new-season uncertainty. The calibration-selected target can transfer poorly. No threshold was changed to force a match on held outcomes.",
              "", "## Engineering screen and fixed acquisition", "",
              "| Held season | Bank-reference engineering RMSEP / readings | RMSEP increase vs full PLS | Both prototype conditions met? | Fixed-four RMSEP |",
              "|---|---:|---:|---|---:|"]
    for held in (1,2,3):
        rows=policy[(policy.bank=="swap_mid") & (policy.seed==42) & (policy.held_season==held) & (policy.family=="pls")]
        a=rows[(rows.objective=="two_reference") & (rows.operating_point=="engineering")].iloc[0]
        fixed=rows[(rows.objective=="fixed_length") & (rows.operating_point=="depth_4")].iloc[0]
        lines.append("| %d | %.4f / %.3f | %.4f | %s | %.4f |"%
                     (held,a.rmsep,a.mean_pulses,a.rmsep_increase_vs_bank,
                      "Yes" if a.evaluation_engineering_pass else "No",fixed.rmsep))
    lines += ["", "This screen requires at most +0.25 pp RMSEP versus full bank and at least 25% fewer readings. It does not certify the stricter v1 search constraints, physical energy savings, repeatability, or a deployable device. Calibration feasibility and held-season success are recorded separately in policy_metrics.csv.",
              "", "## Independent-bank sensitivity", "",
              "The uniform bank's bank-reference engineering policy passes both relative prototype conditions in all three held development seasons. This favorable sensitivity is retained. Its full-bank PLS comparator is weaker than the primary bank, especially in seasons 1 and 3; the pass therefore does not establish equivalent absolute accuracy or a general adaptive benefit.",
              "", "| Held season | Uniform adaptive RMSEP / readings | Uniform full-bank RMSEP | Uniform fixed-six RMSEP |",
              "|---|---:|---:|---:|"]
    for held in (1,2,3):
        rows=policy[(policy.bank=="uniform") & (policy.seed==42) & (policy.held_season==held) & (policy.family=="pls")]
        a=rows[(rows.objective=="two_reference") & (rows.operating_point=="engineering")].iloc[0]
        fixed=rows[(rows.objective=="fixed_length") & (rows.operating_point=="depth_6")].iloc[0]
        lines.append("| %d | %.4f / %.3f | %.4f | %.4f |"%
                     (held,a.rmsep,a.mean_pulses,a.bank_rmsep,fixed.rmsep))
    lines += ["", "Fixed-six PLS also passes both relative prototype conditions in all three seasons and has lower point-estimate RMSEP, with six readings for every scan. Adaptation saves about 0.06, 1.00 and 1.29 additional readings at RMSEP increases of about 0.010, 0.144 and 0.450 pp, respectively. Its reading count is comparable to the adaptive sensitivity in season 1 only; this is not an equal-budget superiority test in seasons 2 and 3. Every fixed length was included in advance; highlighting six here is descriptive and does not register it as a newly validated choice.",
              "", "The uniform scientific stopping-objective comparison is budget-comparable only in season 2: the two-reference-minus-single RMSEP difference is approximately +0.008 pp, with a 95% population-bootstrap interval spanning zero. The other uniform seasons are budget-incomparable. Thus the independent bank supplies a conditional relative-screen success, without establishing objective superiority.",
              "", "## Complete evidence and interpretation limits", "",
              "- Two banks are retained: prior primary swap_mid and independent catalog-only uniform. All primary-bank seeds 42, 7 and 99 are included. Subset PLS/ridge and logistic fitting are deterministic; these repeated seeds vary the reused MLP predictions, not independent data samples.",
              "- results/predictor_metrics.csv contains every subset-depth summary for training OOF, calibration and held data. Only held data support the seasonal performance assessment.",
              "- results/policy_metrics.csv and policy_predictions.csv.gz retain all four frozen objective/operating-point policies and fixed lengths 2–8, for all predictors and cases.",
              "- results/paired_comparisons.csv contains paired objective, fixed-four and exact-budget predictor differences; endpoint_summary.csv includes group confidence intervals on both endpoint components.",
              "- results/threshold_curves.csv retains every calibration and held-season point on the fixed grid. Held curves are descriptive; they do not reselect a policy.",
              "- Calibration mapping and threshold selection share reserved calibration groups. Held-season evaluation remains separate. Harvest groups substitute for missing verified fruit IDs.",
              "- The stopping-only learner is logistic regression on observed values and masks. This controlled comparison tests that specified learner and common order; it does not establish that the label distinction cannot help a different calibrated learner.",
              "- Rich-spectrum and full-bank errors remain model-relative comparisons. The finite-band LED emulator retains its documented optical approximations.",
              "", "This round introduces no learned channel-order search and promotes no deployment model. Its results identify whether prediction quality or the stopping objective warrants further development. Any revised method requires fresh independent seasonal validation before a confirmatory claim.",
              "", "## Reproduction", "",
              "Run .venv/bin/python revisions/methodology_v2/run.py all --resume. Reporting alone uses the report command and cannot fit models. The verify command independently recomputes metrics, checks split provenance, and verifies preservation of version 1. See verification_report.md for executed checks."]
    write_bytes(HERE / "decision_report.md", ("\n".join(lines)+"\n").encode())
