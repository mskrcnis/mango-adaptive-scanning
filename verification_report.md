# Final verification report

**Verification: passed. Computational scope: completed.**

The verifier does not refit research models or reopen sealed external assays. It recomputes claims from the already-scored prediction table. Tiny synthetic networks inside the contract-test suite are software fixtures only.

| Check | Status | Evidence |
|---|---|---|
| frozen_manifest_and_nested_hashes | passed | Recorded in results/verification.json |
| completed_external_output_hashes | passed | Recorded in results/verification.json |
| reporting_only_guarded_rerun | passed | Recorded in results/verification.json |
| real_data_reader_and_source_contracts | passed | Recorded in results/verification.json |
| software_contract_tests | passed | Recorded in results/verification.json |
| registered_partitions_and_all_oof_checkpoints | passed | Recorded in results/verification.json |
| walsh_and_static_reference_training_boundaries | passed | Recorded in results/verification.json |
| real_development_runtime_and_optical_contracts | passed | Recorded in results/verification.json |
| normal_cli_replay_entrypoint | passed | Recorded in results/verification.json |
| normal_app_entrypoint | passed | Recorded in results/verification.json |
| app_cli_manual_trace_equivalence | passed | Recorded in results/verification.json |
| saved_prediction_table_loaded | passed | Recorded in results/verification.json |
| comparison_completeness_and_duplicate_exclusion | passed | Recorded in results/verification.json |
| every_manuscript_cell_recomputed | passed | Recorded in results/verification.json |
| uncertainty_and_calibration_denominators | passed | Recorded in results/verification.json |
| all_saved_trace_information_boundaries | passed | Recorded in results/verification.json |
| interruption_and_current_frozen_resume | passed | Recorded in results/verification.json |
| required_deliverables | passed | Recorded in results/verification.json |
| pdf_structure_text_and_placeholder_checks | passed | Recorded in results/verification.json |
| rendered_pdf_visual_qa | passed | Recorded in results/verification.json |
| final_frozen_and_external_hash_recheck | passed | Recorded in results/verification.json |

## Executed commands

| Invocation | Return code | Captured output |
|---|---:|---|
| `/home/mskr/Research/Agro/Mango/.venv/bin/python -m results.data_audit.verify_data` | 0 | `results/verification_logs/data_audit.log` |
| `/home/mskr/Research/Agro/Mango/.venv/bin/python -m pytest -q tests` | 0 | `results/verification_logs/pytest.log` |
| `python3 run_project.py replay --example --trace-output results/verification_cli_trace.json` | 0 | `results/verification_logs/cli_replay.log` |
| `python3 run_project.py app --self-test` | 0 | `results/verification_logs/app_self_test.log` |
| `pdfinfo manuscript/main.pdf` | 0 | `results/verification_logs/main_pdfinfo.log` |
| `pdftotext -layout manuscript/main.pdf -` | 0 | `results/verification_logs/main_pdftotext.log` |
| `pdfinfo manuscript/supplement.pdf` | 0 | `results/verification_logs/supplement_pdfinfo.log` |
| `pdftotext -layout manuscript/supplement.pdf -` | 0 | `results/verification_logs/supplement_pdftotext.log` |

Python checks also inspect every saved OOF model checkpoint, execute real development invariance checks, replay every saved external trace, rerun the frozen scorer with data readers disabled, and guard reporting against fitting. Reporting-only evidence is reused only when its exact dependencies and generated artifact hashes still match.

## Scope and unresolved evidence

- No physical acquisition, noise, energy, timing or repeatability measurements.
- Six journal full-method sources remain unavailable; source audit records verified scope.
- Instrument logarithm base is conventional base 10, not explicitly firmware-verified.
- Fruit identities are unavailable; harvest groups constrain but cannot prove identity isolation.
- External seasons were used in earlier local work and are reused benchmarks.
- Author declarations remain pending; no release, submission, purchase or patent filing occurred.
- Live app screenshot inspection was attempted but the CUA browser access host was unavailable (results/app_visual_qa.json). Normal app HTTP, manual-entry and trace-export checks are recorded separately in results/app_test.json; optional screenshot unavailability is not a failed computational check.

Computational completion does not mean an engineering criterion passed or that the proposed objective improved prediction. Scientific outcomes and budget comparability are reported in `decision_report.md`. Missing physical measurements and inaccessible full texts are evidence limits, not completed experimental stages.

The interrupted-training resume evidence is explicitly from the preserved preliminary run before bank-design isolation. Separate development-fixture interruption recovery and current frozen-scorer resume evidence are checked. No interrupted job is relabeled complete merely because newer results exist.

Machine-readable evidence: `results/verification.json`; all command outputs: `results/verification_logs/`.
