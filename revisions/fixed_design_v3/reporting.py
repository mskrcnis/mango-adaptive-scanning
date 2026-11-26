"""Report the locked fixed-design round without selecting or fitting anything."""
import io
import json
from itertools import combinations

import joblib
import numpy as np
import pandas as pd

from revisions.methodology_v2.reporting import csv, write_bytes, paired_bootstrap
from revisions.methodology_v2.stopping import evaluate_stopping, _metrics
from .pipeline import HERE, OUT, CASES, FAMILIES, features_from_full, event


def report():
    scores, predictions, curves, comparisons = [], [], [], []
    mask_scores, order_scores, chosen, composition, stability = [], [], [], [], []
    designs={}
    for held,bank in CASES:
        case=joblib.load(OUT/"checkpoints"/("evaluation_s%d_%s.joblib"%(held,bank)))
        design=joblib.load(OUT/"checkpoints"/("design_s%d_%s.joblib"%(held,bank)))
        designs[(held,bank)]=design
        data=case["data"]["valid"]
        y,groups=data["y"],data["groups"]
        for row in design["composition"]:
            composition.append(dict(held_season=held,bank=bank,**row))
        for family in FAMILIES:
            base={"held_season":held,"bank":bank,"family":family}
            selection=design["selections"][family]
            centers=design["centers_nm"]
            masks=case["masks"]
            for row in selection["mask_scores"]:
                mask_scores.append(dict(base,mask_index=row["mask_index"],depth=row["depth"],
                    indices=",".join(map(str,row["indices"])),
                    centers_nm=",".join(str(centers[i]) for i in row["indices"]),
                    mse=row["mse"],rmsep=row["rmsep"],
                    selected=selection["by_depth"][str(row["depth"])]==row["mask_index"]))
            for row in selection["order_scores"]:
                order_scores.append(dict(base,order=",".join(map(str,row["order"])),score=row["score"],
                    path_indices=",".join(map(str,row["path_indices"])),
                    selected=row["order"]==selection["order"]))
            order=selection["order"]
            row=dict(base,order=",".join(map(str,order)),
                     order_nm=",".join(str(centers[i]) for i in order),
                     catalog_order_nm=",".join(str(centers[i]) for i in selection["catalog_order"]),
                     order_margin=selection["order_margin"],order_score=selection["order_score"],
                     catalog_order_score=selection["catalog_order_score"],
                     n_design_groups=design["crossfit"]["n_groups"],n_design_scans=design["crossfit"]["n"])
            for depth in (4,6):
                subset=np.flatnonzero(masks[selection["by_depth"][str(depth)]])
                row["selected_%d_nm"%depth]=",".join(str(centers[i]) for i in subset)
                row["ordered_%d_nm"%depth]=",".join(str(centers[i]) for i in order[:depth])
                row["subset_%d_margin"%depth]=selection["by_depth_second_best_mse_margin"][str(depth)]
            chosen.append(row)
            policies={}
            item=case["families"][family]
            for variant,entry in item["orders"].items():
                paths=entry["paths"]
                features=features_from_full(case["full_features"]["valid"],masks,entry["path_indices"])
                evaluated=evaluate_stopping(entry["stopping"],features,paths["valid"],paths["valid"][:,-1],
                                             data["rich"],y)
                scores.extend(dict(base,variant=variant,**r) for r in
                              evaluated["records"]+evaluated["fixed_length_controls"])
                for key,value in evaluated["policies"].items():
                    objective,point=key.split("|")
                    if objective=="fixed_length":
                        point="depth_"+point
                    policies[(variant,objective,point)]=value
                for objective,rows in evaluated["frontiers"].items():
                    curves.extend(dict(base,variant=variant,split="valid",**r) for r in rows)
                for objective,rows in entry["stopping"]["calibration_frontier"].items():
                    curves.extend(dict(base,variant=variant,split="cal",**r) for r in rows)
            fixed=item["fixed_subset_paths"]["valid"]
            bank_prediction=fixed[:,-1]
            for j,depth in enumerate(range(2,9)):
                pulses=np.full(len(y),depth)
                value={"predictions":fixed[:,j],"pulses":pulses}
                policies[("selected_subset","fixed_length","depth_"+str(depth))]=value
                scores.append(dict(base,variant="selected_subset",objective="fixed_length",
                    operating_point="depth_"+str(depth),fixed_depth=depth,
                    **_metrics(y,value["predictions"],pulses,bank_prediction,data["rich"],.5)))
            for (variant,objective,point),value in policies.items():
                frame=pd.DataFrame({"row_id":data["row_ids"],"group":groups,"y":y,
                    "prediction":value["predictions"],"pulses":value["pulses"],
                    "bank_prediction":bank_prediction,"rich_prediction":data["rich"]})
                for name,val in dict(base,variant=variant,objective=objective,operating_point=point).items():
                    frame[name]=val
                predictions.append(frame)
            def compare(name,point,key_a,key_b):
                a,b=policies[key_a],policies[key_b]
                comparisons.append(dict(base,comparison=name,operating_point=point,
                    **paired_bootstrap(groups,y,a["predictions"],b["predictions"],a["pulses"],b["pulses"])))
            for depth in (4,6):
                point="depth_"+str(depth)
                b=("catalog","fixed_length",point)
                compare("designed_fixed_minus_catalog",point,("designed","fixed_length",point),b)
                compare("selected_subset_minus_catalog",point,("selected_subset","fixed_length",point),b)
            for point,depth in (("scientific",4),("engineering",6)):
                compare("two_minus_single",point,("designed","two_reference",point),("designed","single_reference",point))
                compare("adaptive_minus_selected_subset",point,("designed","two_reference",point),
                        ("selected_subset","fixed_length","depth_"+str(depth)))
    for bank in ("swap_mid","uniform"):
        for family in FAMILIES:
            for a,b in combinations((1,2,3),2):
                da,db=designs[(a,bank)],designs[(b,bank)]
                for variant in ("designed","selected_subset"):
                    for depth in range(2,9):
                        sets=[]
                        for d in (da,db):
                            s=d["selections"][family]
                            indices=s["order"][:depth] if variant=="designed" else np.flatnonzero(
                                d["crossfit"]["masks"][s["by_depth"][str(depth)]])
                            sets.append(set(indices))
                        stability.append({"bank":bank,"family":family,"variant":variant,"depth":depth,
                            "held_a":a,"held_b":b,"jaccard":len(sets[0]&sets[1])/len(sets[0]|sets[1])})
    frames={name:pd.DataFrame(rows) for name,rows in
            [("metrics",scores),("threshold_curves",curves),("comparisons",comparisons),
             ("design_subsets",mask_scores),("design_orders",order_scores),("selected_designs",chosen),
             ("design_composition",composition),("selection_stability",stability)]}
    for name,frame in frames.items():
        csv(OUT/(name+".csv"),frame)
    csv(OUT/"predictions.csv.gz",pd.concat(predictions,ignore_index=True),compressed=True)
    make_report(frames)
    make_figures(frames)
    event("Reporting complete: every locked subset/order and all 348 evaluation policies retained.")


def get_row(frame,held,bank="swap_mid",family="pls",variant="designed",objective="fixed_length",point="depth_4"):
    rows=frame[(frame.held_season==held)&(frame.bank==bank)&(frame.family==family)&
               (frame.variant==variant)&(frame.objective==objective)&(frame.operating_point==point)]
    assert len(rows)==1
    return rows.iloc[0]


def make_report(frames):
    m,c,d=frames["metrics"],frames["comparisons"],frames["selected_designs"]
    primary=c[(c.bank=="swap_mid")&(c.family=="pls")&(c.comparison=="designed_fixed_minus_catalog")&
              (c.operating_point=="depth_4")]
    improved=int((primary.delta_rmsep<0).sum())
    resolved=int((primary.rmsep_ci_high<0).sum())
    lines=["# Fixed-subset and acquisition-order study: results", "",
           "Completed one locked, development-only follow-up. Versions 1 and 2 are preserved. All channel choices used reserved design groups; all six bank/held-season designs were locked before source evaluation arrays were parsed. Seasons 4 and 5 were not loaded or rescored. These repeatedly used development seasons provide exploratory evidence.",
           "", "The primary PLS bank supports improving fixed channel selection/order. The prespecified fixed-six procedure passes the relative engineering screen in all three seasons with 25% fewer simulated readings than the eight-channel reference. The proposed bank-reference stopping objective adds no demonstrated advantage. Prioritize a fixed-channel candidate for fresh validation; no universal configuration or deployment claim is established.",
           "", "## Primary result: identical four-reading budgets", "",
           "The design-selected PLS order lowers RMSEP relative to the catalog-only order in %d of 3 held development seasons; %d of 3 paired population-bootstrap intervals lie entirely below zero. These comparisons use exactly four readings on both sides, with the same fitted predictor family, initial channels and installed bank."%(improved,resolved),
           "", "| Held season | Catalog order RMSEP | Designed order RMSEP | Selected fixed-four RMSEP | Full-bank RMSEP | Designed minus catalog [95% CI] |",
           "|---|---:|---:|---:|---:|---:|"]
    for held in (1,2,3):
        a=get_row(m,held,variant="catalog")
        b=get_row(m,held)
        s=get_row(m,held,variant="selected_subset")
        q=primary[primary.held_season==held].iloc[0]
        lines.append("| %d | %.4f | %.4f | %.4f | %.4f | %.4f [%.4f, %.4f] |"%
                     (held,a.rmsep,b.rmsep,s.rmsep,b.bank_rmsep,q.delta_rmsep,q.rmsep_ci_low,q.rmsep_ci_high))
    lines+=["", "RMSEP is in dry-matter percentage points. Selected fixed-four subsets minimize their own design MSE; they can differ from the four-channel prefix of the globally selected nested order. The latter minimizes the sum of design MSE over depths 2–7, not four-channel error alone.",
            "", "## Selected channels and repeatability across design splits", "",
            "| Held season | Selected PLS order, nm | Independent fixed-four subset, nm | Independent fixed-six subset, nm |",
            "|---|---|---|---|"]
    for _,r in d[(d.bank=="swap_mid")&(d.family=="pls")].iterrows():
        lines.append("| %d | %s | %s | %s |"%(r.held_season,r.order_nm,r.selected_4_nm,r.selected_6_nm))
    lines+=["", "Each row is a separate training-side design. No universal order or device was chosen from held outcomes. Selection is constrained to the two existing eight-channel banks and fixed endpoint pair; this is not a global wavelength optimum.",
            "", "## Engineering screen at fixed budgets", "",
            "The screen requires RMSEP no more than 0.25 pp above the same full-bank reference and at most six readings. Absolute errors remain relevant even when a relative screen passes.",
            "", "| Held season | Designed fixed-four: RMSEP / pass | Selected fixed-four: RMSEP / pass | Selected fixed-six: RMSEP / pass |",
            "|---|---:|---:|---:|"]
    pass_counts={"designed4":0,"selected4":0,"selected6":0}
    for held in (1,2,3):
        cells=[]
        for key,variant,point in (("designed4","designed","depth_4"),("selected4","selected_subset","depth_4"),
                                  ("selected6","selected_subset","depth_6")):
            r=get_row(m,held,variant=variant,point=point)
            passed=r.rmsep_increase_vs_bank<=.25 and r.mean_pulses<=6
            pass_counts[key]+=int(passed)
            cells.append("%.4f / %s"%(r.rmsep,"yes" if passed else "no"))
        lines.append("| %d | %s |"%(held," | ".join(cells)))
    lines+=["", "Primary-bank passes across the three held seasons: designed fixed-four %d/3; independently selected fixed-four %d/3; independently selected fixed-six %d/3."%
            (pass_counts["designed4"],pass_counts["selected4"],pass_counts["selected6"]),
            "", "The fixed-six result is a prespecified engineering sensitivity, not a claim that six readings is the optimum among all reported lengths. Its selected wavelengths differ across design splits. Absolute accuracy for this procedure is:",
            "", "| Held season | Fixed-six RMSEP | Full-eight RMSEP | Fixed-six MAE | Signed bias | Scans with absolute error above 2 pp |",
            "|---|---:|---:|---:|---:|---:|"]
    for held in (1,2,3):
        r=get_row(m,held,variant="selected_subset",point="depth_6")
        lines.append("| %d | %.4f | %.4f | %.4f | %+.4f | %.1f%% |"%
                     (held,r.rmsep,r.bank_rmsep,r.mae,r.bias,100*r.large_absolute_error_rate))
    lines+=["", "No independently justified application tolerance or physical instrument measurement establishes deployment suitability. Fewer simulated readings do not establish measured energy, latency or hardware savings.",
            "", "## Does stopping add evidence beyond a better fixed order?", "",
            "The logistic stopping learner, two objective definitions and calibration rules are unchanged from revision 2. Catalog stoppers were reused only after exact feature/path checks; designed-order stoppers use core OOF targets and separate calibration groups.",
            "", "| Held season | Designed bank-reference RMSEP / readings | Designed rich-reference RMSEP / readings | Paired RMSEP difference [95% CI] | Budget comparable? |",
            "|---|---:|---:|---:|---|"]
    for held in (1,2,3):
        a=get_row(m,held,objective="two_reference",point="scientific")
        b=get_row(m,held,objective="single_reference",point="scientific")
        q=c[(c.held_season==held)&(c.bank=="swap_mid")&(c.family=="pls")&
            (c.comparison=="two_minus_single")&(c.operating_point=="scientific")].iloc[0]
        lines.append("| %d | %.4f / %.3f | %.4f / %.3f | %.4f [%.4f, %.4f] | %s |"%
                     (held,a.rmsep,a.mean_pulses,b.rmsep,b.mean_pulses,q.delta_rmsep,q.rmsep_ci_low,
                      q.rmsep_ci_high,"yes" if q.budget_comparable else "no"))
    lines+=["", "All three scientific comparisons are within the registered 0.25-reading margin, but their achieved budgets are not exactly equal. The bank-reference objective has higher RMSEP in all three seasons; the paired intervals exclude zero in seasons 2 and 3. This provides no support for its proposed advantage. Frozen threshold curves are descriptive and never used to retune held-season points.",
            "", "| Held season | Bank-reference engineering RMSEP / readings | Both engineering conditions met? | Selected fixed-six RMSEP |",
            "|---|---:|---|---:|"]
    for held in (1,2,3):
        a=get_row(m,held,objective="two_reference",point="engineering")
        b=get_row(m,held,variant="selected_subset",point="depth_6")
        lines.append("| %d | %.4f / %.3f | %s | %.4f |"%(held,a.rmsep,a.mean_pulses,
                    "yes" if a.evaluation_engineering_pass else "no",b.rmsep))
    lines+=["", "The adaptive engineering policies use fewer readings than fixed-six but have higher RMSEP. This is an accuracy versus acquisition-effort trade-off, not evidence of adaptive superiority at equal cost.",
            "", "## Independent bank and ridge sensitivity", "",
            "Every bank/family combination has its own design choices. Consequently these rows are complete pipeline sensitivities, not matched-subset predictor-family comparisons.",
            "", "| Bank / predictor | Held season | Catalog fixed-four | Designed fixed-four | Selected fixed-four | Selected fixed-six | Full bank |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for bank,family in (("uniform","pls"),("swap_mid","ridge"),("uniform","ridge")):
        for held in (1,2,3):
            rows=[get_row(m,held,bank,family,variant=v,point=p) for v,p in
                  (("catalog","depth_4"),("designed","depth_4"),("selected_subset","depth_4"),("selected_subset","depth_6"))]
            lines.append("| %s / %s | %d | %.4f | %.4f | %.4f | %.4f | %.4f |"%
                         (bank,family,held,*[r.rmsep for r in rows],rows[0].bank_rmsep))
    lines+=["", "The large primary-bank PLS improvement is not consistently reproduced by the uniform bank or ridge sensitivity. These results do not establish a general advantage across optical designs or predictor families.",
            "", "## Evidence limits and disposition", "",
            "- Design folds contain only 9, 9 and 6 populations (998, 953 and 857 scans). Leave-one-population-out fitting retains 8, 8 and 5 training populations. Pooled scan MSE weights large populations and represented seasons more heavily; counts are retained in design_composition.csv.",
            "- For the held-season-1 design, 958 of 998 scans are from season 3. The other design sets are also uneven. Exhaustive 64-subset/720-order minima are tuning results, not validation scores. Reported uncertainty is conditional on selected designs and fitted models.",
            "- Confidence intervals resample complete harvest populations 1000 times with seed 42. They do not describe selection uncertainty, unknown fruit identities, future seasons, or multiplicity-adjusted evidence.",
            "- All 64 masks and 720 orders per family/case are saved; all fixed lengths and frozen stopping curves are retained. No new bank, initial pair, learner, threshold grid or refinement was added after inspecting scores.",
            "- Independently selected fixed subsets need not be nested. They are scored as separate fixed-budget devices, never passed off as an adaptive acquisition path.",
            "- Full-bank and rich-spectrum references remain fitted-model comparators, not irreducible optical limits. Optical channels are simulated from documented emitter profiles, with the inherited detector/log-base limitations.",
            "", "No revised deployment policy or universal LED configuration is promoted. The exact-budget fixed-design contrasts determine whether the earlier poor order was an avoidable source of error. Any selected configuration must be frozen using development data and evaluated on genuinely new seasonal and physical measurements before a confirmatory or hardware-performance claim.",
            "", "## Reproduction and artifacts", "",
            "Run .venv/bin/python revisions/fixed_design_v3/run.py all --resume. Separate design, evaluate, report, verify and status commands are available.",
            "", "results/design_lock.json records the six complete designs before evaluation. results/design_subsets.csv and design_orders.csv retain the entire search. selected_designs.csv and selection_stability.csv record memberships and fold differences. metrics.csv, predictions.csv.gz, threshold_curves.csv and comparisons.csv retain every scored result. See verification_report.md for independent checks, preservation and resume evidence."]
    write_bytes(HERE/"decision_report.md",("\n".join(lines)+"\n").encode())


def save_figure(fig,name):
    for extension in ("png","pdf"):
        buffer=io.BytesIO()
        kwargs={"dpi":180} if extension=="png" else {"metadata":{"CreationDate":None,"ModDate":None}}
        fig.savefig(buffer,format=extension,bbox_inches="tight",**kwargs)
        write_bytes(HERE/"figures"/(name+"."+extension),buffer.getvalue())


def make_figures(frames):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    m=frames["metrics"]
    fig,axes=plt.subplots(1,3,figsize=(12,3.4),sharex=True,sharey=True)
    for held,ax in enumerate(axes,1):
        rows=m[(m.bank=="swap_mid")&(m.family=="pls")&(m.held_season==held)&(m.objective=="fixed_length")]
        for variant,label,color,style in (("catalog","Catalog order","#777777","s--"),
                                         ("designed","Design-selected order","#1b6c8e","o-"),
                                         ("selected_subset","Independent fixed subsets","#b24d31","D")):
            r=rows[rows.variant==variant].sort_values("fixed_depth")
            ax.plot(r.fixed_depth,r.rmsep,style,label=label,color=color)
        ax.set(title="Held development season %d"%held,xlabel="Fixed number of readings",xticks=range(2,9))
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Dry-matter RMSEP (percentage points)")
    axes[1].legend(loc="upper center",bbox_to_anchor=(.5,-.24),ncol=3,frameon=False)
    fig.suptitle("PLS on primary bank • choices made only in reserved design groups",y=1.03)
    save_figure(fig,"fixed_design_curves");plt.close(fig)
    c=frames["threshold_curves"]
    fig,axes=plt.subplots(1,3,figsize=(12,3.4),sharex=True,sharey=True)
    for held,ax in enumerate(axes,1):
        rows=c[(c.bank=="swap_mid")&(c.family=="pls")&(c.variant=="designed")&
               (c.split=="valid")&(c.held_season==held)]
        for objective,label,color in (("two_reference","Bank-reference stop","#1b6c8e"),
                                      ("single_reference","Rich-reference stop","#b24d31")):
            r=rows[rows.objective==objective]
            ax.plot(r.mean_pulses,r.rmsep,".-",label=label,color=color)
            point=get_row(m,held,objective=objective,point="scientific")
            ax.scatter([point.mean_pulses],[point.rmsep],s=90,marker="*",color=color,zorder=5)
        r=m[(m.bank=="swap_mid")&(m.family=="pls")&(m.variant=="selected_subset")&(m.held_season==held)]
        ax.scatter(r.mean_pulses,r.rmsep,marker="D",color="#555555",s=25,label="Selected fixed subsets")
        ax.set(title="Held development season %d"%held,xlabel="Mean simulated readings",xticks=range(2,9))
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Dry-matter RMSEP (percentage points)")
    axes[1].legend(loc="upper center",bbox_to_anchor=(.5,-.24),ncol=3,frameon=False)
    fig.suptitle("Stopping on the design-selected PLS order • stars: frozen target-budget points",y=1.03)
    save_figure(fig,"designed_stopping_frontiers");plt.close(fig)
