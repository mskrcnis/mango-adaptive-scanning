# Public research release

This repository distributes the existing research code, frozen inference bundles, numerical reports and current JNIRS manuscript package. It does not establish new scientific results or journal acceptance. The source paper remains an author-review draft, including its pending author fields and AI-policy review.

## Supported immediately from a clone

1. Read the manuscript, supplement, saved comparisons and scientific limitations.
2. Run `python3 scripts/verify_public_release.py` to verify the distributed files against `release/release_manifest.json` and the included frozen/archive manifests.
3. Compile the main and supplementary PDFs with `bash revisions/jnirs_submission_v6/build_pdfs.sh` using a suitable TeX Live installation.
4. Run the six-channel candidate using `revisions/candidate_v4/predict.py`, its complete frozen bundle and the three development example rows. NumPy and SciPy are sufficient for this interface.
5. Run the original adaptive replay application using the supplied original frozen directory and the pinned scientific environment. This is a software demonstration; the adaptive superiority claim remains unsupported.

Both frozen bundles retain their original hashes. Their model files are project-generated artifacts, not newly fitted models. Example inputs are derived from the attributed public dataset and are development examples, not unseen validation observations.

## What is omitted

| Omitted local material | Reason and available alternative |
|---|---|
| Full raw, sealed and processed spectral files | Retrieve the exact official dataset via its DOI/provider metadata; verify the documented SHA-256 |
| Downloaded journal PDFs, full text and manufacturer PDF/image copies | Redistribution rights are not asserted; bibliographic metadata, source URLs and checksums remain |
| Training checkpoints, stale attempts and cached per-scan predictions | Large working artifacts; source, frozen inference models, aggregate comparisons and reporting evidence remain |
| Virtual environment, temporary files, rendered page-QA images and TeX intermediates | Rebuild locally; final PDFs and hash-bound review records remain |
| Original internal execution prompt and root session ledger | Operational history; scientific protocols, revision status reports and verification records remain |

No omitted files were deleted from the local research workspace. `.gitignore` controls the publication boundary. Header-only prospective validation templates contain no new participant or fruit observations.

## Historical verification and a full research rerun

Historical manifests and reports describe the complete original workspace, including files omitted above. They remain unchanged as provenance. A public clone therefore cannot satisfy every old whole-workspace preservation check or resume training solely by invoking historical `all --resume` commands. Use the public-release verifier for the distributed set. In particular, the v6 `verify_package.py` checks a complete v5 directory when one is present; the filtered historical v5 directory in Git is not that complete workspace. This is why the release verifier separately checks delivered PDFs and the self-contained archive.

The independently compilable current manuscript ZIP is the supported document-reproduction route. For full model regeneration, use a separate fresh working directory, obtain the official version-3 dataset, restore the documented optical source assets or verify their numeric profiles, and recreate each analysis stage under its registered dependencies. Read `docs/HISTORICAL_WORKFLOW.md`, the original protocol and each revision's workflow before initializing a fresh experiment. Do not rewrite the published frozen artifacts or weaken a failed integrity check to force a resume. Exact reproduction of historic hardware-dependent training is not claimed by this release.

The dataset-preparation implementation is `mango/data.py`; it resolves public provider records and verifies the official file checksum. Source details and trace coordinates for the optical simulation are under `data/catalog/`. These are fixed simulation assumptions, not measurements from a constructed scanner.

## Audit scope

The release file manifest covers the tracked publication payload except the manifest itself. The verifier checks exact file bytes, the intended file exclusions, recognized credential patterns, the journal source ZIP and its embedded checksums, PDF delivery hashes, and included frozen bundle files. A credential-pattern scan is a bounded check, not a universal security guarantee. The verifier does not modify research data or fit models.

Release preparation also runs existing software tests and checks inference and manuscript compilation from a clean copy. Public visibility is verified after pushing using unauthenticated GitHub HTTP access and an unauthenticated clone. Local publication receipts are kept under ignored `release/local/` so recording the final remote commit does not create a circular commit reference.

## Rights and manuscript status

No blanket open-source license has been added. Third-party terms are recorded in `THIRD_PARTY_NOTICES.md`; public visibility is separate from licensing. The source and results are offered as a transparent research record subject to their applicable rights.

The manuscript was prepared before this public release and contains historical statements that software access remains to be specified. Its final submission edition should cite this repository and complete actual author declarations. No authorship, funding, conflict, all-author approval, journal-policy eligibility or journal submission is asserted by publishing the repository.
