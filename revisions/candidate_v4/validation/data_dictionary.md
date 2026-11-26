# Prospective collection and validation data dictionary

These are header-only software input templates. No observations, assays, predictions or harvest decisions have been recorded. Copy them into a separate study archive; preserve this template package. The protocol controls eligibility, blinding, aggregation and interpretation.

## Conventions

- Encode UTF-8 CSV with one header row; preserve identifiers as strings and do not recycle them. Dates use ISO 8601; timestamps use UTC with a Z suffix. Booleans are lowercase true/false. Hashes are 64 lowercase hexadecimal SHA-256 characters.
- Empty fields mean unavailable or not yet assigned, never zero. Record required missingness reasons. Do not use invented values, NaN strings or a numeric sentinel.
- Prefix all identifiers with a study namespace; all cross-file joins use study_id plus the named key. Every fruit belongs to one recorded population and one independent analysis cluster. All repeated scans remain linked to the same fruit.
- Files ending _restricted.csv contain assay values or their linkage. Keep them inaccessible to model-prediction production until the prediction manifest is frozen. Do not put assays in scan metadata.
- A frozen study must replace draft/pending fields with its registered choices before the relevant stage. Readiness fields may stay null only where the protocol explicitly permits descriptive research without a practical acceptance claim.
- Replay spectra require one row per scan/wavelength in spectral_values.csv, exactly the frozen grid and representation. Raw files are retained separately; the candidate inference input adapter must be checked against the final model manifest. No interpolation or unit conversion is implied by this template.
- Structural keys: population_id, fruit_id and scan_id are unique within their respective study tables. Spectral keys are (study_id, scan_id, wavelength_nm). Prediction keys are (study_id, scan_id, model_id) and (study_id, fruit_id, model_id). Assay linkage is one-to-one between a fruit and its reconciled laboratory sample. Every reference is traceable to retained aliquots.
- Schemas describe intake/custody, not executable enforcement. Validate keys, hashes, chronology, finite inputs and allowed categories before use; presence of a row does not verify its truth.

## File fields

### populations.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| season_id | string | New season identifier; not original dataset seasons 1–5. |
| population_id | string | Unique harvest population; stable across all linked files. |
| analysis_cluster_id | string | Independent population cluster used for resampling; shared where populations are dependent. |
| orchard_or_supplier_id | string | Pseudonymous source identifier; retain linkage under custody. |
| block_or_lot_id | string | Source block or lot identifier. |
| cultivar | string | Recorded cultivar, not inferred from spectra. |
| harvest_window_start | date | ISO 8601 date. |
| harvest_window_end | date | ISO 8601 date. |
| recruitment_rule_id | string | Registered recruitment rule. |
| independence_attestation_id | string | Evidence that original seasons 1–5 and shared fruit/derived observations are excluded. |

### fruits.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| fruit_id | string | Unique physical fruit identifier, never a scan identifier. |
| population_id | string | Foreign key to populations.csv. |
| enrolled_at_utc | datetime | ISO 8601 UTC with Z suffix. |
| harvested_at_utc | datetime | Actual harvest time; empty when not known, with a documented reason. |
| collection_site | string | Collection site, using registered categories. |
| handling_protocol_id | string | Registered handling/storage procedure. |
| eligibility_status | enum | eligible, ineligible, or pending; determined without model errors. |
| eligibility_reason | string | Required reason for noneligible or pending status. |
| disposition | enum | enrolled, withdrawn, lost, or analyzed; preserve all recruited fruit. |

### scans.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| scan_id | string | Globally unique scan identifier. |
| fruit_id | string | Foreign key to fruits.csv. |
| scanned_at_utc | datetime | ISO 8601 UTC scan timestamp. |
| instrument_id | string | Instrument and calibration record identifier. |
| measurement_mode | enum | spectral_replay or physical_device; do not pool modes. |
| scan_site | string | Registered position on fruit. |
| repeat_index | integer | One-based repeat index within fruit/site. |
| raw_file_path | string | Relative path under the source archive; no external traversal. |
| raw_file_sha256 | sha256 | Lowercase SHA-256 of unmodified source bytes. |
| spectral_schema_id | string | Frozen wavelength grid, units and signal-representation schema. |
| acquisition_protocol_id | string | Frozen acquisition procedure. |
| qc_status | enum | pass, fail, or pending based on registered outcome-independent rules. |
| qc_reason_code | string | Required for fail or pending; rule IDs must be registered. |

### spectral_values.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| scan_id | string | Foreign key to scans.csv. |
| wavelength_nm | number | Wavelength in nm; exact frozen grid required for replay. |
| signal_value | number | Finite untransformed supplied input value in declared representation. |
| signal_representation | string | Frozen input representation; do not silently change log or absorbance convention. |

### assay_aliquots_restricted.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| lab_sample_id | string | Blinded laboratory sample identifier; no model predictions supplied. |
| aliquot_id | string | Unique technical aliquot ID. |
| fresh_mass_g | number | Positive recorded fresh sample mass in grams. |
| dry_mass_g | number | Recorded dry sample mass in grams under assay SOP. |
| assay_method_id | string | Frozen validated reference SOP/version. |
| assay_batch_id | string | Laboratory batch identifier. |
| drying_endpoint_record | string | Evidence required by assay SOP; do not invent a fixed drying duration. |
| assayed_at_utc | datetime | ISO 8601 UTC timestamp. |
| assay_qc_status | enum | pass, fail, or pending under frozen laboratory rules. |
| assay_qc_reason | string | Required for fail or pending. |

### assay_references_restricted.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| lab_sample_id | string | One reconciled reference per blinded laboratory sample. |
| reference_dm_percent | number | Fresh-weight dry matter percent, from 100 * dry_mass / fresh_mass and registered reconciliation. |
| reconciliation_rule_id | string | Frozen rule resolving technical replicates; do not choose best agreement with predictions. |
| reference_qc_status | enum | pass, fail, or pending. |
| reference_qc_reason | string | Required for fail or pending. |
| assay_archive_sha256 | sha256 | Hash of retained laboratory aliquot archive. |
| assay_frozen_at_utc | datetime | Reference freeze time before model-linkage release. |

### assay_linkage_restricted.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| fruit_id | string | Foreign key to fruits.csv. |
| lab_sample_id | string | Foreign key to assay_references_restricted.csv. |
| custodian_id | string | Person/role controlling linkage release. |
| released_at_utc | datetime | Release time after predictions have been frozen. |
| prediction_freeze_id | string | Foreign key to an immutable prediction freeze. |
| prediction_manifest_sha256 | sha256 | Hash of complete frozen prediction manifest before linkage. |

### scan_predictions.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| scan_id | string | Foreign key to scans.csv. |
| fruit_id | string | Must agree with scan-to-fruit metadata. |
| model_id | enum | fixed_six, full_eight, or rich_spectrum. |
| model_bundle_sha256 | sha256 | Hash identifying frozen bundle used at inference. |
| predicted_dm_percent | number_or_empty | Finite dry-matter prediction; empty only for a logged prediction failure. |
| prediction_status | enum | success or failure. |
| failure_reason | string | Required for failure; never substitute zero for a failure. |
| predicted_at_utc | datetime | Prediction timestamp before assay linkage. |

### fruit_predictions.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| fruit_id | string | One row per fruit/model for aggregation. |
| model_id | enum | fixed_six, full_eight, or rich_spectrum. |
| model_bundle_sha256 | sha256 | Hash identifying the frozen inference bundle. |
| mean_predicted_dm_percent | number_or_empty | Arithmetic mean of common eligible scan predictions; empty when fruit unavailable. |
| eligible_paired_scan_count | integer | Same retained scan set across all three models for a fruit. |
| scan_prediction_sd_pp | number_or_empty | Descriptive repeat variation; empty with fewer than two scans. |
| availability_status | enum | available or unavailable under registered minimum scan count. |
| availability_reason | string | Required if unavailable. |
| prediction_freeze_id | string | Immutable freeze identifier before assay linkage. |

### qc_dispositions.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| record_type | enum | fruit, scan, assay, or source. |
| record_id | string | Identifier in corresponding retained table. |
| rule_id | string | Registered outcome-independent QC rule. |
| decision | enum | retain, exclude, or quarantine. |
| reason | string | Human-readable evidence for decision. |
| decided_at_utc | datetime | Timestamp of QC decision. |
| decided_by_role | string | Role making the decision. |
| validation_outcomes_accessed | boolean | true or false; true requires protocol-deviation disclosure. |

### freeze_manifest.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| freeze_id | string | Immutable stage freeze identifier. |
| stage | enum | registration, model, inputs, qc, scan_predictions, fruit_predictions, assays, linkage, or analysis. |
| artifact_path | string | Relative archive path. |
| artifact_sha256 | sha256 | SHA-256 of exact frozen bytes. |
| frozen_at_utc | datetime | UTC timestamp. |
| custodian_id | string | Responsible custodian or automated process. |
| prior_freeze_id | string | Earlier immutable freeze if this is an amendment; empty otherwise. |
| amendment_reason | string | Required if superseding a prior freeze; preserve prior artifact. |

### independence_checks.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Registered study identifier. |
| source_id | string | Prospective source or archive identifier. |
| source_sha256 | sha256 | Hash of original source artifact. |
| lineage_evidence | string | Origin, date and custody evidence beyond filename. |
| old_dataset_overlap_check | enum | clear, overlap, or unresolved. |
| duplicate_check_method | string | Byte hashes plus fruit/source lineage review; spectral similarity if registered. |
| duplicate_check_result | string | Retain exact findings, including ambiguous transformed duplicates. |
| decision | enum | eligible, ineligible, or quarantine. |
| reviewer_role | string | Attestation/review role. |
| reviewed_at_utc | datetime | UTC timestamp. |

### harvest_observations_optional.csv

| Field | Type | Meaning |
|---|---|---|
| study_id | string | Separate registered harvest study identifier. |
| observation_id | string | Unique field/quality observation identifier. |
| fruit_id | string | Physical fruit identifier; do not pretend matched fruit are identical. |
| population_id | string | Prospective field population. |
| paired_or_sentinel_fruit_id | string | Matched/sentinel fruit if destructive assay uses another fruit; empty if inapplicable. |
| criterion_id | string | Independently sourced and frozen cultivar/market maturity criterion. |
| decision_rule_id | string | Frozen model-to-harvest decision rule, if evaluated. |
| observed_at_utc | datetime | Field or quality observation timestamp. |
| observation_type | string | Registered variable: actual harvest, maturity assessment, or postharvest outcome. |
| observation_value | string | Value using the registered outcome definition. |
| observation_units | string | Registered units or categorical coding. |
| assessor_blinded_to_model | boolean | true or false; retain actual blinding state. |
| followup_protocol_id | string | Frozen postharvest handling/assessment protocol if relevant. |

## Required freeze evidence

The registration identifies all model hashes, population and precision plan, scan plan, laboratory and QC SOPs, and analysis version. The prediction freeze covers the complete input/QC/prediction manifests, including failures, before assay linkage release. A laboratory archive hash and a custodian release record complete the assay chain. Record amendments as new freezes; do not overwrite earlier evidence.

Harvest observations are an optional schema for a separate future field study. A populated record is not a validated recommendation to pick. A maturity criterion, decision rule, independent outcome plan and comparative field design must be frozen first.
