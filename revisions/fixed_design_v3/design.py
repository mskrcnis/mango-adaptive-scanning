"""Design-group-only subset and nested-order selection.

The caller must supply only the reserved design rows. No core fitting,
calibration, held-season, or external data are accepted by this interface.
All scores use equal scan weights; selection is deterministic and exhaustive.
"""

from itertools import combinations, permutations
import warnings

import numpy as np
from sklearn.model_selection import GroupKFold

from revisions.methodology_v2.pipeline import SubsetRegressors, fixed_order, path_indices


FAMILIES = ('pls', 'ridge')
INITIAL = (0, 7)
REMAINING = tuple(range(1, 7))


def validate_masks(masks):
    """Require exactly the 64 reachable masks of the specified eight-LED bank."""
    masks = np.asarray(masks)
    if masks.shape != (64, 8):
        raise ValueError('Expected exactly 64 masks over eight bank channels')
    if not np.isin(masks, [False, True]).all():
        raise ValueError('Masks must contain only binary values')
    masks = masks.astype(bool)
    expected = set()
    for count in range(len(REMAINING) + 1):
        for subset in combinations(REMAINING, count):
            row = np.zeros(8, dtype=bool)
            row[list(INITIAL) + list(subset)] = True
            expected.add(tuple(row))
    if set(map(tuple, masks)) != expected:
        raise ValueError('Masks must contain every unique subset preserving initial channels 0 and 7')
    if not masks[-1].all():
        raise ValueError('The full-bank mask must be last for SubsetRegressors')
    return masks


def _outcomes(y, n):
    y = np.asarray(y, dtype=float)
    if y.shape != (n,) or not np.isfinite(y).all():
        raise ValueError('y must be a finite vector with one outcome per design scan')
    return y


def crossfit_design(x, y, groups, masks, folds=3, *, checkpoint_fold=None):
    """Generate group-OOF predictions for both fixed predictor families.

    Each model and its scaler see only the design groups in that fold's
    fitting partition. PLS uses min(6, subset size) components; ridge uses
    alpha=10 after fold-local standardization, via the unchanged v2 helper.
    Local row identifiers refer exclusively to the arrays passed here. An
    optional synchronous ``checkpoint_fold(fold, fn)`` callback can cache each
    fold; this module never chooses a cache path or reads data from disk.
    """
    masks = validate_masks(masks)
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 8 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError('x must be a nonempty finite design matrix with eight columns')
    y = _outcomes(y, len(x))
    y_fit = y.astype(np.float32)
    if not np.isfinite(y_fit).all():
        raise ValueError('Design outcomes must be representable as finite float32 values')
    groups = np.asarray(groups)
    if groups.shape != (len(x),):
        raise ValueError('groups must have one identifier per design scan')
    groups = groups.astype(str)
    if any(value in ('', 'nan', 'None', 'NaT') for value in groups):
        raise ValueError('Design group identifiers must not be missing')
    unique = np.unique(groups)
    if len(unique) < 3:
        raise ValueError('At least three distinct design groups are required')
    if isinstance(folds, bool) or not isinstance(folds, (int, np.integer)) or folds < 3:
        raise ValueError('folds must be an integer of at least three')
    count = min(int(folds), len(unique))
    splitter = GroupKFold(n_splits=count)
    predictions = {family: np.full((len(x), len(masks)), np.nan) for family in FAMILIES}
    fold_ids = np.full(len(x), -1, dtype=int)
    provenance = []
    for fold, (fit, target) in enumerate(splitter.split(x, y, groups)):
        fit_groups, target_groups = set(groups[fit]), set(groups[target])
        if fit_groups & target_groups:
            raise AssertionError('A design group crossed a fitting/OOF boundary')
        if len(fit) <= 6:
            raise ValueError('Each design fitting fold needs more than six scans for six-component PLS')
        def fit_fold():
            fold_predictions, fold_warnings = {}, {}
            for family in FAMILIES:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    fitted = SubsetRegressors(family, masks).fit(x[fit], y_fit[fit])
                    fold_predictions[family] = fitted.predict(x[target])
                fold_warnings[family] = [str(item.message) for item in caught]
            return {'predictions': fold_predictions, 'warnings': fold_warnings,
                    'fit_local_row_ids': fit.tolist(), 'target_local_row_ids': target.tolist()}
        value = fit_fold() if checkpoint_fold is None else checkpoint_fold(fold, fit_fold)
        if value['fit_local_row_ids'] != fit.tolist() or value['target_local_row_ids'] != target.tolist():
            raise AssertionError('Cached design fold does not match the current row partition')
        for family in FAMILIES:
            predicted = np.asarray(value['predictions'][family], dtype=float)
            if predicted.shape != (len(target), len(masks)) or not np.isfinite(predicted).all():
                raise ValueError('Invalid cached design-fold predictions for ' + family)
            predictions[family][target] = predicted
        warnings_by_family = value['warnings']
        fold_ids[target] = fold
        provenance.append({'fold': fold, 'fit_groups': sorted(fit_groups),
                           'target_groups': sorted(target_groups),
                           'fit_local_row_ids': fit.tolist(), 'target_local_row_ids': target.tolist(),
                           'n_fit': len(fit), 'n_target': len(target), 'warnings': warnings_by_family})
    if np.any(fold_ids < 0) or not all(np.isfinite(p).all() for p in predictions.values()):
        raise RuntimeError('Design cross-fitting left missing or nonfinite predictions')
    return {'predictions': predictions, 'fold_ids': fold_ids, 'provenance': provenance,
            'n': len(x), 'n_groups': len(unique), 'n_folds': count, 'masks': masks.copy(),
            'weighting': 'equal scan weights', 'fitting_dtype': 'float32',
            'model_settings': {'pls': {'components': 'min(6, observed channels)', 'scale': True},
                               'ridge': {'alpha': 10.0, 'standardization': 'design-fold fitting rows only'}}}


def select_design(predictions, y, masks, centers):
    """Select one family's per-depth subsets and best nested acquisition order.

    ``predictions`` must be the N-by-64 design-OOF predictions for one family.
    The nested objective sums mean squared assay error over depths 2 through 7.
    The complete-bank endpoint is common to every order and is excluded.
    Exact score ties use lexicographic local channel indices; no epsilon-based
    tie changes the selected design. All 720 candidates remain in the result.
    """
    masks = validate_masks(masks)
    predictions = np.asarray(predictions, dtype=float)
    if predictions.ndim != 2 or predictions.shape[1] != 64 or len(predictions) == 0:
        raise ValueError('predictions must have nonempty shape (N, 64) for one predictor family')
    if not np.isfinite(predictions).all():
        raise ValueError('Design OOF predictions must be finite')
    y = _outcomes(y, len(predictions))
    centers = np.asarray(centers, dtype=float)
    if centers.shape != (8,) or not np.isfinite(centers).all() or np.any(np.diff(centers) <= 0):
        raise ValueError('centers must be eight distinct finite increasing wavelengths')
    with np.errstate(over='ignore'):
        mse = np.mean((predictions - y[:, None]) ** 2, axis=0)
    if not np.isfinite(mse).all():
        raise ValueError('Design squared errors are not finite')
    observed = [tuple(np.flatnonzero(mask).tolist()) for mask in masks]
    depth = masks.sum(axis=1)
    by_depth, depth_margins = {}, {}
    for size in range(2, 9):
        candidates = sorted(np.flatnonzero(depth == size).tolist(), key=lambda j: (mse[j], observed[j]))
        by_depth[str(size)] = int(candidates[0])
        depth_margins[str(size)] = float(mse[candidates[1]] - mse[candidates[0]]) if len(candidates) > 1 else None
    scores = []
    for suffix in permutations(REMAINING):
        order = list(INITIAL + suffix)
        path = path_indices(masks, order)
        score = float(np.sum(mse[path[:-1]]))
        scores.append({'order': order, 'path_indices': path.tolist(), 'score': score,
                       'depth_mse': mse[path].tolist()})
    ranked = sorted(scores, key=lambda row: (row['score'], tuple(row['order'])))
    best, second = ranked[:2]
    catalog = fixed_order(centers)
    catalog_path = path_indices(masks, catalog)
    mask_scores = [{'mask_index': j, 'indices': list(observed[j]), 'depth': int(depth[j]),
                    'mse': float(mse[j]), 'rmsep': float(np.sqrt(mse[j]))}
                   for j in range(len(masks))]
    return {'mask_mse': mse, 'mask_scores': mask_scores, 'by_depth': by_depth,
            'by_depth_second_best_mse_margin': depth_margins,
            'order': best['order'], 'path_indices': best['path_indices'], 'order_score': best['score'],
            'order_scores': scores, 'n_candidate_orders': len(scores),
            'second_best_order': second['order'], 'second_best_order_score': second['score'],
            'order_margin': float(second['score'] - best['score']),
            'exact_best_order_ties': sum(row['score'] == best['score'] for row in scores),
            'catalog_order': catalog, 'catalog_path_indices': catalog_path.tolist(),
            'catalog_order_score': float(np.sum(mse[catalog_path[:-1]])),
            'selection_objective': 'sum of equal-scan design-OOF MSE over depths 2 through 7',
            'tie_break': 'lexicographic observed local indices for subsets; full local order for orders',
            'initial_indices': list(INITIAL), 'centers_nm': centers.tolist()}
