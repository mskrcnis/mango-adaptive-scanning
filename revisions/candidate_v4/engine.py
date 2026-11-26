"""In-memory final-candidate selection and fitting; no data or file access.

Direct sklearn PLS fitting reproduces the inherited PLSReference transform and
settings while retaining warnings that PLSReference suppresses. Selection uses
only caller-supplied development arrays. There is no internal validation claim
for the selected minimum, and no outcome-dependent hyperparameter search.
"""

from dataclasses import dataclass
from itertools import combinations
import warnings

import numpy as np
from sklearn.cross_decomposition import PLSRegression

from .inference import preprocess


def candidate_subsets():
    """The 15 lexicographically ordered six-of-eight endpoint-preserving sets."""
    return [(0,) + middle + (7,) for middle in combinations(range(1, 7), 4)]


def _outcomes(y, count):
    y = np.asarray(y, dtype=np.float64)
    if y.shape != (count,) or not np.isfinite(y).all():
        raise ValueError('y must contain one finite assay per development row')
    with np.errstate(over='ignore', invalid='ignore'):
        fit_y = y.astype(np.float32)
    if not np.isfinite(fit_y).all():
        raise ValueError('Fitting assays must be representable as finite float32')
    return y, fit_y


def _rows(indices, count, name):
    array = np.asarray(indices)
    if (array.ndim != 1 or len(array) == 0 or array.dtype.kind not in 'iu' or
            np.any(array < 0) or np.any(array >= count) or
            len(np.unique(array)) != len(array)):
        raise ValueError(name + ' must contain unique in-range integer row indices')
    return array.astype(np.int64, copy=True)


@dataclass
class FittedPLS:
    """Frozen transform plus sklearn estimator; .predict accepts raw readings."""

    model: object
    n_features: int
    rich: bool = False

    def predict(self, values):
        transformed = preprocess(values, self.n_features, rich=self.rich)
        predicted = self.model.predict(transformed).ravel()
        if not np.isfinite(predicted).all():
            raise ValueError('Fitted PLS produced nonfinite predictions')
        return predicted


def _fit(values, y_fit, components, *, rich=False):
    width = np.asarray(values).shape[1]
    transformed = preprocess(values, width, rich=rich)
    if len(transformed) <= components:
        raise ValueError('Registered PLS requires more fitting rows than components')
    estimator = PLSRegression(n_components=components, scale=True, max_iter=500,
                              tol=1e-6, copy=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        estimator.fit(transformed, y_fit)
    recorded = [{'category': item.category.__name__, 'message': str(item.message)}
                for item in caught]
    return FittedPLS(estimator, width, rich), recorded


def fit_fold(xbank, y, fit_indices, target_indices):
    """Fit all registered subsets on supplied rows and predict held-out rows.

    Group construction and exhaustive LOPO coverage belong to orchestration.
    This function verifies row disjointness and never fits on target outcomes.
    """
    xbank = preprocess(xbank, 8)
    _, y_fit = _outcomes(y, len(xbank))
    fit = _rows(fit_indices, len(xbank), 'fit_indices')
    target = _rows(target_indices, len(xbank), 'target_indices')
    if np.intersect1d(fit, target).size:
        raise ValueError('Fitting and target rows must be disjoint')
    predictions = np.empty((len(target), 15), dtype=np.float64)
    recorded = []
    for column, indices in enumerate(candidate_subsets()):
        model, caught = _fit(xbank[fit][:, indices], y_fit[fit], 6)
        predictions[:, column] = model.predict(xbank[target][:, indices])
        recorded.append({'subset_index': column, 'indices': list(indices), 'warnings': caught})
    return {'predictions': predictions, 'fit_indices': fit, 'target_indices': target,
            'warnings': recorded}


def select_subset(predictions, y):
    """Choose by float64 pooled scan MSE, then exact lexicographic ties."""
    predictions = np.asarray(predictions, dtype=np.float64)
    if (predictions.ndim != 2 or predictions.shape[1] != 15 or
            len(predictions) == 0 or not np.isfinite(predictions).all()):
        raise ValueError('Selection predictions must be a finite nonempty N-by-15 matrix')
    assays, _ = _outcomes(y, len(predictions))
    with np.errstate(over='ignore', invalid='ignore'):
        mse = np.mean((predictions - assays[:, None]) ** 2, axis=0)
    if not np.isfinite(mse).all():
        raise ValueError('Selection squared errors are nonfinite')
    subsets = candidate_subsets()
    ranked = sorted(range(len(subsets)), key=lambda index: (mse[index], subsets[index]))
    best, second = ranked[:2]
    scores = [{'index': index, 'indices': list(indices), 'mse': float(mse[index]),
               'rmsep': float(np.sqrt(mse[index]))}
              for index, indices in enumerate(subsets)]
    return {'scores': scores, 'selected_index': best, 'selected_indices': list(subsets[best]),
            'selected_mse': float(mse[best]), 'selected_rmsep': float(np.sqrt(mse[best])),
            'runner_up_index': second, 'margin': float(mse[second] - mse[best]),
            'exact_best_ties': int(np.sum(mse == mse[best])),
            'objective': 'pooled equal-scan development LOPO mean squared error',
            'tie_break': 'exact score then lexicographic selected local indices'}


def _portable(model):
    estimator = model.model
    # sklearn 1.3 stores coefficients for standardized X. Keeping this explicit
    # avoids cancellation from folding means into a large raw intercept.
    coefficients = np.asarray(estimator.coef_, dtype=np.float64).reshape(-1)
    mean = np.asarray(estimator._x_mean, dtype=np.float64)
    scale = np.asarray(estimator._x_std, dtype=np.float64)
    intercept = float(np.asarray(estimator.intercept_).reshape(-1)[0])
    raw_coefficients = coefficients / scale
    raw_intercept = intercept - float(mean @ raw_coefficients)
    if (coefficients.shape != (model.n_features,) or
            not np.isfinite(np.r_[coefficients, mean, scale, intercept, raw_intercept]).all() or
            np.any(scale <= 0)):
        raise ValueError('Cannot export invalid PLS coefficients')
    return {'n_features': model.n_features, 'n_components': int(estimator.n_components),
            'coefficients': coefficients.tolist(), 'intercept': intercept,
            'x_mean': mean.tolist(), 'x_std': scale.tolist(),
            'raw_linear_coefficients': raw_coefficients.tolist(),
            'raw_linear_intercept': raw_intercept,
            'preprocessing': 'snv_sg_second_derivative' if model.rich else 'raw_channels',
            'input_dtype': 'float32', 'math_dtype': 'float64',
            'scale': True, 'max_iter': 500, 'tol': 1e-6,
            'rich_settings': ({'snv_ddof': 0, 'snv_floor': 1e-8, 'window_length': 11,
                               'polyorder': 2, 'deriv': 2, 'delta_nm': 3.0}
                              if model.rich else None)}


def fit_final(xbank, xfull, y, indices):
    """Fit the selected six, full eight, and inherited rich PLS on equal rows."""
    xbank = preprocess(xbank, 8)
    xfull = preprocess(xfull, 103)
    if len(xbank) != len(xfull):
        raise ValueError('Bank and rich references require identical fitting rows')
    _, y_fit = _outcomes(y, len(xbank))
    raw_indices = np.asarray(indices)
    if raw_indices.dtype.kind not in 'iu' or raw_indices.ndim != 1:
        raise ValueError('Candidate indices must be a registered integer subset')
    indices = tuple(int(index) for index in raw_indices)
    if indices not in candidate_subsets():
        raise ValueError('Candidate indices must be one registered endpoint-preserving subset')
    models, recorded = {}, {}
    models['candidate'], recorded['candidate'] = _fit(xbank[:, indices], y_fit, 6)
    models['full_bank'], recorded['full_bank'] = _fit(xbank, y_fit, 6)
    models['rich'], recorded['rich'] = _fit(xfull, y_fit, 12, rich=True)
    portable = {'schema_version': 1, 'candidate_indices': list(indices),
                'candidate_channel_order': 'ascending registered bank index',
                'wavelengths_nm': list(range(684, 991, 3)),
                'models': {kind: _portable(model) for kind, model in models.items()}}
    return {'models': models, 'portable': portable, 'warnings': recorded,
            'n_fit': len(xbank), 'candidate_indices': list(indices)}
