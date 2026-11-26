# Frozen-output diagnostic summaries

Retrospective descriptive diagnostics from frozen predictions; no fitting, threshold selection or outcome-driven change.

## Large errors despite reference agreement

|bank prediction - rich PLS prediction| <= 0.5 pp; |assay - policy prediction| > 2 pp.

| Season | Method | All scans | Reference agreement | Large errors within agreement | Conditional rate | Unconditional joint rate |
|---|---|---:|---:|---:|---:|---:|
| 4 | proposed | 1448 | 525 | 143 | 0.2724 | 0.0988 |
| 4 | single | 1448 | 525 | 150 | 0.2857 | 0.1036 |
| 5 | proposed | 320 | 27 | 6 | 0.2222 | 0.0187 |
| 5 | single | 320 | 27 | 5 | 0.1852 | 0.0156 |

The CSV/JSON retain every scored comparison and a separate stricter three-prediction agreement definition. These descriptions do not imply that agreement is a safe stopping rule.

## Paired examples

Each category uses the qualifying event nearest its within-season median gain, with row ID/depth tie-breaks. A missing category is reported as no qualifying event. Useful continuations must have actually occurred; missing single-policy depths are not imputed.

| Season | Category | Scan | Proposed / single final estimate | Proposed / single readings | Before / after actual continuation |
|---|---|---|---|---|---|
| 4 | premature_stop | v3_011625 | 14.996 / 14.996 | 2 / 2 | Not applicable |
| 4 | full_bank_limitation | v3_011677 | 16.561 / 16.561 | 2 / 2 | Not applicable |
| 4 | useful_continuation | v3_010912 | 14.742 / 14.742 | 8 / 8 | 16.397 / 14.742 |
| 5 | premature_stop | v3_011722 | 15.592 / 15.592 | 2 / 2 | Not applicable |
| 5 | full_bank_limitation | v3_011703 | 16.030 / 15.003 | 8 / 2 | Not applicable |
| 5 | useful_continuation | v3_011696 | 16.157 / 14.696 | 8 / 2 | 15.001 / 16.157 |

The JSON supplies assays, bank/rich references, signed gaps and both actual traces; all are evaluator-only diagnostics. These selected examples illustrate mechanisms and cannot establish average efficacy.

## Exact bank membership and calibration

`selected_bank_parts.csv` lists every role, its final seed-42 bank, installed position, initial-reading flag, real part ID, nominal and digitized center/width, modeled support, and source/profile hashes. The role assignments are development-selected.

`calibrator_summary.json` preserves the isotonic knots, sample/state counts, positive-label frequency, fitting Brier scores and selected scientific threshold for each final role bank. These are training-calibration diagnostics; external visited-state reliability remains in `calibration.json`.

No physical spectrum, detector noise, energy or timing has been measured by this report.
