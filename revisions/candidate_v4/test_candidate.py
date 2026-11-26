"""Synthetic invariants for candidate selection and frozen portable inference."""
import ast
import copy
import inspect
import json
import os
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

from revisions.candidate_v4 import engine, inference


@pytest.fixture(autouse=True)
def no_external_reads(monkeypatch):
    import builtins
    import io
    import mango.data
    def forbidden(*args, **kwargs):
        raise AssertionError('A synthetic candidate test attempted external-data access')
    monkeypatch.setattr(mango.data, 'load_external', forbidden)
    monkeypatch.setattr(mango.data, 'load_external_features', forbidden)
    def guard(opener):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)):
                parts = str(file).replace('\\', '/').lower().split('/')
                if 'sealed' in parts or any(part.startswith('external') for part in parts):
                    forbidden()
            return opener(file, *args, **kwargs)
        return checked
    monkeypatch.setattr(builtins, 'open', guard(builtins.open))
    monkeypatch.setattr(io, 'open', guard(io.open))


@pytest.fixture(scope='module')
def arrays():
    rng = np.random.RandomState(444)
    x = rng.normal(size=(64, 8))
    x[:, 0] = np.arange(len(x))
    full = rng.normal(size=(64, 103))
    y = 15 + .03 * x[:, 0] + x[:, 1] - .7 * x[:, 5] + rng.normal(scale=.1, size=len(x))
    return x, full, y


@pytest.fixture(scope='module')
def final(arrays):
    x, full, y = arrays
    return engine.fit_final(x, full, y, engine.candidate_subsets()[4])


def test_candidate_space_has_all_15_endpoint_preserving_six_subsets():
    expected = sorted(tuple(sorted((0, 7, *middle))) for middle in combinations(range(1, 7), 4))
    assert engine.candidate_subsets() == expected
    assert len(set(expected)) == 15
    assert all(len(set(indices)) == 6 and indices[0] == 0 and indices[-1] == 7 for indices in expected)


def test_selection_matches_all_scores_global_optimum_and_exact_ties():
    rng = np.random.RandomState(17)
    predictions = rng.normal(size=(31, 15))
    y = rng.normal(size=31)
    actual = engine.select_subset(predictions, y)
    mse = np.mean((predictions - y[:, None]) ** 2, axis=0)
    candidates = engine.candidate_subsets()
    rank = sorted(range(15), key=lambda i: (mse[i], candidates[i]))
    assert actual['selected_index'] == rank[0]
    assert actual['runner_up_index'] == rank[1]
    assert actual['selected_indices'] == list(candidates[rank[0]])
    assert actual['margin'] == pytest.approx(mse[rank[1]] - mse[rank[0]], abs=1e-14)
    for i, row in enumerate(actual['scores']):
        assert row['index'] == i and row['indices'] == list(candidates[i])
        assert row['mse'] == pytest.approx(mse[i], abs=1e-14)
        assert row['rmsep'] == pytest.approx(np.sqrt(mse[i]), abs=1e-14)
    tied = engine.select_subset(np.ones((7, 15)), np.zeros(7))
    assert tied['selected_index'] == 0 and tied['runner_up_index'] == 1
    assert tied['exact_best_ties'] == 15 and tied['margin'] == 0


def test_every_fold_model_and_its_autoscaling_use_only_fit_rows(monkeypatch, arrays):
    x, _, y = arrays
    fit, target = np.arange(40), np.arange(40, 64)
    original = engine.PLSRegression.fit
    fitted = []
    def tracking(self, values, outcomes, *args, **kwargs):
        result = original(self, values, outcomes, *args, **kwargs)
        fitted.append((values.copy(), outcomes.copy(), self._x_mean.copy(), self._x_std.copy()))
        return result
    monkeypatch.setattr(engine.PLSRegression, 'fit', tracking)
    result = engine.fit_fold(x, y, fit, target)
    assert result['predictions'].shape == (len(target), 15)
    assert len(fitted) == 15
    for indices, (values, outcomes, mean, scale) in zip(engine.candidate_subsets(), fitted):
        expected = x[fit][:, indices].astype(np.float32).astype(float)
        np.testing.assert_array_equal(values, expected)
        np.testing.assert_array_equal(outcomes, y[fit].astype(np.float32))
        np.testing.assert_allclose(mean, expected.mean(0), atol=1e-13, rtol=0)
        np.testing.assert_allclose(scale, expected.std(0, ddof=1), atol=1e-13, rtol=0)
    np.testing.assert_array_equal(result['fit_indices'], fit)
    np.testing.assert_array_equal(result['target_indices'], target)


def test_target_assay_changes_do_not_change_out_of_fold_predictions(arrays):
    x, _, y = arrays
    fit, target = np.arange(40), np.arange(40, 64)
    before = engine.fit_fold(x, y, fit, target)
    changed = y.copy()
    changed[target] += np.linspace(-1000, 1000, len(target))
    after = engine.fit_fold(x, changed, fit, target)
    np.testing.assert_array_equal(before['predictions'], after['predictions'])


@pytest.mark.parametrize('fit,target', [([0, 1, 2], [2, 3]), ([0, 0, 1], [3]),
                                        (list(range(10)), [64]), (list(range(10)), [10.5])])
def test_invalid_or_overlapping_fold_rows_are_rejected(arrays, fit, target):
    x, _, y = arrays
    with pytest.raises(ValueError):
        engine.fit_fold(x, y, np.asarray(fit), np.asarray(target))


def test_candidate_fit_is_independent_of_the_two_omitted_channels(arrays, final):
    x, full, y = arrays
    indices = final['candidate_indices']
    omitted = sorted(set(range(8)) - set(indices))
    changed = x.copy()
    changed[:, omitted] = 1000 * np.random.RandomState(4).normal(size=(len(x), 2))
    altered = engine.fit_final(changed, full, y, indices)
    np.testing.assert_array_equal(final['models']['candidate'].predict(x[:, indices]),
                                   altered['models']['candidate'].predict(x[:, indices]))
    assert final['portable']['models']['candidate'] == altered['portable']['models']['candidate']


def test_json_portable_models_match_fitted_models_and_batch_layouts(arrays, final):
    x, full, _ = arrays
    portable = json.loads(json.dumps(final['portable'], allow_nan=False))
    indices = final['candidate_indices']
    for kind, values in [('candidate', x[:, indices]), ('full_bank', x)]:
        expected = final['models'][kind].predict(values)
        for layout in [np.ascontiguousarray(values), np.asfortranarray(values)]:
            np.testing.assert_allclose(inference.predict_channels(portable, layout, kind),
                                       expected, atol=1e-10, rtol=0)
        np.testing.assert_allclose(inference.predict_channels(portable, values[0], kind),
                                   expected[:1], atol=1e-10, rtol=0)
    np.testing.assert_allclose(inference.predict_spectrum(portable, full),
                               final['models']['rich'].predict(full), atol=1e-10, rtol=0)


def test_final_models_reproduce_registered_inherited_pls_transforms(arrays, final):
    from mango.models import PLSReference
    x, full, y = arrays
    for kind, values, components in [('candidate', x[:, final['candidate_indices']], 6),
                                     ('full_bank', x, 6), ('rich', full, 12)]:
        reference = PLSReference(components, use_snv=kind == 'rich', derivative=kind == 'rich')
        reference.fit(values.astype(np.float32), y.astype(np.float32))
        np.testing.assert_allclose(final['models'][kind].predict(values),
                                   reference.predict(values.astype(np.float32)), atol=1e-10, rtol=0)


def test_final_candidate_rejects_nonregistered_or_misordered_indices(arrays):
    x, full, y = arrays
    for bad in [[0, 1, 2, 3, 4, 5], [7, 0, 1, 2, 3, 4], [0, 1, 1, 2, 3, 7], [0., 1., 2., 3., 4., 7.]]:
        with pytest.raises(ValueError):
            engine.fit_final(x, full, y, bad)


@pytest.mark.parametrize('width', [5, 7, 8])
def test_candidate_runtime_requires_exactly_six_readings(final, width):
    with pytest.raises(ValueError, match='exactly 6'):
        inference.predict_channels(final['portable'], np.ones(width))


def test_shape_nonfinite_and_invalid_portable_guards(arrays, final):
    x, _, y = arrays
    with pytest.raises(ValueError):
        engine.select_subset(np.zeros((4, 14)), np.zeros(4))
    with pytest.raises(ValueError):
        engine.select_subset(np.full((4, 15), np.nan), np.zeros(4))
    with pytest.raises(ValueError):
        engine.fit_fold(x, np.full_like(y, np.nan), np.arange(40), np.arange(40, 64))
    for bad in [np.full(6, np.nan), np.full(6, np.inf), np.full(6, 1e100), np.empty((0, 6))]:
        with pytest.raises(ValueError):
            inference.predict_channels(final['portable'], bad)
    with pytest.raises(ValueError):
        inference.predict_spectrum(final['portable'], np.ones(102))
    altered = copy.deepcopy(final['portable'])
    altered['models']['candidate']['x_std'][0] = 0
    with pytest.raises(ValueError):
        inference.predict_channels(altered, np.ones(6))


def test_optical_emulator_matches_independent_intensity_integration():
    rng = np.random.RandomState(16)
    weights = rng.uniform(size=(103, 8))
    weights /= weights.sum(0)
    spectra = rng.uniform(.2, 1.8, size=(15, 103))
    expected = -np.log10(np.power(10., -spectra) @ weights)
    np.testing.assert_allclose(inference.emulate_channels(spectra, weights), expected, atol=1e-14, rtol=0)
    np.testing.assert_allclose(inference.emulate_channels(np.full(103, 1000.), weights),
                               np.full(8, 1000.), atol=1e-12, rtol=0)
    for bad in [weights[:-1], weights * 2, -weights]:
        with pytest.raises(ValueError):
            inference.emulate_channels(spectra, bad)


def test_inference_is_array_only_without_training_data_or_assay_interface():
    for function in [inference.predict_channels, inference.predict_spectrum, inference.emulate_channels]:
        assert not {'y', 'assay', 'groups', 'season', 'metadata'}.intersection(inspect.signature(function).parameters)
    tree = ast.parse(Path(inference.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module.split('.')[0] in {'numpy', 'scipy'}
        elif isinstance(node, ast.Import):
            assert all(alias.name.split('.')[0] in {'numpy', 'scipy'} for alias in node.names)
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', None)
            assert name not in {'open', 'load', 'load_external', 'load_external_features', 'fit', 'fit_transform'}


def test_completed_checkpoint_reuses_bytes_and_cannot_repair_after_freeze(monkeypatch, tmp_path):
    from revisions.candidate_v4 import pipeline as p
    monkeypatch.setattr(p, 'OUT', tmp_path / 'results')
    monkeypatch.setattr(p, 'FROZEN', tmp_path / 'frozen')
    monkeypatch.setattr(p, 'event', lambda message: None)
    first = p.checkpoint('fixture', 'dependency', lambda: {'value': 42})
    paths = sorted((p.OUT / 'checkpoints').iterdir())
    before = {str(path): p.digest(path) for path in paths}
    def forbidden():
        raise AssertionError('Completed checkpoint refitted')
    assert p.checkpoint('fixture', 'dependency', forbidden) == first
    assert before == {str(path): p.digest(path) for path in paths}
    p.FROZEN.mkdir()
    (p.FROZEN / 'manifest.json').write_text('{}')
    (p.OUT / 'checkpoints/fixture.joblib').write_bytes(b'corrupted')
    with pytest.raises(RuntimeError, match='after candidate freeze'):
        p.checkpoint('fixture', 'dependency', forbidden)


def test_frozen_manifest_rejects_changed_extra_and_escaping_files(monkeypatch, tmp_path):
    from revisions.candidate_v4 import pipeline as p
    monkeypatch.setattr(p, 'FROZEN', tmp_path / 'frozen')
    p.FROZEN.mkdir()
    item = p.FROZEN / 'weights.json'
    item.write_text('registered content')
    manifest = {'status': 'frozen', 'files': {'weights.json': p.digest(item)}}
    p.atomic_json(p.FROZEN / 'manifest.json', manifest)
    assert p.check_frozen() == manifest
    item.write_text('changed content')
    with pytest.raises(ValueError, match='mismatch'):
        p.check_frozen()
    item.write_text('registered content')
    extra = p.FROZEN / 'unregistered.txt'
    extra.write_text('extra')
    with pytest.raises(ValueError, match='unregistered'):
        p.check_frozen()
    extra.unlink()
    outside = tmp_path / 'outside.json'
    outside.write_text('outside')
    p.atomic_json(p.FROZEN / 'manifest.json', {'status': 'frozen', 'files': {'../outside.json': p.digest(outside)}})
    with pytest.raises(ValueError, match='mismatch'):
        p.check_frozen()


def test_registered_fitting_dependency_cannot_silently_change(monkeypatch, tmp_path):
    from revisions.candidate_v4 import pipeline as p
    monkeypatch.setattr(p, 'HERE', tmp_path)
    monkeypatch.setattr(p, 'OUT', tmp_path / 'results')
    monkeypatch.setattr(p, 'snapshot_prior', lambda: None)
    (tmp_path / 'selection_spec.json').write_text('{}')
    dependencies = {'engine.py': 'original'}
    monkeypatch.setattr(p, 'dependencies', lambda: dict(dependencies))
    original = p.register()
    assert p.register() == original
    dependencies['engine.py'] = 'changed'
    with pytest.raises(RuntimeError, match='new revision'):
        p.register()
    assert json.loads((p.OUT / 'registration.json').read_text()) == original


def test_guard_excludes_prior_results_unregistered_data_and_prior_writes(monkeypatch, tmp_path):
    from revisions.candidate_v4 import pipeline as p
    root = tmp_path / 'project'
    here = root / 'revisions/candidate_v4'
    hooks = []
    monkeypatch.setattr(p, 'ROOT', root)
    monkeypatch.setattr(p, 'HERE', here)
    monkeypatch.setattr(p, 'GUARDED', False)
    monkeypatch.setattr(p, 'READ_PATHS', set())
    monkeypatch.setattr(p.sys, 'addaudithook', hooks.append)
    p.install_guard()
    assert len(hooks) == 1
    def opening(path, mode='rb', flags=os.O_RDONLY):
        hooks[0]('open', (str(root / path), mode, flags))
    for name in ['data/sealed/outcomes.csv', 'data/processed/metadata.csv',
                 'data/processed/external_features.csv', 'results/metrics.csv',
                 'revisions/methodology_v2/results/metrics.csv', 'revisions/fixed_design_v3/results/metrics.csv']:
        with pytest.raises(PermissionError):
            opening(name)
    for name in ['mango/models.py', 'data/processed/development.csv', 'revisions/fixed_design_v3/protocol.md']:
        with pytest.raises(PermissionError, match='read-only'):
            opening(name, 'wb', os.O_WRONLY | os.O_CREAT)
    opening('data/processed/development.csv')
    opening('data/catalog/catalog.json')
    opening('revisions/candidate_v4/results/new.json', 'wb', os.O_WRONLY | os.O_CREAT)
    assert p.READ_PATHS == {'data/processed/development.csv', 'data/catalog/catalog.json'}
