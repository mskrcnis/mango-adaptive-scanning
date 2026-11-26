# Optical catalog and forward emulator audit

The primary catalog contains **10 distinct real part families** and supports the preregistered eight-installed-LED / four-reading target with alternative banks. All ten primary responses are **digitized typical data-sheet curves**, not Gaussian profiles and not measured individual devices. Manufacturer numerical response tables were not linked on the inspected Roithner or Marktech catalog pages. Source PDFs, extracted text, rendered pages, trace overlays and SHA-256 hashes are retained under `data/catalog/`. Read `catalog.json` for exact part membership and source page.

| Part | Nominal peak, nm | Stated spectral width, nm | Digitized response mass within 684–990 nm |
|---|---:|---:|---:|
| LED720-03AU | 720 | 23 | 98.078% |
| LED740-01AU | 740 | 30 | 100.000% |
| LED760-03AU | 760 | 30 | 100.000% |
| LED780-03AU | 780 | 27 | 99.982% |
| LED800-01AU | 800 | 29 | 100.000% |
| LED820-01AU | 820 | 35 | 100.000% |
| LED850-03UP | 850 | 40 | 100.000% |
| LED890-03AU | 890 | 47 | 100.000% |
| LED910D-01 | 910 | 35 | 99.902% |
| LED940D-05 | 940 | 40 | 99.379% |

The cutoff is 95% modeled response mass. Each curve came from the actual linked component sheet on the [Roithner catalog](https://www.roithner-laser.com/led_standard.html), inspected 26 November 2026. The [Marktech catalog](https://marktechopto.com/led-emitters/near-ir/) was also inspected; it offered alternative parts but was unnecessary after ten usable plotted profiles were recovered. Package/beam-angle variants sharing one spectral family were not counted as additional choices. The selected primary nominal peaks differ by at least 20 nm; different beam angles alone do not generate distinct spectral options here.

The largest off-diagonal cosine similarity of normalized response-weight vectors
on the common grid is 0.84055 (LED890-03AU versus LED910D-01), with no equal
profile pair. These are distinct modeled design options; detectability of their
differences in a physical instrument depends on optical noise and calibration.
The calculation is saved in `data/catalog/profile_distinctness.json`.

## Traceability and approximation boundaries

`data/catalog/digitize_profiles.py` recreates each curve from a cached PDF using Poppler at 1400-pixel page height. Axes and page numbers were manually read from rendered plots. The trace identifies dark curve pixels, excludes plot text, and stores pixel coordinates, intensity threshold and axis limits. All ten red-overlay traces were visually inspected against the black manufacturer curves. CSV curves are linearly interpolated to the measured 3 nm grid. This is interpolation of a **response function**, not imputation of any unmeasured fruit channel.

The plotted domain has finite support; profiles are assigned zero at plot endpoints and outside the plotted range. Thus the percentages above refer to the digitized plotted profile under that explicit tail assumption, not a certified bound on unplotted real-device emission. Some plots show small nonzero edge tails. Digitization and manufacturer typical-curve precision do not justify interpreting 100.000% as physically exact coverage. Nominal width and digitized width are both retained. In particular, the LED820-series tabulates 35 nm width while its drawn curve is about 26 nm at half height; the primary uses the actual trace and the nominal-Gaussian sensitivity reveals this discrepancy. Typical operating conditions are about 25 degrees C, and the source sheets give different nominal currents. Relative normalized profiles discard absolute emitted power.

`get_catalog(profile_type='gaussian_approximation')` makes a **separate sensitivity catalog** from documented nominal peak and spectral width for the same parts. It is never labeled measured or digitized. Roithner labels most widths “Half Width”; the plotted half-height full widths show that this is intended as spectral FWHM (explicitly named FWHM in LED940D-05). The nominal Gaussian is not substituted into the primary traces.

A conservative sensitivity uses peak shifts of +/-5 nm and width scale 0.9 or 1.1. Peak perturbations lie within several published part ranges (e.g. 710–730 nm for LED720, 805–835 nm for LED820, 930–955 nm for LED940), although the 740/760 sheets do not specify a peak range. The 10% width perturbation is an engineering scenario, **not a claimed manufacturer tolerance**, because the sheets give typical widths without tolerance limits. All primary curves still clear 95% coverage at the widest +/-5 nm settings; the worst is LED720 at -5 nm and 1.1 width, 95.61%. Larger manufacturer peak-extreme perturbations may fail support and must be rejected, not silently renormalized.

LED840-04AU and LED870-01UP had verified center/width-only one-page sheets; they are omitted from the primary digitized pool. LED700/710 sheets were downloaded but not added because adequate better-covered alternatives already existed and uncertain edge tails would add a weak support assumption. LED970D-03 and LED980D-03 have nominal Gaussian support fractions below 95%, so they are unsuitable for this common window; a test explicitly rejects 980 nm / 55 nm FWHM with only 66.57% support. The catalog's original uppercase LED890 PDF URL returned 404; the same official lowercase URL succeeded and is the retained source. The LED890 sheet contains an unrelated outline-dimension label “LED570-01” on page 3; the spectral chart, description and optical table concern 890 nm, and mechanical dimensions are not used here.

## Forward calculation and assumptions

For base-10 apparent absorbance A, relative intensity r=10^(-A). The emulator computes z_j=-log10(sum_k w_jk r_k / sum_k w_jk). It therefore averages intensities before taking the logarithm. Wavelength quadrature uses trapezoidal widths (1.5 nm at the two endpoints, 3 nm internally). Its numerical implementation uses a per-row absorbance shift for stable exponentials; this does not change the weighted ratio.

The data provider identifies raw absorbance, and the F-750 manual defines Log(1/Reflectance), but available documentation does not explicitly print the logarithm base. **Base 10 is the standard apparent-absorbance convention adopted here, not a firmware-level verification.** No reference detector responsivity, optical throughput spectrum, fruit geometry transfer or LED-specific reference measurement is available. Flat detector and reference weighting is therefore a declared simulation assumption. Although normalization cancels a wavelength-independent multiplicative factor, it cannot eliminate unknown within-band responsivity or geometry effects. The API can accept measured nonnegative detector/reference arrays later; those do not currently establish device fidelity.

No derivative, whole-spectrum normalization or sparse-reading interpolation is performed at inference. The offline emulator constructs individual finite-band readings from complete original spectra; the deployed controller must receive only requested readings. Pulse counts are simulated acquisition effort. Neither emitted energy, shot noise, actual scanning time nor hardware repeatability is measured.

## Interface and executed checks

- `get_catalog()` returns eligible primary dictionaries in ascending nominal wavelength order.
- `response_weights(wavelengths, catalog)` returns `(number_of_wavelengths, number_of_channels)` weights with normalized columns and explicit coverage rejection.
- `channel_matrix(X, wavelengths, catalog)` returns the corresponding channel matrix; a single input row is supported.
- Center-shift, bandwidth-scale and optional detector/reference arrays are keyword arguments. Unsupported perturbed responses raise an error.

An independent numerical check used 103 points, 684:3:990 nm, and constant A=1.23456. Maximum absolute deviation was 2.22e-16. All weight columns sum to one, and an unsupported 980 nm Gaussian was rejected. Saved evidence: `data/catalog/verification.json`. These checks establish software invariants, not physical validation.
