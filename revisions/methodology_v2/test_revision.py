"""Synthetic contracts for the isolated, development-only methodology revision."""
from __future__ import annotations

import ast
import copy
import inspect
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mango.models import PLSReference
from revisions.methodology_v2 import pipeline, stopping


def reachable_masks():
    masks = []
    for size in range(7):
        for subset in combinations(range(1, 7), size):
            mask = np.zeros(8, dtype=bool)
            mask[[0, 7, *subset]] = True
            masks.append(mask)
    return np.asarray(masks)


@pytest.fixture(autouse=True)
def prohibit_external_access(monkeypatch):
    """Any exercised external reader fails before it could inspect external rows."""
    import builtins
    import io
    import mango.data

    def forbidden(*args, **kwargs):
        raise AssertionError('V2 synthetic tests attempted an external-data read')

    monkeypatch.setattr(mango.data, 'load_external', forbidden)
    monkeypatch.setattr(mango.data, 'load_external_features', forbidden)
    for name in ('load_external', 'load_external_features'):
        for module in (pipeline, stopping):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    ordinary_open, ordinary_io_open = builtins.open, io.open

    def guard(opener):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)):
                name = str(file).replace('\\', '/').lower()
                if '/sealed/' in name or any(part.startswith('external') for part in name.split('/')):
                    forbidden()
            return opener(file, *args, **kwargs)
        return checked

    monkeypatch.setattr(builtins, 'open', guard(ordinary_open))
    monkeypatch.setattr(io, 'open', guard(ordinary_io_open))


@pytest.fixture(scope='module')
def spectra():
    rng = np.random.RandomState(821)
    x = rng.normal(size=(96, 8))
    x *= np.linspace(.3, 2.1, 8)
    y = 15 + x @ np.array([.9, 1.3, -.7, .2, -.4, .8, .5, -.6])
    y += rng.normal(scale=.07, size=len(x))
    return x, y


@pytest.mark.parametrize('family', ['pls', 'ridge'])
def test_every_subset_uses_exactly_its_acquired_columns(spectra, family):
    x, y = spectra
    masks = reachable_masks()
    fitted = pipeline.SubsetRegressors(family, masks).fit(x[:72], y[:72])
    actual = fitted.predict(x[72:])
    assert actual.shape == (24, 64)
    for index, mask in enumerate(masks):
        reference = (PLSReference(min(6, int(mask.sum()))) if family == 'pls'
                     else make_pipeline(StandardScaler(), Ridge(alpha=10)))
        reference.fit(x[:72, mask], y[:72])
        np.testing.assert_allclose(actual[:, index], reference.predict(x[72:, mask]).ravel(),
                                   atol=1e-11, rtol=0)


@pytest.mark.parametrize('family', ['pls', 'ridge'])
def test_subset_inference_ignores_hidden_values_and_preserves_endpoint(spectra, family):
    x, y = spectra
    masks = reachable_masks()
    fitted = pipeline.SubsetRegressors(family, masks).fit(x[:72], y[:72])
    values = x[72:80].copy()
    all_predictions = fitted.predict(values)
    for column in [0, 1, 17, 42, 63]:
        mask = masks[column]
        changed = values.copy()
        changed[:, ~mask] = np.nan
        baseline = fitted.predict_observed(values, mask)
        np.testing.assert_array_equal(baseline, fitted.predict_observed(changed, mask))
        changed[:, ~mask] = 1e25
        np.testing.assert_array_equal(baseline, fitted.predict_observed(changed, mask))
        np.testing.assert_allclose(baseline, all_predictions[:, column], atol=1e-12, rtol=0)
    full = masks[-1]
    np.testing.assert_allclose(fitted.predict_observed(np.asfortranarray(values), full),
                               all_predictions[:, -1], atol=1e-12, rtol=0)
    changed = values.copy()
    changed[:, 0] += 2
    assert np.max(np.abs(fitted.predict_observed(changed, masks[0]) -
                         fitted.predict_observed(values, masks[0]))) > .1


def test_acquired_zero_is_a_measurement_not_a_missing_marker(spectra):
    x, y = spectra
    masks = reachable_masks()
    fitted = pipeline.SubsetRegressors('ridge', masks).fit(x, y)
    values = np.zeros((3, 8))
    values[:, 0] = [-1, 0, 1]
    initial = masks[0]
    with_zero = initial.copy()
    with_zero[1] = True
    actual = fitted.predict_observed(values, with_zero)
    reference = make_pipeline(StandardScaler(), Ridge(alpha=10)).fit(x[:, with_zero], y)
    np.testing.assert_allclose(actual, reference.predict(values[:, with_zero]), atol=1e-12, rtol=0)
    hidden = values.copy()
    hidden[:, 1] = np.nan
    np.testing.assert_array_equal(fitted.predict_observed(hidden, initial),
                                   fitted.predict_observed(values, initial))
    assert np.max(np.abs(actual - fitted.predict_observed(values, initial))) > 1e-5


def test_mixed_mask_batch_never_uses_another_rows_unacquired_channels(spectra):
    x, y = spectra
    masks = reachable_masks()
    fitted = pipeline.SubsetRegressors('ridge', masks).fit(x[:72], y[:72])
    selected = np.array([0, 17, 63, 1, 42, 17, 0, 63])
    row_masks = masks[selected]
    values = x[72:80].copy()
    expected = fitted.predict(values)[np.arange(len(values)), selected]
    values[~row_masks] = np.nan
    np.testing.assert_allclose(fitted.predict_observed(values, row_masks), expected, atol=1e-12, rtol=0)


def test_observed_stopper_features_do_not_expose_later_readings(spectra):
    x, _ = spectra
    scaler = StandardScaler().fit(x[:72])
    masks = reachable_masks()
    indices = pipeline.path_indices(masks, pipeline.fixed_order(np.arange(8)))
    values = x[72:80].copy()
    expected = pipeline.observed_path(scaler, values, masks, indices)
    assert expected.shape == (8, 7, 16)
    for depth, index in enumerate(indices):
        changed = values.copy()
        changed[:, ~masks[index]] = np.nan
        actual = pipeline.observed_path(scaler, changed, masks, [index])[:, 0]
        np.testing.assert_array_equal(actual, expected[:, depth])
        np.testing.assert_array_equal(actual[:, :8][:, ~masks[index]],
                                       np.zeros((8, (~masks[index]).sum())))
        np.testing.assert_array_equal(actual[:, 8:], np.broadcast_to(masks[index], values.shape))


def test_fixed_order_path_has_charged_initial_pair_and_no_repeats():
    centers = np.arange(8, dtype=float)
    order = pipeline.fixed_order(centers)
    assert list(order) == [0, 7, 3, 5, 1, 2, 4, 6]
    masks = reachable_masks()
    indices = pipeline.path_indices(masks, order)
    path = masks[np.asarray(indices)]
    np.testing.assert_array_equal(path.sum(1), np.arange(2, 9))
    np.testing.assert_array_equal(path[0], masks[0])
    assert path[-1].all()
    for depth in range(1, 7):
        added = np.flatnonzero(path[depth] & ~path[depth - 1])
        np.testing.assert_array_equal(added, [order[depth + 1]])
        assert np.all(path[depth - 1] <= path[depth])


def test_signed_endpoint_decomposition_keeps_harmful_measurements():
    y = np.full(4, 10.)
    mlp7 = np.array([13., 11., 9., 10.])
    pls7 = np.array([12., 12., 10., 11.])
    pls8 = np.array([11., 10.5, 12., 10.])
    result = pipeline.endpoint_components(y, mlp7, pls7, pls8)
    total, estimator, measurement = [result[key] for key in ['total', 'estimator', 'measurement']]
    np.testing.assert_array_equal(total, [2., .5, -1., 0.])
    np.testing.assert_array_equal(estimator, [1., -1., 1., -1.])
    np.testing.assert_array_equal(measurement, [1., 1.5, -2., 1.])
    np.testing.assert_allclose(total, estimator + measurement, atol=1e-14, rtol=0)
    assert np.any(estimator < 0) and np.any(measurement < 0)


class DevelopmentFixture(SimpleNamespace):
    def __len__(self):
        return len(self.y)


def grouped_fixture():
    rng = np.random.RandomState(509)
    n = 72
    channels = rng.normal(size=(n, 8)).astype(np.float32)
    channels[:, 0] = np.arange(n)
    y = (15 + .03 * channels[:, 0] + channels[:, 1:].sum(1)).astype(np.float32)
    seasons = np.repeat([1, 2, 3], 24)
    local_groups = np.tile(np.repeat(np.arange(6), 4), 3)
    groups = np.asarray(['s%d_g%d' % (s, g) for s, g in zip(seasons, local_groups)])
    data = DevelopmentFixture(y=y, seasons=seasons, groups=groups,
        row_ids=np.asarray(['row_%03d' % i for i in range(n)]), X=rng.normal(size=(n, 103)))
    fit = np.flatnonzero((seasons != 3) & (local_groups < 3))
    cal = np.flatnonzero((seasons != 3) & (local_groups == 3))
    valid = np.flatnonzero(seasons == 3)
    fold_ids = local_groups[fit]
    oof_predictions = np.empty(len(fit), dtype=np.float32)
    folds = []
    for fold in range(3):
        train, held = fit[fold_ids != fold], fit[fold_ids == fold]
        oof_predictions[fold_ids == fold] = PLSReference(6).fit(channels[train], y[train]).predict(channels[held])
        folds.append(dict(fold=fold, fit_groups=sorted(set(groups[train])),
                          target_groups=sorted(set(groups[held]))))
    bundle = {'fit_row_ids': data.row_ids[fit], 'calibration_row_ids': data.row_ids[cal],
              'bank_indices': list(range(8)), 'masks': reachable_masks(),
              'bank_predictor': PLSReference(6).fit(channels[fit], y[fit]),
              'oof': {'groups': groups[fit], 'y': y[fit], 'fold_ids': fold_ids,
                      'folds': folds, 'bank_predictions': oof_predictions}}
    return data, channels, bundle, (fit, cal, valid)


def test_group_assignment_isolation_and_tampered_provenance_rejected():
    data, channels, bundle, expected = grouped_fixture()
    actual = pipeline.validate_case(data, bundle, 3)
    for a, b in zip(actual, expected):
        np.testing.assert_array_equal(a, b)
    changed = copy.deepcopy(bundle)
    changed['calibration_row_ids'][0] = changed['fit_row_ids'][0]
    with pytest.raises(AssertionError):
        pipeline.validate_case(data, changed, 3)
    changed = copy.deepcopy(bundle)
    changed['oof']['fold_ids'][0] = 1
    with pytest.raises(AssertionError):
        pipeline.validate_case(data, changed, 3)
    changed = copy.deepcopy(data)
    changed.seasons[-1] = 4
    with pytest.raises(AssertionError, match='development'):
        pipeline.validate_case(changed, bundle, 3)


def test_actual_subset_fits_and_scalers_exclude_held_groups(monkeypatch):
    data, channels, bundle, (fit, cal, valid) = grouped_fixture()
    scaler_rows, subset_rows = [], []
    original_fit = pipeline.SubsetRegressors.fit

    class TrackingScaler(StandardScaler):
        def fit(self, values, y=None, sample_weight=None):
            scaler_rows.append(np.rint(np.asarray(values)[:, 0]).astype(int))
            return super().fit(values, y=y, sample_weight=sample_weight)

    def tracked_fit(self, x, y):
        subset_rows.append((self.family, np.rint(x[:, 0]).astype(int)))
        return original_fit(self, x, y)

    monkeypatch.setattr(pipeline, 'StandardScaler', TrackingScaler)
    monkeypatch.setattr(pipeline.SubsetRegressors, 'fit', tracked_fit)
    monkeypatch.setattr(pipeline, 'checkpoint', lambda name, fingerprint, action: action())
    result = pipeline.build_linear(data, channels, bundle, 3, 'synthetic', 'synthetic-only')
    expected_rows = [fit[bundle['oof']['fold_ids'] != fold] for fold in range(3)] + [fit]
    assert len(subset_rows) == 8
    assert len(scaler_rows) == 4 * 64
    for fold, expected in enumerate(expected_rows):
        for family, actual in subset_rows[fold * 2:(fold + 1) * 2]:
            np.testing.assert_array_equal(actual, expected)
            assert not set(data.groups[actual]) & set(data.groups[np.concatenate([cal, valid])])
        for actual in scaler_rows[fold * 64:(fold + 1) * 64]:
            np.testing.assert_array_equal(actual, expected)
        provenance = result['provenance'][fold]
        assert set(provenance['fit_groups']).isdisjoint(provenance['target_groups'])
    assert result['predictions']['pls']['train'].shape == (len(fit), 64)
    assert result['oof_endpoint_max_float32_difference'] < 1e-5


def stopping_fixture():
    rng = np.random.RandomState(122)

    def partition(n, prefix):
        x = rng.normal(size=(n, 7, 5))
        x[:, :, -1] = np.arange(2, 9)
        y = 15 + rng.normal(size=n)
        bank = y + rng.uniform(.3, .8, size=n)
        rich = y + rng.uniform(.05, .3, size=n)
        partial = y[:, None] + rng.uniform(-2.2, 2.2, size=(n, 7))
        partial[:, -1] = bank
        groups = np.array([prefix + str(index // 4) for index in range(n)])
        return x, partial, bank, rich, y, groups

    return partition(48, 'fit'), partition(24, 'cal')


def fit_stopper(train, cal, **kwargs):
    return stopping.fit_stopping(*train[:5], *cal[:5], train_groups=train[5],
                                  cal_groups=cal[5], seed=42,
                                  threshold_grid=np.linspace(0, 1, 5), **kwargs)


def test_stopper_uses_only_current_state_and_forces_terminal_probability():
    train, cal = stopping_fixture()
    fitted = fit_stopper(train, cal)
    for objective in ['two_reference', 'single_reference']:
        for raw in [False, True]:
            original = stopping.predict_probabilities(fitted, cal[0], objective, raw=raw)
            assert original.shape == (24, 7)
            assert np.isfinite(original).all()
            assert np.all((original >= 0) & (original <= 1))
            np.testing.assert_array_equal(original[:, -1], np.zeros(24))
            changed = cal[0].copy()
            changed[:, 3:] = 1e7
            altered = stopping.predict_probabilities(fitted, changed, objective, raw=raw)
            np.testing.assert_array_equal(original[:, :3], altered[:, :3])


def test_stopper_rejects_overlapping_fit_and_calibration_groups():
    train, cal = stopping_fixture()
    overlapping = list(cal)
    overlapping[5] = cal[5].copy()
    overlapping[5][0] = train[5][0]
    with pytest.raises((ValueError, AssertionError), match='(?i)group|overlap|disjoint'):
        fit_stopper(train, overlapping)


def test_stopper_rejects_a_different_full_bank_endpoint():
    train, cal = stopping_fixture()
    wrong = list(train)
    wrong[2] = train[2] + .01
    with pytest.raises((ValueError, AssertionError), match='(?i)bank|endpoint|terminal|last'):
        fit_stopper(wrong, cal)


def test_stopping_labels_use_signed_absolute_error_gain_and_strict_delta():
    y = np.array([10., 10.])
    bank = np.array([11., 10.])
    rich = np.array([10., 11.])
    partial = np.array([[11.5, 11.50001, 10., 9., 12., 8., 11.],
                        [10.5, 10.50001, 9.5, 9.49999, 10., 12., 10.]])
    labels = stopping.stopping_labels(partial, bank, rich, y)
    np.testing.assert_array_equal(labels['two_reference'],
        [[False, True, False, False, True, True], [False, True, False, True, False, True]])
    np.testing.assert_array_equal(labels['single_reference'],
        [[True, True, False, True, True, True], [False, False, False, False, False, True]])


def test_stop_model_fit_and_isotonic_calibration_use_separate_rows(monkeypatch):
    train, cal = stopping_fixture()
    logistic_calls, isotonic_calls = [], []
    original_logistic = stopping.LogisticRegression.fit
    original_isotonic = stopping.IsotonicRegression.fit

    def logistic_fit(self, x, y, *args, **kwargs):
        logistic_calls.append((np.array(x), np.array(y), dict(kwargs)))
        return original_logistic(self, x, y, *args, **kwargs)

    def isotonic_fit(self, x, y, *args, **kwargs):
        isotonic_calls.append((np.array(x), np.array(y)))
        return original_isotonic(self, x, y, *args, **kwargs)

    monkeypatch.setattr(stopping.LogisticRegression, 'fit', logistic_fit)
    monkeypatch.setattr(stopping.IsotonicRegression, 'fit', isotonic_fit)
    fitted = fit_stopper(train, cal)
    assert len(logistic_calls) == len(isotonic_calls) == 2
    expected_x = train[0][:, :-1].reshape(-1, train[0].shape[-1])
    train_error = np.abs(train[4][:, None] - train[1][:, :-1])
    cal_error = np.abs(cal[4][:, None] - cal[1][:, :-1])
    for index, objective in enumerate(stopping.OBJECTIVES):
        reference_index = 2 if objective == 'two_reference' else 3
        train_labels = (train_error - np.abs(train[4] - train[reference_index])[:, None] > .5).ravel()
        cal_labels = (cal_error - np.abs(cal[4] - cal[reference_index])[:, None] > .5).ravel()
        train_x, actual_train_labels, kwargs = logistic_calls[index]
        np.testing.assert_array_equal(train_x, expected_x)
        np.testing.assert_array_equal(actual_train_labels, train_labels)
        weights = kwargs.get('sample_weight')
        assert weights is None or np.all(np.asarray(weights) == np.asarray(weights)[0])
        cal_raw = stopping.predict_probabilities(fitted, cal[0], objective, raw=True)[:, :-1].ravel()
        np.testing.assert_array_equal(isotonic_calls[index][0], cal_raw)
        np.testing.assert_array_equal(isotonic_calls[index][1], cal_labels)
    assert set(fitted['group_isolation']['train']).isdisjoint(fitted['group_isolation']['calibration'])


def test_constant_class_and_unused_terminal_features_are_well_defined():
    train, cal = stopping_fixture()
    for partition in [train, cal]:
        partition[0][:, -1] = np.nan
        partition[1][:] = partition[2][:, None]
    fitted = fit_stopper(train, cal)
    assert fitted['fit_diagnostics']['two_reference']['constant_class_fallback']
    actual = stopping.predict_probabilities(fitted, cal[0], 'two_reference')
    np.testing.assert_array_equal(actual, np.zeros((24, 7)))


def test_threshold_equality_and_earliest_stop_and_terminal_fallback():
    partial = np.arange(21, dtype=float).reshape(3, 7)
    probabilities = np.array([[.7, .6, .5, .2, .1, .1, 1.],
                              [.9, .9, .9, .9, .9, .9, 1.],
                              [.5, .2, .1, .1, .1, .1, 1.]])
    chosen = stopping.apply_stopping(partial, probabilities, .5)
    np.testing.assert_array_equal(chosen['indices'], [2, 6, 0])
    np.testing.assert_array_equal(chosen['pulses'], [4, 8, 2])
    np.testing.assert_array_equal(chosen['predictions'], [2., 13., 14.])


def test_threshold_selection_uses_budget_then_error_then_threshold():
    def row(threshold, pulses, error, increase):
        return dict(threshold=threshold, mean_pulses=pulses, rmsep=error,
                    rmsep_increase_vs_bank=increase)
    frontier = [row(.1, 3.5, 1.2, .15), row(.2, 4.5, .9, .1),
                row(.3, 4.5, .9, .1), row(.4, 4.9, .1, .0),
                row(.5, 2.0, .7, .4)]
    selected = stopping.select_thresholds(frontier)
    assert selected['scientific']['threshold'] == .2
    assert selected['engineering']['threshold'] == .1
    assert selected['engineering']['feasible']
    fallback = stopping.select_thresholds([row(.1, 8., 1.5, .3), row(.2, 6., 1.0, .5)])
    assert not fallback['engineering']['feasible']
    assert fallback['engineering']['threshold'] == .1
    boundary = stopping.select_thresholds([row(.1, 6., 1., .25)])
    assert boundary['engineering']['feasible']


def test_evaluation_outcomes_cannot_reselect_thresholds_or_change_decisions(monkeypatch):
    train, cal = stopping_fixture()
    fitted = fit_stopper(train, cal)

    def forbidden(*args, **kwargs):
        raise AssertionError('Evaluation attempted threshold selection')

    monkeypatch.setattr(stopping, 'select_thresholds', forbidden)
    first = stopping.evaluate_stopping(fitted, *cal[:5])
    changed = list(cal)
    changed[4] = cal[4] + np.linspace(-20, 30, len(cal[4]))
    second = stopping.evaluate_stopping(fitted, *changed[:5])
    for key in first['policies']:
        for field in ['predictions', 'pulses', 'indices']:
            np.testing.assert_array_equal(first['policies'][key][field], second['policies'][key][field])
    assert first['records'][0]['rmsep'] != second['records'][0]['rmsep']
    assert len(first['fixed_length_controls']) == 7
    for objective in stopping.OBJECTIVES:
        assert len(first['frontiers'][objective]) == 5


def test_runtime_signatures_do_not_accept_assays_or_future_references():
    forbidden = {'y', 'assay', 'season', 'metadata', 'reference_predictions', 'bank', 'rich'}
    for function in [pipeline.SubsetRegressors.predict_observed,
                     stopping.predict_probabilities, stopping.apply_stopping]:
        assert not forbidden.intersection(inspect.signature(function).parameters)


def test_v2_source_has_no_external_loader_or_scorer_imports_or_calls():
    forbidden = {'load_external', 'load_external_features', 'score_external', 'evaluate_external'}
    for module in (pipeline, stopping):
        tree = ast.parse(Path(module.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith('mango.external')
                assert not forbidden.intersection(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith('mango.external') for alias in node.names)
            elif isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else None)
                assert name not in forbidden
