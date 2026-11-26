"""Independent synthetic checks of v3 design-only subset and order selection."""
from __future__ import annotations

import ast
import copy
import json
import os
from types import SimpleNamespace
from itertools import combinations, permutations
from pathlib import Path

import numpy as np
import pytest
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from revisions.fixed_design_v3 import design
from revisions.fixed_design_v3 import pipeline


def masks_fixture():
    masks = []
    for size in range(7):
        for subset in combinations(range(1, 7), size):
            mask = np.zeros(8, dtype=bool)
            mask[[0, 7, *subset]] = True
            masks.append(mask)
    return np.asarray(masks)


@pytest.fixture(autouse=True)
def prohibit_external_reads(monkeypatch):
    import builtins
    import io
    import mango.data

    def forbidden(*args, **kwargs):
        raise AssertionError('Synthetic design test attempted to read external data')

    monkeypatch.setattr(mango.data, 'load_external', forbidden)
    monkeypatch.setattr(mango.data, 'load_external_features', forbidden)

    def guarded(opener):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)):
                parts = str(file).replace('\\', '/').lower().split('/')
                if 'sealed' in parts or any(part.startswith('external') for part in parts):
                    forbidden()
            return opener(file, *args, **kwargs)
        return checked

    monkeypatch.setattr(builtins, 'open', guarded(builtins.open))
    monkeypatch.setattr(io, 'open', guarded(io.open))


def independent_prefix_indices(masks, order):
    result = []
    for depth in range(2, 9):
        expected = set(order[:depth])
        matches = [i for i, mask in enumerate(masks) if set(np.flatnonzero(mask)) == expected]
        assert len(matches) == 1
        result.append(matches[0])
    return result


def independent_optimum(predictions, y, masks):
    mse = np.mean((predictions - y[:, None]) ** 2, axis=0)
    by_depth = {}
    for depth in range(2, 9):
        candidates = [i for i, m in enumerate(masks) if m.sum() == depth]
        by_depth[str(depth)] = min(candidates, key=lambda i: (mse[i], tuple(np.flatnonzero(masks[i]))))
    orders = []
    for permutation in permutations(range(1, 7)):
        order = (0, 7, *permutation)
        indices = independent_prefix_indices(masks, order)
        orders.append((float(np.sum(mse[indices[:-1]])), order, indices))
    orders.sort(key=lambda row: (row[0], row[1]))
    return mse, by_depth, orders


def assert_complete_optimum(actual, predictions, y, masks):
    mse, by_depth, orders = independent_optimum(predictions, y, masks)
    np.testing.assert_allclose(actual['mask_mse'], mse, atol=1e-12, rtol=0)
    assert {str(k): int(v) for k, v in actual['by_depth'].items()} == by_depth
    assert list(actual['order']) == list(orders[0][1])
    assert list(actual['path_indices']) == orders[0][2]
    assert len(actual['mask_scores']) == 64
    assert len(actual['order_scores']) == 720
    scored = {tuple(row['order']): row for row in actual['order_scores']}
    assert len(scored) == 720
    for score, order, indices in orders:
        assert scored[order]['path_indices'] == indices
        assert scored[order]['score'] == pytest.approx(score, abs=1e-12, rel=0)
    path = masks[np.asarray(actual['path_indices'])]
    np.testing.assert_array_equal(path.sum(1), np.arange(2, 9))
    assert path[-1].all()
    assert all(np.all(before <= after) for before, after in zip(path[:-1], path[1:]))


def test_exhaustive_selection_matches_independent_64_mask_720_order_calculation():
    rng = np.random.RandomState(831)
    masks = masks_fixture()
    y = rng.normal(size=29)
    predictions = rng.normal(size=(29, 64)) + rng.uniform(-2, 2, size=64)
    actual = design.select_design(predictions, y, masks, np.arange(8))
    assert_complete_optimum(actual, predictions, y, masks)


def test_lexicographic_ties_are_independent_of_mask_column_order():
    masks = masks_fixture()
    permutation = np.r_[np.random.RandomState(71).permutation(63), 63]
    shuffled = masks[permutation]
    predictions = np.ones((12, 64))
    y = np.zeros(12)
    actual = design.select_design(predictions, y, shuffled, np.arange(8))
    assert_complete_optimum(actual, predictions, y, shuffled)
    assert list(actual['order']) == [0, 7, 1, 2, 3, 4, 5, 6]
    for depth in range(2, 9):
        expected = set([0, 7, *range(1, depth - 1)])
        assert set(np.flatnonzero(shuffled[actual['by_depth'][str(depth)]])) == expected


def test_independent_best_subsets_are_not_used_as_an_incoherent_path():
    masks = masks_fixture()
    costs = np.full(64, 10.)
    for i, mask in enumerate(masks):
        if mask.sum() >= 4 and not mask[1]:
            costs[i] = 0.
        if set(np.flatnonzero(mask)) == {0, 1, 7}:
            costs[i] = 0.
    predictions = np.broadcast_to(np.sqrt(costs), (8, 64)).copy()
    y = np.zeros(8)
    actual = design.select_design(predictions, y, masks, np.arange(8))
    assert_complete_optimum(actual, predictions, y, masks)
    best3 = masks[actual['by_depth']['3']]
    best4 = masks[actual['by_depth']['4']]
    assert not np.all(best3 <= best4)
    assert actual['order'][2] != 1


def test_full_bank_error_cannot_change_preterminal_order_selection():
    masks = masks_fixture()
    rng = np.random.RandomState(3)
    predictions = rng.normal(size=(18, 64))
    y = rng.normal(size=18)
    first = design.select_design(predictions, y, masks, np.arange(8))
    changed = predictions.copy()
    changed[:, -1] += 1e6
    second = design.select_design(changed, y, masks, np.arange(8))
    assert first['order'] == second['order']
    np.testing.assert_array_equal([row['score'] for row in first['order_scores']],
                                   [row['score'] for row in second['order_scores']])


@pytest.mark.parametrize('problem', ['missing_mask', 'duplicate', 'missing_endpoint'])
def test_incomplete_or_invalid_mask_search_space_is_rejected(problem):
    masks = masks_fixture()
    if problem == 'missing_mask':
        masks = np.delete(masks, 3, axis=0)
    elif problem == 'duplicate':
        masks[3] = masks[2]
    else:
        masks[3, 0] = False
    with pytest.raises((ValueError, AssertionError)):
        design.select_design(np.zeros((9, len(masks))), np.zeros(9), masks, np.arange(8))


@pytest.mark.parametrize('n_folds', [3, 6])
def test_design_group_crossfit_and_every_scaler_use_only_training_populations(monkeypatch, n_folds):
    from revisions.methodology_v2 import pipeline as v2
    rng = np.random.RandomState(66)
    sizes = [3, 5, 4, 7, 2, 6]
    groups = np.repeat(np.arange(6), sizes).astype(str)
    x = rng.normal(size=(len(groups), 8)).astype(np.float32)
    x[:, 0] = np.arange(len(x))
    y = 12 + .03 * x[:, 0] + x[:, 1] - x[:, 5]
    masks = masks_fixture()
    fitted_rows, scaler_rows = [], []
    original_fit = v2.SubsetRegressors.fit

    def tracked_fit(self, values, outcomes):
        fitted_rows.append((self.family, np.rint(values[:, 0]).astype(int)))
        return original_fit(self, values, outcomes)

    class TrackingScaler(StandardScaler):
        def fit(self, values, y=None, sample_weight=None):
            scaler_rows.append(np.rint(np.asarray(values)[:, 0]).astype(int))
            return super().fit(values, y=y, sample_weight=sample_weight)

    monkeypatch.setattr(v2.SubsetRegressors, 'fit', tracked_fit)
    monkeypatch.setattr(v2, 'StandardScaler', TrackingScaler)
    result = design.crossfit_design(x, y, groups, masks, folds=n_folds)
    folds = list(GroupKFold(n_splits=n_folds).split(x, y, groups))
    assert len(fitted_rows) == n_folds * 2 and len(scaler_rows) == n_folds * 64
    fold_ids = np.asarray(result['fold_ids'])
    for index, (train, target) in enumerate(folds):
        np.testing.assert_array_equal(fold_ids[target], np.full(len(target), index))
        for family, rows in fitted_rows[index * 2:index * 2 + 2]:
            np.testing.assert_array_equal(rows, train)
            assert not set(groups[rows]) & set(groups[target])
        for rows in scaler_rows[index * 64:(index + 1) * 64]:
            np.testing.assert_array_equal(rows, train)
        record = result['provenance'][index]
        assert set(record['fit_groups']) == set(groups[train])
        assert set(record['target_groups']) == set(groups[target])
        if n_folds == 6:
            assert len(record['target_groups']) == 1
            assert len(record['fit_groups']) == 5
        np.testing.assert_array_equal(record['fit_local_row_ids'], train)
        np.testing.assert_array_equal(record['target_local_row_ids'], target)
    for family in ['pls', 'ridge']:
        assert result['predictions'][family].shape == (len(x), 64)
        assert np.isfinite(result['predictions'][family]).all()
    for group in set(groups):
        assert len(set(fold_ids[groups == group])) == 1


def test_held_design_population_outcomes_do_not_change_its_own_oof_predictions():
    rng = np.random.RandomState(39)
    x = rng.normal(size=(36, 8))
    y = 12 + x[:, 0] + .4 * x[:, 5] + rng.normal(scale=.1, size=36)
    groups = np.repeat(np.arange(6), 6)
    first = design.crossfit_design(x, y, groups, masks_fixture(), folds=6)
    changed = y.copy()
    changed[groups == 2] += np.linspace(-100, 100, 6)
    second = design.crossfit_design(x, changed, groups, masks_fixture(), folds=6)
    for family in ['pls', 'ridge']:
        np.testing.assert_array_equal(first['predictions'][family][groups == 2],
                                       second['predictions'][family][groups == 2])
        assert not np.array_equal(first['predictions'][family][groups != 2],
                                   second['predictions'][family][groups != 2])


def test_completed_design_fold_cache_resumes_without_fit_and_rejects_corruption(monkeypatch):
    rng = np.random.RandomState(107)
    x = rng.normal(size=(30, 8))
    y = 12 + x[:, 0] - x[:, 3]
    groups = np.repeat(np.arange(6), 5)
    cached, called = {}, []

    def checkpoint(fold, fit):
        called.append(fold)
        if fold not in cached:
            cached[fold] = fit()
        return cached[fold]

    first = design.crossfit_design(x, y, groups, masks_fixture(), folds=6, checkpoint_fold=checkpoint)
    assert called == list(range(6))

    def forbidden_fit(*args, **kwargs):
        raise AssertionError('A complete design checkpoint was refitted')

    monkeypatch.setattr(design.SubsetRegressors, 'fit', forbidden_fit)
    second = design.crossfit_design(x, y, groups, masks_fixture(), folds=6, checkpoint_fold=checkpoint)
    for family in ['pls', 'ridge']:
        np.testing.assert_array_equal(first['predictions'][family], second['predictions'][family])
    original = copy.deepcopy(cached[0])
    cached[0]['target_local_row_ids'] = list(reversed(original['target_local_row_ids']))
    with pytest.raises(AssertionError, match='partition'):
        design.crossfit_design(x, y, groups, masks_fixture(), folds=6, checkpoint_fold=checkpoint)
    cached[0] = copy.deepcopy(original)
    cached[0]['predictions']['pls'] = original['predictions']['pls'][:, :-1]
    with pytest.raises(ValueError, match='cached'):
        design.crossfit_design(x, y, groups, masks_fixture(), folds=6, checkpoint_fold=checkpoint)
    cached[0] = copy.deepcopy(original)
    cached[0]['predictions']['ridge'][0, 0] = np.nan
    with pytest.raises(ValueError, match='cached'):
        design.crossfit_design(x, y, groups, masks_fixture(), folds=6, checkpoint_fold=checkpoint)


def pipeline_fixture():
    rng = np.random.RandomState(46)
    groups = np.repeat(np.arange(12), 4)
    seasons = np.repeat([1, 2, 3], 16)
    data = SimpleNamespace(X=rng.normal(size=(48, 10)), y=rng.normal(size=48),
        groups=groups.astype(str), seasons=seasons, row_ids=np.asarray(['row_%d' % i for i in range(48)]),
        wavelengths=np.arange(10))
    role_groups = {'fit_row_ids': [2, 6], 'bank_design_row_ids': [0, 1, 4, 5],
                   'calibration_row_ids': [3, 7], 'validation_row_ids': [8, 9, 10, 11]}
    assignment = {role: data.row_ids[np.isin(groups, selected)].tolist()
                  for role, selected in role_groups.items()}
    assignment['held_season'] = 3
    return data, assignment


def test_pipeline_selection_ignores_all_core_calibration_and_held_values(monkeypatch):
    data, assignment = pipeline_fixture()
    roles = pipeline.partition_indices(data, assignment)
    bank = [0, 1, 3, 4, 5, 6, 8, 9]
    optical_calls, crossfit_calls = [], []

    def optical(values, wavelengths):
        optical_calls.append(np.array(values))
        return np.array(values)

    def crossfit(x, y, groups, masks, folds, checkpoint_fold=None):
        crossfit_calls.append((x.copy(), y.copy(), groups.copy(), folds))
        predictions = np.column_stack([x[:, mask].mean(1) + .03 * y for mask in masks])
        return {'predictions': {'pls': predictions, 'ridge': predictions * .9}, 'masks': masks}

    monkeypatch.setattr(pipeline, 'channel_matrix', optical)
    monkeypatch.setattr(pipeline, 'crossfit_design', crossfit)
    first = pipeline.build_design(data, assignment, bank, np.arange(8))
    changed = copy.deepcopy(data)
    outside = np.concatenate([roles['fit'], roles['cal'], roles['valid']])
    changed.X[outside] = np.nan
    changed.y[outside] = np.nan
    second = pipeline.build_design(changed, assignment, bank, np.arange(8))
    for recorded in optical_calls:
        np.testing.assert_array_equal(recorded, data.X[roles['design']])
    for x, y, groups, folds in crossfit_calls:
        np.testing.assert_array_equal(x, data.X[roles['design']][:, bank].astype(np.float32))
        np.testing.assert_array_equal(y, data.y[roles['design']])
        np.testing.assert_array_equal(groups, data.groups[roles['design']])
        assert folds == len(set(groups)) == 4
    for family in ['pls', 'ridge']:
        assert pipeline.canonical_hash(first['selections'][family]) == pipeline.canonical_hash(second['selections'][family])
    np.testing.assert_array_equal(first['design_row_ids'], second['design_row_ids'])
    overlapping = copy.deepcopy(assignment)
    overlapping['fit_row_ids'][0] = overlapping['bank_design_row_ids'][0]
    with pytest.raises(AssertionError, match='Population overlaps'):
        pipeline.build_design(data, overlapping, bank, np.arange(8))


def test_new_order_features_hide_future_values_and_preserve_full_endpoint():
    masks = masks_fixture()
    rng = np.random.RandomState(99)
    full = np.column_stack([rng.normal(size=(9, 8)), np.ones((9, 8))])
    indices = independent_prefix_indices(masks, [0, 7, 6, 4, 2, 5, 3, 1])
    expected = pipeline.features_from_full(full, masks, indices)
    np.testing.assert_array_equal(expected[:, -1], full)
    for depth, index in enumerate(indices):
        changed = full.copy()
        changed[:, :8][:, ~masks[index]] = np.nan
        actual = pipeline.features_from_full(changed, masks, [index])[:, 0]
        np.testing.assert_array_equal(actual, expected[:, depth])
        np.testing.assert_array_equal(actual[:, 8:], np.broadcast_to(masks[index], (9, 8)))
    bad = full.copy()
    bad[0, 8] = 0
    with pytest.raises(ValueError, match='availability'):
        pipeline.features_from_full(bad, masks, indices)


@pytest.mark.parametrize('stage', ['design', 'evaluate'])
def test_read_guard_blocks_external_prior_writes_and_premature_case_access(monkeypatch, tmp_path, stage):
    root = tmp_path / 'project'
    here = root / 'revisions/fixed_design_v3'
    v2 = root / 'revisions/methodology_v2'
    hooks = []
    monkeypatch.setattr(pipeline, 'ROOT', root)
    monkeypatch.setattr(pipeline, 'HERE', here)
    monkeypatch.setattr(pipeline, 'V2', v2)
    monkeypatch.setattr(pipeline, 'GUARD', None)
    monkeypatch.setattr(pipeline, 'READ_PATHS', set())
    monkeypatch.setattr(pipeline.sys, 'addaudithook', hooks.append)
    pipeline.install_guard(stage)
    assert len(hooks) == 1
    hook = hooks[0]

    def opening(path, mode='r', flags=os.O_RDONLY):
        hook('open', (str(path), mode, flags))

    for path in [root / 'data/sealed/season4.csv', root / 'data/processed/external_features.csv',
                 root / 'results/model.joblib', v2 / 'results/predictions.csv']:
        with pytest.raises(PermissionError):
            opening(path)
    for path in [root / 'mango/models.py', root / 'data/processed/development.csv',
                 v2 / 'results/checkpoints/case_s1_swap_mid_seed42.joblib']:
        with pytest.raises(PermissionError, match='read-only'):
            opening(path, 'wb', os.O_WRONLY | os.O_CREAT)
    opening(here / 'results/new_checkpoint.joblib', 'wb', os.O_WRONLY | os.O_CREAT)
    opening(root / 'data/processed/development.csv')
    opening(root / 'results/fold_assignments.json')
    for held, bank in pipeline.CASES:
        case = pipeline.source_path(held, bank)
        if stage == 'design':
            with pytest.raises(PermissionError, match='unavailable to design'):
                opening(case)
        else:
            opening(case)
    with pytest.raises(RuntimeError, match='separate processes'):
        pipeline.install_guard('evaluate' if stage == 'design' else 'design')


def test_design_lock_requires_every_completed_case_and_rejects_changed_bytes(monkeypatch, tmp_path):
    here = tmp_path / 'v3'
    out = here / 'results'
    (out / 'checkpoints').mkdir(parents=True)
    monkeypatch.setattr(pipeline, 'HERE', here)
    monkeypatch.setattr(pipeline, 'OUT', out)
    registration = {'dependency': 'synthetic_dependency'}
    for number, (held, bank) in enumerate(pipeline.CASES):
        path = out / 'checkpoints' / ('design_s%d_%s.joblib' % (held, bank))
        path.write_bytes(('synthetic design %d' % number).encode())
        path.with_suffix('.json').write_text(json.dumps({'status': 'complete',
            'dependency': pipeline.canonical_hash([registration['dependency'], 'design', held, bank]),
            'sha256': pipeline.digest(path)}))
    lock = pipeline.lock_designs(registration)
    assert pipeline.validate_lock(registration) == lock
    with pytest.raises(AssertionError):
        pipeline.validate_lock({'dependency': 'changed'})
    victim = here / next(iter(lock['design_sha256']))
    original = victim.read_bytes()
    victim.write_bytes(original + b' changed')
    with pytest.raises(AssertionError):
        pipeline.validate_lock(registration)
    victim.write_bytes(original)
    incomplete = copy.deepcopy(lock)
    del incomplete['design_sha256'][next(iter(incomplete['design_sha256']))]
    (out / 'design_lock.json').write_text(json.dumps(incomplete))
    with pytest.raises(AssertionError):
        pipeline.validate_lock(registration)
    substituted = copy.deepcopy(lock)
    old_name = next(iter(substituted['design_sha256']))
    del substituted['design_sha256'][old_name]
    replacement = out / 'checkpoints/unregistered_design.joblib'
    replacement.write_bytes(b'unregistered design')
    substituted['design_sha256'][str(replacement.relative_to(here))] = pipeline.digest(replacement)
    (out / 'design_lock.json').write_text(json.dumps(substituted))
    with pytest.raises(AssertionError):
        pipeline.validate_lock(registration)


def test_preservation_verifier_detects_changed_or_missing_prior_artifact(monkeypatch, tmp_path):
    root = tmp_path / 'project'
    here = root / 'revisions/fixed_design_v3'
    here.mkdir(parents=True)
    prior = root / 'revisions/methodology_v2/summary.txt'
    prior.parent.mkdir(parents=True)
    prior.write_text('prior scientific artifact')
    monkeypatch.setattr(pipeline, 'ROOT', root)
    monkeypatch.setattr(pipeline, 'HERE', here)
    monkeypatch.setattr(pipeline, 'protected_files', lambda: [prior])
    pipeline.snapshot()
    assert pipeline.verify_preservation()['passed']
    prior.write_text('changed artifact')
    assert pipeline.verify_preservation()['changed'] == ['revisions/methodology_v2/summary.txt']
    prior.unlink()
    assert not pipeline.verify_preservation()['passed']


def test_source_predictions_are_replayed_exactly_without_held_out_refitting(monkeypatch):
    rng = np.random.RandomState(82)
    masks = masks_fixture()
    catalog = [0, 7, 3, 5, 1, 2, 4, 6]
    order = [0, 7, 1, 2, 3, 4, 5, 6]
    catalog_indices = independent_prefix_indices(masks, catalog)
    selected_indices = independent_prefix_indices(masks, order)
    subsets = {str(depth): int(np.flatnonzero(masks.sum(1) == depth)[-1]) for depth in range(2, 9)}
    selection = dict(by_depth=subsets, catalog_order=catalog, order=order,
                     catalog_path_indices=catalog_indices, path_indices=selected_indices)
    source = dict(masks=masks, bank_indices=list(range(8)), held_season=3, bank='synthetic', data={}, families={})
    selected = dict(crossfit={'masks': masks}, bank_indices=list(range(8)),
                    selections={family: copy.deepcopy(selection) for family in ['pls', 'ridge']},
                    role_row_ids={}, role_groups={'design': ['design-only']})
    for split, role, n in [('train', 'fit', 12), ('cal', 'cal', 8), ('valid', 'valid', 10)]:
        full = np.column_stack([rng.normal(size=(n, 8)), np.ones((n, 8))])
        rows = np.asarray([split + '_row%d' % i for i in range(n)])
        groups = np.asarray([split + '_group%d' % (i // 2) for i in range(n)])
        y = rng.normal(size=n)
        source['data'][split] = dict(row_ids=rows, groups=groups, y=y, rich=y + .2,
                                    features=pipeline.features_from_full(full, masks, catalog_indices))
        selected['role_row_ids'][role] = rows
        selected['role_groups'][role] = sorted(set(groups))
    for family in ['pls', 'ridge']:
        predictions = {split: rng.normal(size=(len(info['y']), 64)) for split, info in source['data'].items()}
        source['families'][family] = {'all_predictions': predictions,
            'paths': {split: values[:, catalog_indices] for split, values in predictions.items()},
            'stopping': {'saved_catalog_object': family}}
    fit_calls = []

    def fitted(*args, **kwargs):
        fit_calls.append((args, kwargs))
        return {'new_design_fit': len(fit_calls)}

    def probabilities(bundle, features, objective):
        return np.zeros(features.shape[:2])

    monkeypatch.setattr(pipeline, 'fit_stopping', fitted)
    monkeypatch.setattr(pipeline, 'predict_probabilities', probabilities)
    actual = pipeline.evaluate_case(source, selected)
    assert len(fit_calls) == 2
    for index, family in enumerate(['pls', 'ridge']):
        result = actual['families'][family]
        assert result['orders']['catalog']['stopping'] is source['families'][family]['stopping']
        for variant in ['catalog', 'designed']:
            indices = catalog_indices if variant == 'catalog' else selected_indices
            for split in source['data']:
                predictions = source['families'][family]['all_predictions'][split]
                np.testing.assert_array_equal(result['orders'][variant]['paths'][split], predictions[:, indices])
                np.testing.assert_array_equal(result['orders'][variant]['paths'][split][:, -1], predictions[:, -1])
        args, kwargs = fit_calls[index]
        np.testing.assert_array_equal(args[4], source['data']['train']['y'])
        np.testing.assert_array_equal(args[9], source['data']['cal']['y'])
        assert set(kwargs['train_groups']).isdisjoint(kwargs['cal_groups'])
        assert set(kwargs['train_groups']).isdisjoint(source['data']['valid']['groups'])
    changed = copy.deepcopy(source)
    changed['data']['valid']['y'] += 1e6
    pipeline.evaluate_case(changed, selected)
    for before, after in zip(fit_calls[:2], fit_calls[2:]):
        for a, b in zip(before[0], after[0]):
            np.testing.assert_array_equal(a, b)
    changed = copy.deepcopy(source)
    changed['data']['valid']['row_ids'] = changed['data']['valid']['row_ids'][::-1]
    with pytest.raises(AssertionError):
        pipeline.evaluate_case(changed, selected)
    changed = copy.deepcopy(source)
    changed['masks'][[1, 2]] = changed['masks'][[2, 1]]
    with pytest.raises(AssertionError):
        pipeline.evaluate_case(changed, selected)


def test_design_source_has_no_external_data_or_held_out_selection_dependencies():
    tree = ast.parse(Path(design.__file__).read_text())
    forbidden = {'load_external', 'load_external_features', 'score_external', 'evaluate_external',
                 'cal_y', 'held_y', 'valid_y', 'validation_y', 'core_y'}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or '').startswith('mango.external')
            assert not forbidden.intersection(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else None)
            assert name not in forbidden
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert not forbidden.intersection(argument.arg for argument in node.args.args)
