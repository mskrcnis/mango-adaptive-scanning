"""Portable inference for one frozen fixed-channel candidate.

This module uses only NumPy and SciPy. It never reads files, fits a transform,
or accepts outcomes or metadata. Candidate prediction requires exactly the six
selected scalar readings in the order recorded by the frozen bundle.
"""

import numpy as np
from scipy.signal import savgol_filter


def _matrix(values, width, name, *, float32_boundary=False):
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        array = array[None, :]
    if array.ndim != 2 or array.shape[1] != width or not len(array):
        raise ValueError('%s must contain one or more rows of exactly %d values' % (name, width))
    if not np.isfinite(array).all():
        raise ValueError('%s must contain finite values' % name)
    if float32_boundary:
        with np.errstate(over='ignore', invalid='ignore'):
            array = array.astype(np.float32).astype(np.float64)
        if not np.isfinite(array).all():
            raise ValueError('%s values must be representable as finite float32' % name)
    return array


def preprocess(values, width, *, rich=False):
    """Use the registered float32 input boundary and legacy float64 transforms."""
    transformed = _matrix(values, width, 'Model input', float32_boundary=True)
    if rich:
        if width != 103:
            raise ValueError('The registered rich reference requires 103 wavelengths')
        transformed = ((transformed - transformed.mean(axis=1, keepdims=True)) /
                       np.maximum(transformed.std(axis=1, keepdims=True), 1e-8))
        transformed = savgol_filter(transformed, window_length=11, polyorder=2,
                                    deriv=2, delta=3.0, axis=1)
    return transformed


def _model(portable, kind):
    if not isinstance(portable, dict) or portable.get('schema_version') != 1:
        raise ValueError('Unsupported portable model schema')
    try:
        model = portable['models'][kind]
    except (KeyError, TypeError):
        raise ValueError('Missing frozen model: ' + kind)
    width = {'candidate': 6, 'full_bank': 8, 'rich': 103}[kind]
    expected = 'snv_sg_second_derivative' if kind == 'rich' else 'raw_channels'
    if (model.get('n_features') != width or model.get('preprocessing') != expected or
            model.get('input_dtype') != 'float32' or model.get('math_dtype') != 'float64'):
        raise ValueError('Frozen model settings do not match the registered input contract')
    return model, width


def _predict(model, transformed):
    width = transformed.shape[1]
    mean = np.asarray(model['x_mean'], dtype=np.float64)
    scale = np.asarray(model['x_std'], dtype=np.float64)
    coefficients = np.asarray(model['coefficients'], dtype=np.float64)
    intercept = np.asarray(model['intercept'], dtype=np.float64)
    if (mean.shape != (width,) or scale.shape != (width,) or
            coefficients.shape != (width,) or intercept.ndim != 0 or
            not np.isfinite(mean).all() or not np.isfinite(scale).all() or
            not np.isfinite(coefficients).all() or not np.isfinite(intercept) or
            np.any(scale <= 0)):
        raise ValueError('Invalid frozen PLS coefficients or scaler')
    # Preserve the fitted sklearn arithmetic order, including its autoscaling.
    prediction = ((transformed - mean) / scale) @ coefficients + float(intercept)
    if not np.isfinite(prediction).all():
        raise ValueError('Frozen model produced nonfinite predictions')
    return prediction


def predict_channels(portable, values, kind='candidate'):
    """Predict from EXACTLY six candidate or eight complete-bank readings.

    A six-channel caller cannot supply eight values and have hidden readings
    silently selected. The caller must supply the registered selected-channel
    order. One input row returns a one-element vector.
    """
    if kind not in ('candidate', 'full_bank'):
        raise ValueError('Channel model must be candidate or full_bank')
    model, width = _model(portable, kind)
    return _predict(model, preprocess(values, width))


def predict_spectrum(portable, raw103):
    """Predict the rich reference from raw absorbance at 684:3:990 nm."""
    model, width = _model(portable, 'rich')
    return _predict(model, preprocess(raw103, width, rich=True))


def emulate_channels(spectra, weights):
    """Offline finite-band emulation with supplied frozen response weights.

    This is separate from candidate runtime inference. Like mango.optics, it
    computes -log10(sum(w * 10**(-A))) after a stable row shift. It applies no
    float32 conversion; the registered caller controls the spectral boundary.
    """
    raw = np.asarray(spectra)
    single = raw.ndim == 1
    absorbance = _matrix(raw, 103, 'Emulation spectra')
    weights = np.asarray(weights, dtype=np.float64)
    if (weights.ndim != 2 or weights.shape[0] != 103 or weights.shape[1] < 1 or
            not np.isfinite(weights).all() or np.any(weights < 0) or
            not np.allclose(weights.sum(axis=0), 1.0, rtol=1e-12, atol=1e-12)):
        raise ValueError('Weights must have 103 rows and finite nonnegative unit-sum columns')
    shift = absorbance.min(axis=1, keepdims=True)
    ratio = np.power(10.0, -(absorbance - shift)) @ weights
    if np.any(ratio <= 0) or not np.isfinite(ratio).all():
        raise ValueError('Channel intensity underflow; inspect absorbance units')
    result = -np.log10(ratio) + shift
    return result[0] if single else result
