"""Matched stopping-only policies for externally supplied, fixed-order paths.

The caller supplies grouped out-of-fold training predictions and a disjoint
calibration set. This module does not read data, choose an acquisition order,
fit a spectral predictor, or select a threshold on evaluation outcomes. Each
row of ``x[:, depth, :]`` must contain only information acquired at that depth.
"""

import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


DEPTHS = np.arange(2, 9, dtype=int)
OBJECTIVES = ('two_reference', 'single_reference')
DEFAULT_THRESHOLD_GRID = np.linspace(0.0, 1.0, 21)


class ConstantProbability:
    """Serializable fallback when the fitting labels contain one class."""

    def __init__(self, probability):
        self.probability = float(probability)
        self.classes_ = np.array([0, 1])
        self.n_iter_ = np.array([0])

    def predict_proba(self, x):
        positive = np.full(len(x), self.probability)
        return np.column_stack([1.0 - positive, positive])


def _features(x, name='x'):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 3 or x.shape[1] != len(DEPTHS) or x.shape[0] == 0 or x.shape[2] == 0:
        raise ValueError(name + ' must have nonempty shape (N, 7, D), for depths 2 through 8')
    if not np.isfinite(x[:, :-1]).all():
        raise ValueError(name + ' nonterminal observed-state features must be finite')
    return x


def _path(partial, n=None):
    partial = np.asarray(partial, dtype=np.float64)
    if partial.ndim != 2 or partial.shape[1] != len(DEPTHS) or partial.shape[0] == 0:
        raise ValueError('partial predictions must have nonempty shape (N, 7)')
    if n is not None and len(partial) != n:
        raise ValueError('Feature and prediction row counts differ')
    if not np.isfinite(partial).all():
        raise ValueError('Partial predictions must be finite')
    return partial


def _vector(values, n, name):
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (n,) or not np.isfinite(values).all():
        raise ValueError(name + ' must be a finite vector with one value per scan')
    return values


def _prediction_data(partial, bank, rich, y, n=None):
    partial = _path(partial, n)
    n = len(partial)
    bank, rich, y = [_vector(v, n, name) for v, name in
                     [(bank, 'bank'), (rich, 'rich'), (y, 'y')]]
    if not np.allclose(partial[:, -1], bank, rtol=1e-6, atol=1e-6):
        raise ValueError('Depth-eight prediction must equal the same complete-bank reference')
    return partial, bank, rich, y


def stopping_labels(partial, bank, rich, y, delta=0.5):
    """Assay-relative material-gain labels for the six nonterminal depths."""
    partial, bank, rich, y = _prediction_data(partial, bank, rich, y)
    if not np.isfinite(delta) or delta < 0:
        raise ValueError('delta must be finite and nonnegative')
    error = np.abs(y[:, None] - partial[:, :-1])
    return {'two_reference': error - np.abs(y - bank)[:, None] > delta,
            'single_reference': error - np.abs(y - rich)[:, None] > delta}


def apply_stopping(partial, probabilities, threshold):
    """Stop at the first p <= threshold; force termination at eight readings."""
    partial = _path(partial)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.shape != partial.shape:
        raise ValueError('Probability and prediction paths must have identical shapes')
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Probability threshold must lie in [0, 1]')
    nonterminal = probabilities[:, :-1]
    if not np.isfinite(nonterminal).all() or np.any((nonterminal < 0) | (nonterminal > 1)):
        raise ValueError('Nonterminal probabilities must be finite and lie in [0, 1]')
    stops = np.column_stack([nonterminal <= threshold, np.ones(len(partial), dtype=bool)])
    indices = stops.argmax(axis=1)
    return {'predictions': partial[np.arange(len(partial)), indices],
            'pulses': DEPTHS[indices].copy(), 'indices': indices,
            'stop_probabilities': np.where(indices == len(DEPTHS) - 1, 0.0,
                                           probabilities[np.arange(len(partial)), indices])}


def predict_probabilities(bundle, x, objective='two_reference', raw=False):
    """Compute each state's probability independently; terminal zero is forced."""
    if objective not in OBJECTIVES:
        raise ValueError('Unknown stopping objective: ' + str(objective))
    x = _features(x)
    if x.shape[2] != bundle['feature_count']:
        raise ValueError('Runtime feature width differs from the fitted representation')
    flat = x[:, :-1].reshape(-1, x.shape[2])
    probability = bundle['models'][objective].predict_proba(flat)[:, 1]
    if not raw:
        probability = bundle['calibrators'][objective].predict(probability)
    result = np.zeros(x.shape[:2], dtype=np.float64)
    result[:, :-1] = probability.reshape(len(x), len(DEPTHS) - 1)
    return result


def _metrics(y, prediction, pulses, bank, rich, delta):
    error = prediction - y
    absolute = np.abs(error)
    bank_error, rich_error = np.abs(y - bank), np.abs(y - rich)
    early = pulses < DEPTHS[-1]
    missed = early & (absolute - bank_error > delta)
    total = float(np.sum((y - np.mean(y)) ** 2))
    bank_rmsep = float(np.sqrt(np.mean(bank_error ** 2)))
    rmsep = float(np.sqrt(np.mean(error ** 2)))
    return {'n': len(y), 'rmsep': rmsep, 'mae': float(absolute.mean()),
            'bias': float(error.mean()), 'r2': float(1 - np.sum(error ** 2) / total) if total > 0 else None,
            'bank_rmsep': bank_rmsep, 'rmsep_increase_vs_bank': rmsep - bank_rmsep,
            'mean_pulses': float(pulses.mean()), 'median_pulses': float(np.median(pulses)),
            'p95_pulses': float(np.percentile(pulses, 95)), 'early_n': int(early.sum()),
            'early_fraction': float(early.mean()), 'missed_n': int(missed.sum()),
            'missed_rate': float(missed.sum() / early.sum()) if early.any() else None,
            'missed_unconditional': float(missed.mean()),
            'bank_loss_n': int(np.sum(bank_error - rich_error > delta)),
            'bank_loss_rate': float(np.mean(bank_error - rich_error > delta)),
            'large_absolute_error_n': int(np.sum(absolute > 2.0)),
            'large_absolute_error_rate': float(np.mean(absolute > 2.0))}


def _visited_calibration(probability, labels, indices):
    probability = np.asarray(probability, dtype=float)
    visited = np.arange(len(DEPTHS) - 1)[None, :] <= indices[:, None]
    p, target = probability[:, :-1][visited], labels[visited].astype(float)
    return {'visited_states': int(visited.sum()), 'visited_positive_n': int(target.sum()),
            'visited_brier': float(np.mean((p - target) ** 2)),
            'visited_observed_fraction': float(target.mean()),
            'visited_mean_probability': float(p.mean())}


def threshold_frontier(partial, probabilities, bank, rich, y, objective='two_reference',
                       thresholds=None, delta=0.5):
    """Score a supplied fixed grid; caller determines whether rows may select."""
    partial, bank, rich, y = _prediction_data(partial, bank, rich, y)
    if objective not in OBJECTIVES:
        raise ValueError('Unknown stopping objective: ' + str(objective))
    thresholds = _threshold_grid(thresholds)
    labels = stopping_labels(partial, bank, rich, y, delta)[objective]
    rows = []
    for index, threshold in enumerate(thresholds):
        selected = apply_stopping(partial, probabilities, threshold)
        rows.append(dict(_metrics(y, selected['predictions'], selected['pulses'], bank, rich, delta),
                         **_visited_calibration(probabilities, labels, selected['indices']),
                         objective=objective, threshold_index=index, threshold=float(threshold)))
    return rows


def _threshold_grid(thresholds):
    thresholds = DEFAULT_THRESHOLD_GRID.copy() if thresholds is None else np.asarray(thresholds, dtype=float)
    if thresholds.ndim != 1 or len(thresholds) == 0 or not np.isfinite(thresholds).all():
        raise ValueError('Threshold grid must be a nonempty finite vector')
    if np.any((thresholds < 0) | (thresholds > 1)) or np.any(np.diff(thresholds) <= 0):
        raise ValueError('Threshold grid must be strictly increasing within [0, 1]')
    return thresholds


def select_thresholds(frontier, target_pulses=4.0, engineering_max_pulses=6.0,
                      engineering_rmsep_margin=0.25):
    """Select only from calibration rows using registered deterministic rules."""
    if not frontier:
        raise ValueError('No calibration frontier rows were supplied')
    if not (DEPTHS[0] <= target_pulses <= DEPTHS[-1] and
            DEPTHS[0] <= engineering_max_pulses <= DEPTHS[-1] and
            np.isfinite(engineering_rmsep_margin) and engineering_rmsep_margin > 0):
        raise ValueError('Invalid pulse target or engineering margin')
    scientific = min(frontier, key=lambda r: (abs(r['mean_pulses'] - target_pulses),
                                              r['rmsep'], r['threshold']))
    feasible = [r for r in frontier if r['mean_pulses'] <= engineering_max_pulses + 1e-12 and
                r['rmsep_increase_vs_bank'] <= engineering_rmsep_margin + 1e-12]
    def violation(row):
        return (max(0.0, row['mean_pulses'] / engineering_max_pulses - 1.0),
                max(0.0, row['rmsep_increase_vs_bank'] / engineering_rmsep_margin - 1.0))
    engineering = min(feasible, key=lambda r: (r['mean_pulses'], r['rmsep'], r['threshold'])) if feasible else min(
        frontier, key=lambda r: (max(violation(r)), sum(violation(r)), r['rmsep'], r['mean_pulses'], r['threshold']))
    return {'scientific': dict(scientific, selection_rule='closest mean to four, then RMSEP, then lower threshold',
                               target_pulses=float(target_pulses)),
            'engineering': dict(engineering, feasible=bool(feasible),
                                selection_rule='fewest readings among feasible, then RMSEP, then lower threshold' if feasible else
                                'descriptive fallback: minimum maximum normalized violation, then total violation, RMSEP, readings, threshold',
                                max_mean_pulses=float(engineering_max_pulses),
                                max_rmsep_increase=float(engineering_rmsep_margin))}


def fit_stopping(train_x, train_partial, train_bank, train_rich, train_y,
                 cal_x, cal_partial, cal_bank, cal_rich, cal_y, *,
                 train_groups=None, cal_groups=None, seed=42, delta=0.5, threshold_grid=None):
    """Fit matched logistic heads, then isotonic calibration and frozen rules.

    Spectral predictors underlying the training labels must be grouped OOF;
    verifying their fit provenance is the caller's responsibility. Calibration
    and threshold selection intentionally share the reserved calibration set;
    the outer held season remains separate. Every scan contributes six states
    of equal weight, with no class or group reweighting.
    """
    train_x, cal_x = _features(train_x, 'train_x'), _features(cal_x, 'cal_x')
    if train_x.shape[2] != cal_x.shape[2]:
        raise ValueError('Training and calibration feature widths differ')
    train_partial, train_bank, train_rich, train_y = _prediction_data(
        train_partial, train_bank, train_rich, train_y, len(train_x))
    cal_partial, cal_bank, cal_rich, cal_y = _prediction_data(
        cal_partial, cal_bank, cal_rich, cal_y, len(cal_x))
    groups = {'checked': False}
    if (train_groups is None) != (cal_groups is None):
        raise ValueError('Supply both training and calibration groups, or neither')
    if train_groups is not None:
        train_groups, cal_groups = np.asarray(train_groups).astype(str), np.asarray(cal_groups).astype(str)
        if train_groups.shape != (len(train_x),) or cal_groups.shape != (len(cal_x),):
            raise ValueError('Group arrays must have one identifier per scan')
        overlap = set(train_groups) & set(cal_groups)
        if overlap:
            raise ValueError('Training and calibration groups overlap: ' + ', '.join(sorted(overlap)))
        groups = {'checked': True, 'train': sorted(set(train_groups)), 'calibration': sorted(set(cal_groups))}
    thresholds = _threshold_grid(threshold_grid)
    train_labels = stopping_labels(train_partial, train_bank, train_rich, train_y, delta)
    cal_labels = stopping_labels(cal_partial, cal_bank, cal_rich, cal_y, delta)
    flat = train_x[:, :-1].reshape(-1, train_x.shape[2])
    config = {'seed': int(seed), 'delta': float(delta), 'C': 1.0, 'solver': 'lbfgs',
              'max_iter': 2000, 'tol': 1e-7, 'equal_scan_weights': True,
              'nonterminal_depths': DEPTHS[:-1].tolist(), 'terminal_depth': int(DEPTHS[-1]),
              'calibration': 'isotonic on every nonterminal fixed-order calibration state',
              'calibration_and_threshold_same_groups': True, 'target_pulses': 4.0,
              'engineering_max_mean_pulses': 6.0, 'engineering_rmsep_margin': 0.25}
    bundle = {'models': {}, 'calibrators': {}, 'feature_count': train_x.shape[2],
              'config': config, 'threshold_grid': thresholds.tolist(), 'group_isolation': groups,
              'fit_diagnostics': {}, 'calibration_diagnostics': {}, 'calibration_frontier': {}, 'selections': {}}
    for objective in OBJECTIVES:
        label = train_labels[objective].ravel().astype(int)
        if np.unique(label).size == 1:
            model = ConstantProbability(label[0])
            warning_messages = []
        else:
            model = LogisticRegression(C=config['C'], solver=config['solver'], max_iter=config['max_iter'],
                                       tol=config['tol'], random_state=seed, class_weight=None)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', ConvergenceWarning)
                model.fit(flat, label)
            warning_messages = [str(w.message) for w in caught]
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                raise RuntimeError('Stopping logistic model did not converge: ' + objective)
        bundle['models'][objective] = model
        raw = predict_probabilities(bundle, cal_x, objective, raw=True)
        calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
        calibrator.fit(raw[:, :-1].ravel(), cal_labels[objective].ravel().astype(int))
        bundle['calibrators'][objective] = calibrator
        probability = predict_probabilities(bundle, cal_x, objective)
        bundle['fit_diagnostics'][objective] = {'scans': len(train_x), 'states': len(label),
            'positive_n': int(label.sum()), 'positive_fraction': float(label.mean()),
            'constant_class_fallback': isinstance(model, ConstantProbability),
            'iterations': model.n_iter_.tolist(), 'warnings': warning_messages}
        bundle['calibration_diagnostics'][objective] = {'scans': len(cal_x), 'states': int(cal_labels[objective].size),
            'positive_n': int(cal_labels[objective].sum()),
            'raw_brier': float(np.mean((raw[:, :-1] - cal_labels[objective]) ** 2)),
            'calibrated_brier': float(np.mean((probability[:, :-1] - cal_labels[objective]) ** 2)),
            'scope': 'In-sample isotonic calibration diagnostic; objectives have different target events'}
        frontier = threshold_frontier(cal_partial, probability, cal_bank, cal_rich, cal_y,
                                      objective, thresholds, delta)
        bundle['calibration_frontier'][objective] = frontier
        bundle['selections'][objective] = select_thresholds(frontier)
    return bundle


def evaluate_stopping(bundle, x, partial, bank, rich, y, include_frontier=True):
    """Score frozen decisions and fixed lengths; outcomes never select a rule."""
    x = _features(x)
    partial, bank, rich, y = _prediction_data(partial, bank, rich, y, len(x))
    labels = stopping_labels(partial, bank, rich, y, bundle['config']['delta'])
    records, policies, frontiers = [], {}, {}
    for objective in OBJECTIVES:
        probability = predict_probabilities(bundle, x, objective)
        for point in ('scientific', 'engineering'):
            selected_rule = bundle['selections'][objective][point]
            selected = apply_stopping(partial, probability, selected_rule['threshold'])
            key = objective + '|' + point
            policies[key] = dict(selected, probabilities=probability,
                                 threshold=float(selected_rule['threshold']))
            record = dict(_metrics(y, selected['predictions'], selected['pulses'], bank, rich, bundle['config']['delta']),
                          **_visited_calibration(probability, labels[objective], selected['indices']),
                          objective=objective, operating_point=point, threshold=float(selected_rule['threshold']),
                          threshold_index=int(selected_rule['threshold_index']))
            if point == 'engineering':
                record['calibration_engineering_feasible'] = selected_rule['feasible']
                record['evaluation_engineering_pass'] = bool(record['mean_pulses'] <= 6.0 and
                                                              record['rmsep_increase_vs_bank'] <= 0.25)
            records.append(record)
        if include_frontier:
            frontiers[objective] = threshold_frontier(partial, probability, bank, rich, y, objective,
                                                      bundle['threshold_grid'], bundle['config']['delta'])
    fixed = []
    for index, depth in enumerate(DEPTHS):
        selected = {'predictions': partial[:, index].copy(), 'pulses': np.full(len(x), depth, dtype=int),
                    'indices': np.full(len(x), index, dtype=int)}
        key = 'fixed_length|' + str(depth)
        policies[key] = selected
        fixed.append(dict(_metrics(y, selected['predictions'], selected['pulses'], bank, rich, bundle['config']['delta']),
                          objective='fixed_length', operating_point='depth_' + str(depth), fixed_depth=int(depth)))
    return {'records': records, 'policies': policies, 'frontiers': frontiers, 'fixed_length_controls': fixed}
