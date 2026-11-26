# Frozen fixed-channel research candidate

Selected nominal centers: **720, 760, 820, 890, 910, 940 nm**.

Intended research use: estimate mango dry matter and assess limits for future harvest-timing support. No validated pick/wait rule is supplied.

Selection: 15 endpoint-preserving subsets; 94 leave-population-out folds on seasons 1–3. Final fitting: all 10,243 development scans. No independent accuracy claim is attached to this final fit.

Candidate: six-component autoscaled PLS on exactly six channels. Comparators: six-component full-eight PLS and twelve-component full-spectrum PLS with SNV and second derivative. All use identical fitting rows.

The optical integration weights describe simulated channels from digitized nominal emitter curves. Detector/reference responses are assumed flat. Physical instruments require separate calibration/transfer evidence; measured energy and timing are unavailable.

Dry matter is returned in percent fresh weight. Application error tolerance, cultivar/market harvest threshold, and prospective sampling plan remain unresolved. No per-fruit uncertainty interval or calibrated decision probability is provided.

Use portable_models.json with inference.py for sparse inference; models.joblib is the fitted reference for trusted-local verification. Do not unpickle unknown external model files.

The local manifest verifies file integrity. New fitting dependencies or physical recalibration require a new version.
