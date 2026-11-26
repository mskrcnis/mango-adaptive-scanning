# Decision report

These are scan-level, simulated-acquisition results on reused public harvest-season benchmarks. Error units are dry-matter percentage points (pp). The first table uses the separately frozen scientific operating points.

| Season | Scans | Two-ref RMSEP | Single-ref RMSEP | Difference | Mean readings two / single | Within 0.25 pulse? | RMSEP increase vs bank | >=25% fewer readings? | <=0.25 pp increase? |
|---|---:|---:|---:|---:|---:|---|---:|---|---|
| 4 | 1448 | 2.672 | 2.752 | -0.081 | 3.096 / 2.365 | False | +1.440 | True | False |
| 5 | 320 | 1.997 | 2.171 | -0.174 | 4.809 / 2.369 | False | +0.753 | True | False |

## Did the objective help?

- Season 4: inconclusive: external budgets differ by more than 0.25 pulse. Material missed corrections: 755/1250 early stops.
- Season 5: inconclusive: external budgets differ by more than 0.25 pulse. Material missed corrections: 106/199 early stops.

| Season | RMSEP difference, 95% cluster interval (pp) | Reading difference, 95% cluster interval | Conditional missed-rate difference, 95% interval |
|---|---|---|---|
| 4 | -0.081; [-0.165, -0.014] | 0.731; [0.327, 1.194] | 0.012; [-0.015, 0.038] |
| 5 | -0.174; not estimated | 2.441; not estimated | 0.033; not estimated |

Season-5 harvest-population strata (no population-level interval):

| Population | Method | Scans | RMSEP (pp) | Mean readings | Missed / early stops |
|---|---|---:|---:|---:|---:|
| s5_pop128 | proposed | 160 | 2.251 | 4.950 | 60 / 100 |
| s5_pop128 | single | 160 | 2.326 | 2.225 | 80 / 158 |
| s5_pop129 | proposed | 160 | 1.706 | 4.669 | 46 / 99 |
| s5_pop129 | single | 160 | 2.005 | 2.513 | 77 / 156 |

Use `results/external_uncertainty.json` for paired harvest-population bootstrap intervals. Season 5 has only two populations, so no population-level confidence interval is reported. Three seeds describe training variability separately. A point-estimate advantage alone is not a robust generalization claim.

## Do these trade-offs justify a prototype?

The two illustrative external engineering criteria do not pass in both seasons. Development screening failed; the primary bank is the registered descriptive fallback.
The complete bank and rich-spectrum errors must also be considered: passing a relative bank criterion would not establish adequate absolute packhouse accuracy. No grower tolerance was independently established.

The separate frozen engineering operating point gives:

| Season | RMSEP (pp) | Increase vs full bank (pp) | Mean readings | Reading reduction | Accuracy criterion | Reading criterion |
|---|---:|---:|---:|---:|---|---|
| 4 | 1.261 | +0.029 | 7.942 | 0.73% | True | False |
| 5 | 1.244 | -0.000 | 8.000 | 0.00% | True | False |

Neither frozen operating point achieves both prototype criteria in both seasons. The scientific point saves readings but loses too much accuracy; the engineering point largely reads the complete bank.

## Simpler controls and failure mechanism

- Season 4: fixed ordering gives 2.690 pp at 3.046 readings (versus 2.672 pp at 3.096 for learned ordering). Fixed four-LED PLSR gives 1.242 pp and sparse SVR 2.361 pp.
- Season 5: fixed ordering gives 2.013 pp at 4.641 readings (versus 1.997 pp at 4.809 for learned ordering). Fixed four-LED PLSR gives 1.853 pp and sparse SVR 1.530 pp.
The ordering differences are descriptively small, and fixed-budget regressors expose substantial partial-prediction error. These results do not establish value for the extra adaptive controller complexity. Prioritize simpler fixed acquisition and improved prediction/calibration in a new development study; do not revise these frozen models using the external assays.

## Limits and next experiment

- No verified fruit identifiers: harvest populations are the grouping unit; repeated scans cannot establish unique fruit counts. Season 5 represents only two populations.
- Prior local experiments scored the same seasons. This is a locked new analysis of reused benchmarks, not fresh independent replication.
- The emulator uses digitized typical emitter plots and a flat detector/reference response. The F750 manual gives Log(1/Reflectance) without explicitly identifying the base; base 10 is the documented conventional assumption. Actual LED hardware measurements are required.
- Bank-loss gains combine optical information limitations and differences in model fitting. Generic CNN and separately adapted Walsh CNN are distinct references; no published score is presented as a matched local result.
- Two-step look-ahead is a conditional-Gaussian approximation, not the published ACO implementation. Hyperparameter search is deliberately bounded; full frontiers and unsuccessful models are retained.
- Six journal leads have verified metadata but unavailable full methods. Literature overlap with early-exit loss gaps, dynamic feature selection and adaptive spectroscopy prevents a claim of absolute originality or patentability.

A physical follow-up should acquire adaptive and fixed scans on the same newly collected mangoes, obtain oven-dry reference measurements, measure photodiode/detector response, emission profiles, optical SNR, pulse energy, total time and placement repeatability, and evaluate a genuinely later harvest season. Favor fixed ordering if its frozen trade-off is comparable. If bank error dominates, improve optical coverage or transfer calibration before optimizing stopping.

## Prior-art boundary

Jazbec et al. already formulate supervised early-versus-full loss gaps; Covert et al. learn conditional acquisition, Valancius et al. address non-greedy acquisition, and BAARC studies adaptive spectral acquisition. The contribution tested here is an empirical separation of bank-correctable error from richer-spectrum limitation. This is not a legal patent opinion; a specific implementation claim requires a jurisdiction-specific prior-art and claim analysis.

## Evidence

`results/external_predictions.csv`, `results/external_metrics.csv`, `results/frozen_curves.csv`, `results/external_uncertainty.json`, `results/selection.json`, `results/frozen/manifest.json`, and `docs/literature_audit.md`.
