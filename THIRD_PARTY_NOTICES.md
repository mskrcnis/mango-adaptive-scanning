# Rights and third-party provenance

Public availability of this repository does not imply a blanket license for all files. No open-source license has been selected for original project code, manuscript text or other original materials; applicable copyright remains with the respective rightsholders. Do not interpret the dataset license as a license for the entire repository.

## Mango dataset and derived examples

Anderson, Walsh, Subedi and Hayes, *Mango DMC and spectra Anderson et al. 2020*, Mendeley Data version 3, DOI [10.17632/46htwnp833.3](https://doi.org/10.17632/46htwnp833.3). The provider licenses the dataset under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Provider metadata and exact file hashes are retained under `data/provenance/` and the study's data manifest.

The full source CSV is not redistributed in Git. Included development examples, row identities, fitted models, predictions and aggregate result tables were derived through the processing and analysis described in the manuscript and code. Example spectral values and simulated-channel values are identified as development examples; they are not new observations. The authors of the source dataset do not thereby endorse this analysis.

## Emitter profiles and literature

Manufacturer: Roithner Lasertechnik. Part identifiers, original source URLs, source-document checksums, digitization settings and numerical profile coordinates are retained in `data/catalog/`. The numeric profiles were digitized from typical emitter plots and are used as stated simulation assumptions. They are not independently measured responses. See `source_manifest.json` and the original manufacturer documents for source details.

Downloaded manufacturer PDFs, screenshots, extracted full text and downloaded journal/thesis PDFs are excluded. No redistribution license or ownership over those publications is asserted. Bibliographic metadata, citations and source links are supplied for independent access.

## Sage LaTeX components

`revisions/jnirs_submission_v6/sagej.cls` is the unchanged Sage class version 1.20, 17 January 2017. It retains its original copyright and rules of use, including the prohibition on changing that file and the restriction on commercial exploitation. It is included for preparing an article intended for a Sage journal. The author-side `jnirs_review.sty` adjusts the review presentation without editing the class.

`sagev.bst` retains its original license header. The separately named `jnirs_sagev.bst` is the documented derivative that adds conference-year output; its original LaTeX Project Public License terms remain in the file. Provenance copies retain their notices. Exact source URLs, mirror revision and hashes are in `revisions/jnirs_submission_v6/template_provenance/mirror_source.json`.

The current official template download was blocked at preparation time. The recovered class version matches the publisher-linked Overleaf demonstration, but byte-equivalence with that blocked current download is not claimed.

## Dependencies

Python packages and TeX tools are not vendored. `requirements.txt` records the pinned research dependencies; their own licenses apply. The frozen software snapshots preserve the original project implementation and provenance without changing scientific results.
