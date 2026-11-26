# Related-work expansion: primary-source and claim record

Updated 26 November 2026 at the user's request. Section 1.1 now develops six connected topics: mango dry matter as the measured target; robustness and transfer; predictor/preprocessing choices; fixed spectral design; conditional acquisition and stopping; and evaluation and contribution boundaries. All manuscript prose outside Section 1.1 is preserved. The first dataset table was restricted to bottom/page float placement so it cannot appear above the end of Related Work. No empirical analysis or frozen model was changed.

The expanded main paper cites 30 distinct sources, including 26 journal or proceedings articles, plus the dataset, one supporting thesis, one preprint and the manufacturer source. Fifteen previously uncited research papers were added; the existing verified Yang et al. 2026 ensemble paper is now also discussed. All entries are cited in the manuscript: no `nocite` command is used. The article and supporting Walsh thesis are not treated as separate independent validations. Foundational PLS/SNV/Savitzky-Golay candidates were not added merely to increase the reference count.

The bibliography and scope audit for the previously present sources remains in `literature_and_claims_review.md`. The records below document the 15 added sources, their primary links, accessible evidence and the claims used. They identify partial access explicitly. This is a targeted literature review, not a systematic search or a novelty certification. Published error values are not ranked against this study's differently configured comparisons.

# Nine additional primary mango studies for Section 1.1

Verified 26 November 2026. These are empirical research articles, not citation-count padding. None duplicates the 15 existing v5 bibliography entries. Exact authors, titles, publication years, journals, volumes, issues where present, pages/article numbers and DOIs are in `manuscript/references.bib`. Publisher-deposited Crossref records were retrieved successfully for all nine DOIs; initial rate-limit failures for two records were resolved. Publication year follows the journal issue, not the year embedded in the DOI.

Primary-source access was checked by browsing publisher records, author-institution repositories and the authors' arXiv manuscript. Where direct publisher-page requests returned HTTP 403, the indexed publisher abstract/introduction/section text was read; that is explicitly partial access, not a claim that the journal full text was retrieved. No full-text methodological details are inferred from metadata alone. No new model fits, data reads, scientific scores or changes to the main manuscript/bibliography occurred.

## Recommended placement and claims

### 1. `saranwong2004` — biological motivation, without adopting a maturity threshold

**Citation:** Sirinnapa Saranwong, Jinda Sornsrivichai and Sumio Kawano (2004). *Prediction of ripe-stage eating quality of mango fruit from its harvest quality measured nondestructively by near infrared spectroscopy*. **Postharvest Biology and Technology 31(2), 137–145**. DOI [10.1016/j.postharvbio.2003.08.007](https://doi.org/10.1016/j.postharvbio.2003.08.007).

**Primary evidence/access:** [Publisher abstract, introduction and section snippets](https://www.sciencedirect.com/science/article/pii/S0925521403001613); Crossref bibliographic record. Full journal article was not read in this expansion.

**Supported claim:** This study connects harvest-stage dry matter and starch, estimated by NIR, with later soluble-solids outcomes in its mango cohort. It establishes a rationale for dry-matter prediction as a quality-related measurement.

**Boundary:** This does not supply a universal pick/wait threshold or validate this paper's model for eating quality. The source's cohort, individual fruit follow-up and ripe-stage outcomes differ from the present scan-only benchmark.

### 2. `subedi2007` — earlier short-wave NIR and robustness testing

**Citation:** P. P. Subedi, K. B. Walsh and G. Owens (2007). *Prediction of mango eating quality at harvest using short-wave near infrared spectrometry*. **Postharvest Biology and Technology 43(3), 326–334**. DOI [10.1016/j.postharvbio.2006.09.012](https://doi.org/10.1016/j.postharvbio.2006.09.012).

**Primary evidence/access:** [Publisher introduction and abstract/section text](https://www.sciencedirect.com/science/article/pii/S0925521406002365); Crossref. Partial journal text only.

**Supported claim:** Short-wave NIR was investigated for mango dry matter, flesh color and subsequent eating-quality proxies, with attention to harvest-date, regional and cultivar variation. The introduction distinguishes physiological maturity from applying a single dry-matter cutoff.

**Boundary:** Use as historical motivation and robustness context, not as proof of a general agronomic threshold. Keep published SEP, RMSEP and bias measures distinct; do not rank its scores against this paper's different observation and split scheme.

### 3. `wendel2018` — relevant sensing context before filter selection

**Citation:** Alexander Wendel, James Underwood and Kerry Walsh (2018). *Maturity estimation of mangoes using hyperspectral imaging from a ground based mobile platform*. **Computers and Electronics in Agriculture 155, 298–313**. DOI [10.1016/j.compag.2018.10.021](https://doi.org/10.1016/j.compag.2018.10.021).

**Primary evidence/access:** [Publisher abstract, introduction and section snippets](https://www.sciencedirect.com/science/article/abs/pii/S0168169918309013); Crossref. Full methods not recovered in this review.

**Supported claim:** Mobile orchard hyperspectral sensing was used to estimate and map mango dry matter, comparing PLS and CNN prediction. This is the sensing setting underlying the already cited Gutiérrez filter-design work.

**Boundary:** Its remote imaging and lighting geometry differ from the present contact-spectrum replay. The abstract states that prediction was compared with hand-held NIR estimates of dry matter; do not silently label those all direct destructive assays. The source's proposed harvesting application does not establish harvest decisions in this paper.

### 4. `sun2020temperature` — temperature is a calibration issue, not just metadata

**Citation:** Xudong Sun, Phul Subedi and Kerry B. Walsh (2020). *Achieving robustness to temperature change of a NIRS-PLSR model for intact mango fruit dry matter content*. **Postharvest Biology and Technology 162, 111117**. DOI [10.1016/j.postharvbio.2019.111117](https://doi.org/10.1016/j.postharvbio.2019.111117).

**Primary evidence/access:** [Publisher abstract/highlights and indexed section text](https://www.sciencedirect.com/science/article/pii/S0925521419311652); Crossref. Full methods unavailable in this expansion.

**Supported claim:** The study explicitly compared temperature-correction strategies for mango DMC prediction, including external parameter orthogonalization, generalized least-squares weighting and global calibration approaches. It supports treating sample temperature as a possible source of NIR calibration variation.

**Boundary:** Do not import its temperature-correction recommendations, minimum sample percentages or accuracy into this study. No controlled-temperature correction or calibrated per-row temperature was evaluated here. The journal publication year is **2020**, despite the **2019** DOI suffix.

### 5. `anderson2021local` — strongest direct benchmark antecedent

**Citation:** N. T. Anderson, K. B. Walsh, J. R. Flynn and J. P. Walsh (2021). *Achieving robustness across season, location and cultivar for a NIRS model for intact mango fruit dry matter content. II. Local PLS and nonlinear models*. **Postharvest Biology and Technology 171, 111358**. DOI [10.1016/j.postharvbio.2020.111358](https://doi.org/10.1016/j.postharvbio.2020.111358).

**Primary evidence/access:** [Publisher abstract, introduction and section snippets](https://www.sciencedirect.com/science/article/pii/S0925521420309303); Crossref. Journal full text not read. An indexed URL ending in `main.pdf` returned publisher preview text and is not counted as recovered full text.

**Supported claim:** The public mango lineage already supported comparison of local and nonlinear regressors trained across three seasons and tested on a fourth. This makes strong local/nonlinear baselines and benchmark-reuse disclosure directly relevant.

**Boundary:** The authorship is Anderson/Kerry Walsh/Flynn/Jeremy Walsh; it is not the Hayes/Subedi list of Part I. The source explicitly limits conclusions to one spectrometer, so it is not evidence of multi-instrument robustness. Published optimized models are not reproduced by fixed local SVR or PLS settings here.

### 6. `mishra2021preprocessing` — preprocessing changes what a comparison means

**Citation:** Puneet Mishra, Douglas N. Rutledge, Jean-Michel Roger, Khan Wali and Haris Ahmad Khan (2021). *Chemometric pre-processing can negatively affect the performance of near-infrared spectroscopy models for fruit quality prediction*. **Talanta 229, 122303**. DOI [10.1016/j.talanta.2021.122303](https://doi.org/10.1016/j.talanta.2021.122303).

**Primary evidence/access:** [Full publisher-version PDF hosted by coauthor institution Charles Sturt University](https://researchoutput.csu.edu.au/ws/portalfiles/portal/140566376/139926862_Published_article.pdf), 7 pages; abstract and sections 2.1–2.4 and 3.2 reviewed; Crossref checked.

**Supported claim:** In a mango DMC comparison, raw absorbance outperformed the tested preprocessing combinations for the evaluated PLS and deep-learning configurations. Preprocessing benefits therefore cannot be assumed independently of the predictor and dataset.

**Boundary:** Section 2.1 uses a narrower 742–990 nm window and removes outliers from training **and test** data. Its error values are not directly comparable with the present unfiltered 103-channel seasonal evaluation. The result does not imply that SNV or derivatives are universally harmful.

### 7. `mishra2021synergy` — useful complementary preprocessing result

**Citation:** Puneet Mishra and Dário Passos (2021). *A synergistic use of chemometrics and deep learning improved the predictive performance of near-infrared spectroscopy models for dry matter prediction in mango fruit*. **Chemometrics and Intelligent Laboratory Systems 212, 104287**. DOI [10.1016/j.chemolab.2021.104287](https://doi.org/10.1016/j.chemolab.2021.104287).

**Primary evidence/access:** [Full publisher-version PDF in coauthor institution Universidade do Algarve repository](https://sapientia.ualg.pt/server/api/core/bitstreams/e925e5c8-2596-4493-b241-c683b48a68a7/content). Direct browser request timed out; ordinary HTTPS retrieval succeeded and PDF text was extracted. Abstract, data/preprocessing methods and train/test-with/without-outliers comparisons were reviewed; Crossref checked.

**Supported claim:** The authors studied concatenated spectral preparations and chemometric outlier filtering in conjunction with a CNN for mango dry matter. Together with the Talanta paper, this shows that the handling and combination of spectral preparations are part of the modeling question.

**Boundary:** Six concatenated preparations are not six physical sensor readings. The paper separately reports filtered and unfiltered test comparisons; retain that distinction if discussing results. Do not treat the abstract's sample-count wording as this study's dataset specification or assign its reported accuracy to the local adapted architecture.

### 8. `mishra2021transfer` — direct evidence that instrument transfer is separate

**Citation:** Puneet Mishra and Dário Passos (2021). *Deep chemometrics: Validation and transfer of a global deep near-infrared fruit model to use it on a new portable instrument*. **Journal of Chemometrics 35(10), e3367**. DOI [10.1002/cem.3367](https://doi.org/10.1002/cem.3367).

**Primary evidence/access:** [Full publisher-version PDF in Universidade do Algarve repository](https://sapientia.ualg.pt/server/api/core/bitstreams/2766a50e-cccb-44d7-a4fc-8e47ed1b6156/content), 12 pages. Retrieved by HTTPS and text extracted; abstract and methods describing the original/new mango datasets and adaptation reviewed. [Author-institution abstract](https://research.wur.nl/en/publications/deep-chemometrics-validation-and-transfer-of-a-global-deep-near-i/) and Crossref corroborate metadata. Retrieved PDF SHA-256: `1d536f2fae6b8fb33d8b91d8030f1e0300256dad33a1522a3006719d699fc7ac`.

**Supported claim:** A previously fitted mango model was tested on a later cohort measured with a different physical instrument, then updated for seasonal/instrument differences. Direct application and adapted-model performance differed, illustrating that benchmark prediction and calibration transfer are distinct evaluations.

**Boundary:** The new device was another F750, not an emitter-bank scanner. Updating uses target-setting measurements; do not describe all reported transfer results as untouched zero-shot testing or evidence that the current simulated channels transfer physically.

### 9. `dirks2022` — strongest direct support for careful tuning and reuse claims

**Citation:** Matthew Dirks and David Poole (2022). *Automatic neural network hyperparameter optimization for extrapolation: Lessons learned from visible and near-infrared spectroscopy of mango fruit*. **Chemometrics and Intelligent Laboratory Systems 231, 104685**. DOI [10.1016/j.chemolab.2022.104685](https://doi.org/10.1016/j.chemolab.2022.104685).

**Primary evidence/access:** [Publisher abstract/introduction/section text](https://doi.org/10.1016/j.chemolab.2022.104685), Crossref, and [full author manuscript on arXiv](https://arxiv.org/html/2210.01124), sections 2.1–2.4 and conclusion reviewed. The author manuscript and journal preview differ in enumerating validation-set variants; cite the common high-level result, not an exact replication of every final-journal configuration.

**Supported claim:** On the mango seasonal benchmark, validation-set choice and ensembling affected hyperparameter optimization and seasonal extrapolation. This directly supports separating tuning performance from held-season evaluation and documenting stochastic effects.

**Boundary:** The source uses concatenated preprocessing and an outlier-filtered training lineage. It revisits the existing benchmark; it is not an independent dataset validating the present controller. Its authors are **Dirks and Poole**, not the authors of the Mishra papers.

## Suggested integration

A coherent expansion can use all nine without a list of disconnected citations:

1. Motivate DMC as an observed, quality-related target using `saranwong2004,subedi2007`, explicitly retaining the paper's absence of eating-quality or pick/wait outcomes.
2. Connect `wendel2018` to the existing `gutierrez2019`: orchard hyperspectral measurement and then finite-response filter simulation are established precedents. Avoid treating ideal channel selection as an implemented compact instrument.
3. Extend seasonal robustness beyond Part I with `anderson2021local`, then separate temperature variation (`sun2020temperature`) and instrument transfer (`mishra2021transfer`). These motivate boundaries; they are not additional experiments required to finish the present dataset-only paper.
4. Discuss conditional preprocessing findings together (`mishra2021preprocessing,mishra2021synergy`) rather than claiming a universal benefit or harm. Connect these to the locally adapted Walsh architecture.
5. Use `dirks2022` to support the need for explicit seasonal tuning/evaluation separation and stochastic reporting. Conclude with the present paper's distinct, bounded acquisition-versus-prediction question, not an unsupported first-method claim.

The strongest direct additions for the present scientific argument are `anderson2021local`, `dirks2022`, `mishra2021preprocessing`, `mishra2021synergy`, and `sun2020temperature`. The remaining four supply the biological, sensing and transfer context necessary to make those comparisons interpretable. The selected set deliberately excludes a general crop-manipulation paper and unrelated fruit reviews.


# Additional methods sources: verified scope and access

Checked 2026-11-26. The six core sources below directly support the requested Related Work expansion. Only these six core sources were added; foundational-method candidates were omitted. No new models or predictive comparisons were run. None of these methods is an implemented local comparator unless the existing manuscript separately establishes that fact.

Metadata were checked against the publisher/proceedings record and, for the journal articles, Crossref's DOI registry. The new keys and DOIs do not duplicate the supplied bibliography. A publisher abstract supports only its stated scope; it is not labeled a full-methods review. Institutional/proceedings/publisher primary pages supply the technical evidence, rather than later review papers citing these methods.

## Six core additions

### li2009cars — CARS

Li, Hongdong; Liang, Yizeng; Xu, Qingsong; Cao, Dongsheng (2009). *Key wavelengths screening using competitive adaptive reweighted sampling method for multivariate calibration*. **Analytica Chimica Acta 648(1), 77–84**. DOI: **10.1016/j.aca.2009.06.046**.

- Primary evidence: [publisher article](https://www.sciencedirect.com/science/article/pii/S0003267009008332). Publisher abstract and partial article text were available; full PDF was not obtained.
- Supported scope: CARS uses PLS coefficient magnitude to weight wavelength importance, sampling/reweighting to generate subsets, and cross-validation to choose a subset. Its reported examples include simulated and NIR data.
- Useful placement: established supervised fixed-wavelength selection; distinguish its calibration-stage “adaptive reweighting” from a scan-dependent runtime acquire/stop policy.
- Boundary: no claim that our exhaustive constrained-bank selection outperforms CARS; no claim that this paper studied mango or measured LED hardware.

### araujo2001spa — successive projections

Araújo, Mário César Ugulino; Saldanha, Teresa Cristina Bezerra; Galvão, Roberto Kawakami Harrop; Yoneyama, Takashi; Chame, Henrique Caldas; Visani, Valeria (2001). *The successive projections algorithm for variable selection in spectroscopic multicomponent analysis*. **Chemometrics and Intelligent Laboratory Systems 57(2), 65–73**. DOI: **10.1016/S0169-7439(01)00119-8**.

- Primary evidence: [publisher article](https://www.sciencedirect.com/science/article/pii/S0169743901001198). Abstract/introduction available; full PDF not obtained. Full author list independently matched Crossref.
- Supported scope: a deterministic forward selection method using vector projections to reduce variable collinearity in spectroscopic multivariate calibration, demonstrated with UV–visible multicomponent data.
- Useful placement: selected wavelength sets have established methodological precedents beyond coefficient ranking.
- Boundary: the physical response integrals in our bank are not identical to selecting individual source wavelengths; no direct SPA-versus-current-method result was run.

### norgaard2000ipls — interval PLS

Nørgaard, L.; Saudland, A.; Wagner, J.; Nielsen, J. P.; Munck, L.; Engelsen, S. B. (2000). *Interval Partial Least-Squares Regression (iPLS): A Comparative Chemometric Study with an Example from Near-Infrared Spectroscopy*. **Applied Spectroscopy 54(3), 413–419**. DOI: **10.1366/0003702001949500**.

- Primary evidence: [publisher article](https://journals.sagepub.com/doi/10.1366/0003702001949500). Metadata and abstract available; publisher marks full article restricted.
- Supported scope: iPLS is a local spectral modeling/interval-selection procedure compared with full-spectrum PLS and other variable-selection approaches on NIR measurements of beer samples.
- Useful placement: fixed selection can operate over spectral intervals rather than isolated points, providing context for constrained finite-band design.
- Boundary: interval selection does not establish a real LED instrument or the exact response-weighted simulator used here; do not import its reported performance into the mango benchmark.

### shim2018 — explicit acquire/stop learning

Shim, Hajin; Hwang, Sung Ju; Yang, Eunho (2018). *Joint Active Feature Acquisition and Classification with Variable-Size Set Encoding*. **Advances in Neural Information Processing Systems 31**, Curran Associates.

- Primary evidence: [official proceedings record](https://proceedings.neurips.cc/paper/2018/hash/e5841df2166dd424a57127423d276bbe-Abstract.html), [full 11-page proceedings PDF](https://proceedings.neurips.cc/paper_files/paper/2018/file/e5841df2166dd424a57127423d276bbe-Paper.pdf), [official BibTeX](https://proceedings.neurips.cc/paper_files/paper/2018/file/e5841df2166dd424a57127423d276bbe-Bibtex.bib). PDF retrieved; abstract/introduction and acquisition formulation inspected. Official BibTeX supplies no page range, so none is invented.
- Supported scope: jointly learns a classifier and cost-sensitive reinforcement-learning acquisition agent that can acquire a feature or stop; represents acquired features with an order-invariant set encoding. Synthetic and medical examples are reported.
- Boundary: classification differs from our regression problem; this method was not run as a comparator here. It directly prevents novelty claims based only on learned acquire/stop decisions or partial-feature input.

### varma2006 — selection bias in estimated performance

Varma, Sudhir; Simon, Richard (2006). *Bias in error estimation when using cross-validation for model selection*. **BMC Bioinformatics 7, article 91**. DOI: **10.1186/1471-2105-7-91**.

- Primary evidence: [open publisher full text](https://link.springer.com/article/10.1186/1471-2105-7-91). Full HTML retrieved and relevant methods/results/conclusion inspected. Published 23 February 2006; “91” is the article number, not a page span.
- Supported scope: simulations with tuned classifiers show that the minimum CV error used for selection can be optimistically biased; nesting the tuning in an outer evaluation substantially reduces that bias in their experiments.
- Useful placement: why wavelength/threshold design and performance assessment must remain separate, and why V4's selected LOPO minimum is a tuning statistic.
- Boundary: this is methodological support, not proof that our finite reused-season study is unbiased or confirmatory.

### roberts2017 — structured evaluation

Roberts, David R.; Bahn, Volker; Ciuti, Simone; Boyce, Mark S.; Elith, Jane; Guillera-Arroita, Gurutzeta; Hauenstein, Severin; Lahoz-Monfort, José J.; Schröder, Boris; Thuiller, Wilfried; Warton, David I.; Wintle, Brendan A.; Hartig, Florian; Dormann, Carsten F. (2017). *Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure*. **Ecography 40(8), 913–929**. DOI: **10.1111/ecog.02881**.

- Primary evidence: [publisher full text](https://nsojournals.onlinelibrary.wiley.com/doi/full/10.1111/ecog.02881). Full HTML and the authors' simulation/case-study and blocking guidance inspected. This is a review/synthesis containing original simulations/case studies; cite those findings and its scoped evaluation guidance, not a claim to invent blocked CV.
- Supported scope: dependence-aware blocking can expose optimism from random splits; blocking must match the prediction target and can change interpolation into extrapolation.
- Useful placement: harvest-population grouping and whole-season holdouts assess different generalization questions.
- Boundary: no claim that population IDs recover unknown fruit identities or guarantee independence. Bibliographic issue year is 2017; do not replace it with an earlier online-history date.

