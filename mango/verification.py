"""Evidence-producing final verification; never refits research models."""
from __future__ import annotations

from contextlib import ExitStack
import gzip
import inspect
from itertools import combinations
import json
import re
import shlex
import subprocess
import time
import traceback
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from .state import ROOT, atomic_json, canonical_hash, digest, event


class PendingVerification(Exception):
    pass


def _read(relative):
    return json.loads((ROOT / relative).read_text())


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _hashes(paths):
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths) if p.is_file()}


def _protected_hashes():
    paths = list((ROOT / 'results/frozen').rglob('*'))
    paths += list((ROOT / 'results/checkpoints').glob('*.joblib'))
    paths += list((ROOT / 'results/checkpoints').glob('*.json'))
    return _hashes(paths)


def _report_hashes():
    paths = [ROOT / x for x in ['decision_report.md', 'results/manuscript_cells.json',
             'results/decision_summary.json', 'manuscript/main.pdf', 'manuscript/supplement.pdf',
             'manuscript/main.tex', 'manuscript/supplement.tex', 'manuscript/primary_table.tex',
             'manuscript/mechanism_table.tex', 'manuscript/controls_table.tex',
             'manuscript/uncertainty_table.tex', 'manuscript/references.bib']]
    from .reporting_diagnostics import ARTIFACTS
    paths += [ROOT / 'results' / name for name in ARTIFACTS]
    paths += list((ROOT / 'figures').glob('*.pdf')) + list((ROOT / 'figures').glob('*.png'))
    return _hashes(paths)


def _no_fit(*args, **kwargs):
    raise AssertionError('A verification/reporting/resume path attempted model fitting.')


def _report_without_fitting():
    from .reporting import generate_reports
    protected = _protected_hashes()
    key = canonical_hash({'reporting_source': digest(ROOT / 'mango/reporting.py'),
                          'diagnostic_reporting_source': digest(ROOT / 'mango/reporting_diagnostics.py'),
                          'external_completion': digest(ROOT / 'results/external_completion.json'),
                          'template': digest(ROOT / 'manuscript/main_template.tex'),
                          'references': digest(ROOT / 'manuscript/references.bib'),
                          'protected': protected,
                          'demo_trace': _read('results/demo_trace.json')['trace']})
    path = ROOT / 'results/reporting_only_verification.json'
    if path.exists():
        previous = json.loads(path.read_text())
        if (previous.get('status') == 'passed' and previous.get('dependency') == key
                and previous.get('report_artifacts') == _report_hashes()):
            return dict(previous, evidence_reused=True)
    started = time.time()
    with ExitStack() as stack:
        for target in ['mango.training.fit_bundle', 'mango.baselines.fit_static',
                       'mango.walsh_reference.fit_walsh', 'mango.workflow.fit_bundle']:
            stack.enter_context(patch(target, side_effect=_no_fit))
        generate_reports(force=True)
    after = _protected_hashes()
    _require(protected == after, 'Reporting changed frozen or model checkpoint files.')
    result = {'status': 'passed', 'dependency': key, 'evidence_reused': False,
              'invocation': 'mango.reporting.generate_reports() under four raising fit guards',
              'fit_entrypoints_guarded': ['training.fit_bundle', 'baselines.fit_static',
                                        'walsh_reference.fit_walsh', 'workflow.fit_bundle'],
              'protected_files_unchanged': len(protected), 'protected_hashes': after,
              'report_artifacts': _report_hashes(), 'elapsed_seconds': time.time() - started}
    atomic_json(path, result)
    return result


def _external_hashes():
    complete = _read('results/external_completion.json')
    _require(complete.get('status') == 'complete', 'External scoring is incomplete.')
    _require(complete['freeze_sha256'] == digest(ROOT / 'results/frozen/manifest.json'),
             'External results belong to a different freeze.')
    _require(bool(complete.get('outputs')), 'External completion has no output hashes.')
    for name, expected in complete['outputs'].items():
        _require((ROOT / name).is_file() and digest(ROOT / name) == expected,
                 'External output missing or changed: ' + name)
    _require(complete.get('no_training_or_selection_calls') is True, 'Missing evaluator isolation declaration.')
    return {'outputs_verified': len(complete['outputs']), 'freeze_sha256': complete['freeze_sha256'],
            'prediction_rows': complete['prediction_rows'], 'metric_rows': complete['metric_rows']}


def _partitions_and_oof():
    from .data import load_development
    data = load_development()
    assignments = _read('results/frozen/fold_assignments.json')
    _require(len(assignments) == 4, 'Expected three held seasons and one final partition.')
    by_fold = {}
    for assignment in assignments:
        fold = assignment['held_season']
        by_fold[fold] = assignment
        rows = [set(assignment[k]) for k in ['fit_row_ids', 'bank_design_row_ids',
                                           'calibration_row_ids', 'validation_row_ids']]
        groups = [set(assignment[k]) for k in ['fit_groups', 'bank_design_groups',
                                             'calibration_groups', 'validation_groups']]
        for left, right in combinations(range(4), 2):
            _require(not rows[left] & rows[right], 'Rows overlap across partitions.')
            _require(not groups[left] & groups[right], 'Harvest groups overlap across partitions.')
        _require(set.union(*rows) == set(data.row_ids), 'Development partition is incomplete.')
        if fold is not None:
            _require(rows[-1] == set(data.row_ids[data.seasons == fold]), 'Outer season partition differs.')
    audited, inner_folds = [], 0
    for path in sorted((ROOT / 'results/checkpoints').glob('model_*.joblib')):
        metadata = json.loads(path.with_suffix('.json').read_text())
        _require(metadata['status'] == 'complete' and metadata['sha256'] == digest(path),
                 'Unverified model checkpoint: ' + path.name)
        model = joblib.load(path)
        _require('oof' in model, 'Research checkpoint lacks OOF evidence: ' + path.name)
        oof = model['oof']
        match = re.search(r'season([123])_', path.name)
        fold = int(match.group(1)) if match else None
        assignment = by_fold[fold]
        actual_groups = set(map(str, oof['groups']))
        _require(actual_groups == set(assignment['fit_groups']), 'OOF groups differ from fitting assignment.')
        for f in oof['folds']:
            fit, held = set(f['fit_groups']), set(f['target_groups'])
            _require(not fit & held and fit | held == actual_groups, 'Inner target leakage/incomplete split.')
            inner_folds += 1
        for group in actual_groups:
            _require(len(np.unique(oof['fold_ids'][np.asarray(oof['groups']) == group])) == 1,
                     'One group has more than one OOF target fold.')
        np.testing.assert_array_equal(oof['partial_predictions'][:, -1], oof['bank_predictions'])
        _require(np.isfinite(oof['partial_predictions']).all(), 'Nonfinite cross-fitted predictions.')
        audited.append(path.name)
    _require(len(audited) >= 18, 'Fewer than six-bank by three-season model checkpoints were verified.')
    return {'partition_count': len(assignments), 'model_checkpoints': audited,
            'inner_folds_checked': inner_folds, 'oof_full_bank_endpoint_exact': True}


def _real_runtime_and_optics():
    from .app import load_runtime, ScannerSession, ReplaySource
    from .data import load_development
    from .models import observed_input, partial_predict, predict_bank, controller_outputs, gain_labels
    from .training import simulate, lookahead_action
    from .optics import get_catalog, channel_matrix, response_weights
    from .metrics import safe_rate, policy_metrics
    runtime = load_runtime()
    bundle = runtime['bundle']
    data = load_development()
    catalog = get_catalog()
    channels = channel_matrix(data.X[:12], data.wavelengths, catalog)[:, bundle['bank_indices']].astype(np.float32)
    fullmask = np.ones_like(channels, dtype=bool)
    with patch('mango.models.predict_bank', wraps=predict_bank) as dispatch:
        endpoint = partial_predict(bundle, channels, fullmask)
    _require(dispatch.call_count == 1, 'Full-mask prediction did not dispatch once to the bank reference.')
    dispatched_bundle, dispatched_channels = dispatch.call_args.args
    _require(dispatched_bundle is bundle, 'Full-mask prediction used another bank bundle.')
    np.testing.assert_array_equal(dispatched_channels, channels)
    np.testing.assert_array_equal(endpoint, predict_bank(bundle, dispatched_channels))
    direct_endpoint = predict_bank(bundle, channels)
    endpoint_max_error = float(np.max(np.abs(endpoint - direct_endpoint)))
    layout_max_error = float(np.max(np.abs(predict_bank(bundle, np.ascontiguousarray(channels)) -
                                          predict_bank(bundle, np.asfortranarray(channels)))))
    # Boolean row selection changes F- to C-contiguous storage. PLS floating-point
    # reductions may then differ in their last bits despite identical input values.
    endpoint_atol = 1e-12
    np.testing.assert_allclose(endpoint, direct_endpoint, atol=endpoint_atol, rtol=0)
    mask = np.zeros_like(channels, dtype=bool)
    mask[:, bundle['initial_indices']] = True
    changed = channels.copy(); changed[~mask] = np.nan
    np.testing.assert_array_equal(partial_predict(bundle, channels, mask), partial_predict(bundle, changed, mask))
    for objective in bundle['controllers']:
        a, b = controller_outputs(bundle, channels, mask, objective), controller_outputs(bundle, changed, mask, objective)
        for left, right in zip(a, b): np.testing.assert_array_equal(left, right)
    _require(lookahead_action(bundle, channels[0], mask[0]) == lookahead_action(bundle, changed[0], mask[0]),
             'Look-ahead consumed an unobserved value.')
    zero = np.zeros((1, len(bundle['bank_indices'])))
    unread = np.zeros_like(zero, dtype=bool); measured = unread.copy(); measured[0, 0] = True
    _require(not np.array_equal(observed_input(bundle['scaler'], zero, unread),
                               observed_input(bundle['scaler'], zero, measured)), 'Acquired zero equals unread.')
    for function in [partial_predict, controller_outputs, simulate, lookahead_action, ScannerSession.add_reading]:
        _require(not set(inspect.signature(function).parameters) &
                 {'y', 'assay', 'season', 'metadata', 'reference_predictions'}, 'Runtime exposes forbidden inputs.')
    _require('oof' not in bundle and 'assay' not in runtime['example'], 'Runtime fixture carries research targets.')
    for method in ['proposed', 'single', 'uncertainty', 'fixed_order', 'random_order',
                   'fixed_length', 'lookahead', 'full_bank', 'single_cnn_reference']:
        run = simulate(bundle, channels[:2], method, threshold=-1e30)
        for trace in run['traces']:
            requested = [s['next_channel'] for s in trace if s['next_channel'] is not None]
            _require(len(requested) == len(set(requested)), 'Repeated pulse in ' + method)
            _require(trace[-1]['stop'] and trace[-1]['pulses'] == len(bundle['bank_indices']),
                     'Forced full-bank trajectory failed to terminate.')
    result = gain_labels(np.array([10.]), np.array([13.]), np.array([11.]),
                         np.array([10.5]), np.array([[12., 14.]]))
    for name, expected in [('g_stop', [2.]), ('g_bank', [.5]), ('g_actions', [[1., -1.]])]:
        np.testing.assert_array_equal(result[name], expected)
    _require(safe_rate(0, 0) is None, 'Zero denominator must return None.')
    rates = policy_metrics(np.array([10.]), np.array([10.]), np.array([8]),
                           np.array([10.]), np.array([10.]), 8)
    _require(rates['missed_rate'] is None and rates['early_n'] == 0, 'No-early-stop rate semantics differ.')
    np.testing.assert_allclose(channel_matrix(np.full((2, 103), 1.23456), data.wavelengths, catalog),
                               1.23456, atol=1e-12, rtol=0)
    bad = {'id': 'unsupported_software_fixture', 'center_nm': 980., 'fwhm_nm': 55.,
           'profile_type': 'gaussian_approximation'}
    try:
        response_weights(data.wavelengths, [bad])
    except ValueError:
        pass
    else:
        raise AssertionError('Unsupported emitter accepted.')
    return {'real_development_rows': 12, 'all_bank_endpoint_same_frozen_reference': True,
            'all_bank_endpoint_dispatched_result_exact': True,
            'all_bank_endpoint_within_tolerance': True,
            'all_bank_endpoint_max_abs_difference_pp': endpoint_max_error,
            'all_bank_endpoint_absolute_tolerance_pp': endpoint_atol,
            'all_bank_endpoint_relative_tolerance': 0,
            'c_vs_f_contiguous_bank_prediction_max_abs_difference_pp': layout_max_error,
            'original_input_contiguity': {'C': bool(channels.flags.c_contiguous),
                                           'F': bool(channels.flags.f_contiguous)},
            'dispatched_input_contiguity': {'C': bool(dispatched_channels.flags.c_contiguous),
                                             'F': bool(dispatched_channels.flags.f_contiguous)},
            'unseen_nan_invariance': True, 'observed_zero_distinct': True,
            'runtime_no_assay_or_metadata_arguments': True, 'termination_methods': 9,
            'gain_signs_exact': True, 'unsupported_emitter_rejected': True,
            'constant_spectrum_preserved': True, 'zero_denominator_is_none': True}


def _reference_training_boundaries():
    assignments = {r['held_season']: r for r in _read('results/frozen/fold_assignments.json')}
    records = []
    for fold in [1, 2, 3, None]:
        label = 'final' if fold is None else 'season%d' % fold
        expected = set(assignments[fold]['fit_groups'])
        walsh_path = ROOT / 'results/checkpoints' / ('walsh_' + label + '_seed42.joblib')
        model = joblib.load(walsh_path)
        info = model.fit_info
        fit, stop = set(info['fit_groups']), set(info['early_stop_groups'])
        _require(not fit & stop and fit | stop == expected, 'Walsh stopping groups overlap or differ from outer fitting groups.')
        _require(info['max_epochs'] == 750 and 1 <= info['best_epoch'] <= info['epochs'] <= 750,
                 'Walsh reference is a smoke/truncated or invalid fit.')
        static_path = ROOT / 'results/checkpoints' / ('static_' + label + '.joblib')
        static = joblib.load(static_path)
        checked = set()
        for item in static.values():
            if item['family'] in checked: continue
            checked.add(item['family'])
            diagnostic = item['selection_diagnostics']
            for inner in diagnostic['folds']:
                a, b = set(inner['fit_groups']), set(inner['validation_groups'])
                _require(not a & b and a | b == expected, 'Static inner selection groups differ.')
            tolerance = diagnostic['optimality_assessment_tolerance']
            _require(np.max(diagnostic['cv_kkt_violation']) <= tolerance and
                     diagnostic['refit_kkt_violation'] <= tolerance, 'Sparse solver optimality diagnostic failed.')
            _require(np.sum(diagnostic['cv_warning_counts']) == 0 and diagnostic['refit_warning_count'] == 0,
                     'Sparse selection retains unresolved solver warnings.')
        _require(checked == {'physical', 'ideal'}, 'Static physical or ideal family missing.')
        records.append({'held_season': fold, 'walsh_epochs': info['epochs'], 'walsh_best_epoch': info['best_epoch'],
                        'walsh_fit_groups': len(fit), 'walsh_stopping_groups': len(stop),
                        'static_families_verified': sorted(checked)})
    return {'folds': records, 'walsh_and_static_boundaries_verified': True,
            'sparse_solver_warning_and_optimality_checks_passed': True}


def _computed_metrics(frame):
    y, p = frame.y.to_numpy(float), frame.prediction.to_numpy(float)
    residual = p - y
    e, eb, ef = np.abs(residual), np.abs(y - frame.bank_prediction), np.abs(y - frame.rich_prediction)
    early = frame.pulses.to_numpy() < 8
    missed = early & ((e - eb) > .5)
    denom = np.sum((y - y.mean()) ** 2)
    return {'n': len(y), 'rmsep': float(np.sqrt(np.mean(residual ** 2))),
            'mae': float(e.mean()), 'bias': float(residual.mean()),
            'r2': float(1 - np.sum(residual ** 2) / denom) if denom else None,
            'mean_pulses': float(frame.pulses.mean()), 'median_pulses': float(frame.pulses.median()),
            'p95_pulses': float(np.percentile(frame.pulses, 95)), 'early_n': int(early.sum()),
            'early_fraction': float(early.mean()), 'missed_n': int(missed.sum()),
            'missed_rate': float(missed.sum() / early.sum()) if early.sum() else None,
            'missed_unconditional': float(missed.mean()), 'bank_loss_n': int(((eb - ef) > .5).sum()),
            'bank_loss_rate': float(np.mean((eb - ef) > .5)),
            'bank_rmsep': float(np.sqrt(np.mean(eb ** 2))),
            'rich_rmsep': float(np.sqrt(np.mean(ef ** 2)))}


def _recompute_cells(predictions):
    cells = _read('results/manuscript_cells.json')
    _require(len(cells) > 0, 'No manuscript numerical cells supplied.')
    identifiers = {'season', 'rule', 'seed', 'method', 'operating_point', 'scenario'}
    comparisons, maximum_error = [], 0.
    for cell in cells:
        selected = np.ones(len(predictions), dtype=bool)
        static_method = cell['method'] == 'walsh_adapted' or cell['method'].startswith(('physical_', 'ideal_'))
        scenario = cell.get('scenario', 'static' if static_method else 'nominal')
        for key in identifiers:
            value = scenario if key == 'scenario' else cell.get(key)
            if value is not None: selected &= predictions[key].to_numpy() == value
        part = predictions.loc[selected]
        _require(len(part) > 0, 'No predictions match manuscript cell ' + str(cell))
        actual = _computed_metrics(part)
        for metric, expected in cell.items():
            if metric in identifiers: continue
            _require(metric in actual, 'Verifier lacks an independent formula for cell ' + metric)
            found = actual[metric]
            if expected is None:
                _require(found is None, 'Undefined manuscript cell differs.')
                error = 0.
            else:
                _require(found is not None, 'Finite manuscript cell has zero denominator.')
                error = abs(float(found) - float(expected))
                _require(error <= 1e-9, 'Manuscript cell mismatch: ' + str(cell) + '; recomputed=' + str(found))
            maximum_error = max(maximum_error, error)
            comparisons.append({'season': cell['season'], 'method': cell['method'], 'metric': metric,
                                'saved': expected, 'recomputed': found, 'absolute_error': error})
    return {'cell_rows': len(cells), 'numeric_cells': len(comparisons), 'tolerance': 1e-9,
            'maximum_absolute_error': maximum_error, 'comparisons': comparisons}


def _prediction_completeness(predictions):
    from .data import load_external_features
    keys = ['season', 'rule', 'seed', 'scenario', 'method', 'operating_point', 'row_id']
    _require(not predictions.duplicated(keys).any(), 'Duplicate selected-prediction rows.')
    _require(set(predictions.season) == {4, 5}, 'Wrong scored external seasons.')
    _require(np.isfinite(predictions[['y', 'prediction', 'pulses', 'bank_prediction', 'rich_prediction', 'cnn_prediction']]).all().all(),
             'Nonfinite scored predictions.')
    membership = {}
    for season in [4, 5]:
        feature_data = load_external_features(season)
        _require(feature_data.y is None, 'Feature-only membership reader exposed targets.')
        membership[season] = dict(zip(feature_data.row_ids, feature_data.groups))
    grouped = predictions.groupby(keys[:-1], sort=False)
    groups = set()
    for key, frame in grouped:
        _require(len(frame) == {4: 1448, 5: 320}[int(key[0])], 'Incomplete scored scenario: ' + str(key))
        _require(dict(zip(frame.row_id, frame.group)) == membership[int(key[0])],
                 'Scored row identities or harvest-group assignments differ from source features.')
        groups.add(key)
    selection = _read('results/frozen/selection.json')
    roles = {selection[k] for k in ['primary_rule', 'accuracy_rule', 'adaptive_error_rule',
                                     'mean_season_rule', 'independent_rule']}
    primary = selection['primary_rule']
    def expect(season, rule, seed, scenario, method, point):
        _require((season, rule, seed, scenario, method, point) in groups,
                 'Missing required scientific comparison: ' + str((season, rule, seed, scenario, method, point)))
    for season in [4, 5]:
        for rule in roles:
            for method in ['proposed', 'single']: expect(season, rule, 42, 'nominal', method, 'scientific')
            for method in ['full_bank', 'rich_pls', 'rich_cnn']: expect(season, rule, 42, 'nominal', method, 'reference')
        for rule in {primary, selection['independent_rule']}:
            for seed in [7, 99]:
                for method in ['proposed', 'single']: expect(season, rule, seed, 'nominal', method, 'scientific')
        for method in ['single_cnn_reference', 'uncertainty', 'fixed_order', 'random_order', 'fixed_length', 'lookahead']:
            expect(season, primary, 42, 'nominal', method, 'scientific')
        expect(season, primary, 42, 'nominal', 'proposed', 'engineering')
        for family, budgets in [('physical', [4, 8]), ('ideal', [4, 8, 16])]:
            for model in ['plsr', 'sparse_svr', 'mlp']:
                for budget in budgets: expect(season, primary, 42, 'static', '%s_%s_%d' % (family, model, budget), 'reference')
        expect(season, primary, 42, 'static', 'walsh_adapted', 'reference')
        for method in ['proposed', 'single']: expect(season, primary, 42, 'ideal_points', method, 'ideal_scientific')
        exclusions = _read('results/external_sensitivity_exclusions.json')
        for variant in ['center_minus3', 'center_plus3', 'width_times0p9', 'width_times1p1', 'gaussian_approximation']:
            omitted = any(r['season'] == season and r['scenario'] == variant and r['status'] == 'support_excluded'
                          for r in exclusions)
            if not omitted:
                for method in ['proposed', 'single']: expect(season, primary, 42, variant, method, 'response_shift')
    development = pd.read_csv(ROOT / 'results/development_scores.csv')
    for fold in [1, 2, 3]:
        for rule in ['uniform', 'swap_low', 'swap_mid', 'swap_high', 'correlation', 'ridge']:
            for method in ['proposed', 'single']:
                d = development[(development.fold == fold) & (development.rule == rule) &
                                (development.method == method) & (development.seed == 42)]
                _require(len(d) == 21 and d.threshold_index.nunique() == 21, 'Incomplete six-bank development search.')
    curves = pd.read_csv(ROOT / 'results/frozen_curves.csv')
    curve_keys = ['season', 'rule', 'seed', 'scenario', 'method', 'threshold_index']
    _require(not curves.duplicated(curve_keys).any(), 'Duplicate frozen curve rows.')
    for key, curve in curves.groupby(curve_keys[:-1], sort=False):
        size = 7 if key[-1] == 'fixed_length' else 21
        _require(len(curve) == size and set(curve.threshold_index) == set(range(size)),
                 'Incomplete frozen threshold grid: ' + str(key))
    return {'prediction_rows': len(predictions), 'unique_scored_comparisons': len(groups),
            'duplicate_rows': 0, 'all_required_comparisons_present': True,
            'six_bank_three_season_development_search_complete': True,
            'frozen_curve_rows': len(curves), 'all_frozen_threshold_grids_complete': True}


def _uncertainty_and_calibration():
    uncertainties = _read('results/external_uncertainty.json')
    _require(bool(uncertainties), 'No paired uncertainty output.')
    selection = _read('results/frozen/selection.json')
    roles = {selection[k] for k in ['primary_rule', 'accuracy_rule', 'adaptive_error_rule',
                                     'mean_season_rule', 'independent_rule']}
    expected_keys = {'%d|%s|42' % (season, rule) for season in [4, 5] for rule in roles}
    expected_keys |= {'%d|%s|%d' % (season, rule, seed) for season in [4, 5]
                     for rule in {selection['primary_rule'], selection['independent_rule']} for seed in [7, 99]}
    _require(set(uncertainties) == expected_keys, 'Paired uncertainty comparisons are missing or unexpected.')
    for key, record in uncertainties.items():
        season = int(key.split('|')[0])
        _require(record['n_groups'] == {4: 18, 5: 2}[season], 'Wrong uncertainty group denominator.')
        if season == 5:
            _require(record['intervals'] is None and len(record['group_estimates']) == 2,
                     'Two-population uncertainty must suppress population intervals.')
        else:
            _require(len(record['intervals']) == 4 and record['n_boot'] == 1000, 'Missing registered bootstrap.')
        _require(record['achieved_budget_comparable'] == (abs(record['point'][1]) <= .25),
                 'Achieved-budget interpretation differs from registered margin.')
    calibration = _read('results/calibration.json')
    for record in calibration.values():
        _require(sum(b['n'] for b in record['bins']) == record['n_states'], 'Calibration bin count differs.')
        _require(record['brier'] is None or 0 <= record['brier'] <= 1, 'Invalid Brier score.')
    return {'paired_comparisons': len(uncertainties), 'season5_population_intervals_suppressed': True,
            'calibration_records': len(calibration)}


def _traces():
    count = 0
    catalog = _read('results/frozen/catalog.json')
    bank_maps = {}
    with gzip.open(ROOT / 'results/external_traces.jsonl.gz', 'rt') as stream:
        for line in stream:
            item = json.loads(line); previous = None; previous_state = None; requested = []
            key = (item['rule'], int(item['seed']))
            if key not in bank_maps:
                bundle = joblib.load(ROOT / 'results/frozen' / ('%s_seed%d.joblib' % key))
                bank_maps[key] = ([catalog[j]['id'] for j in bundle['bank_indices']], bundle['initial_indices'])
            identifiers, initial = bank_maps[key]
            for state in item['trace']:
                mask = np.asarray(state['mask'], dtype=bool)
                _require(int(mask.sum()) == state['pulses'] == len(state['readings']), 'Trace observation count differs.')
                _require(set(state['readings']) == {identifiers[j] for j in np.flatnonzero(mask)},
                         'Trace exposes readings that do not match its observation mask.')
                _require(all(np.isfinite(v) for v in state['readings'].values()), 'Trace has a nonfinite acquired reading.')
                _require(not {'assay', 'y', 'bank_prediction', 'rich_prediction', 'season', 'group'} & set(state),
                         'Evaluator-only information entered decision state.')
                if previous is None:
                    _require(state['pulses'] == 2 and set(np.flatnonzero(mask)) == set(initial),
                             'Initial bank readings differ or were not both charged.')
                else:
                    _require(np.all(mask[previous]) and np.sum(mask & ~previous) == 1, 'Trace did not add exactly one LED.')
                    added = int(np.flatnonzero(mask & ~previous)[0])
                    _require(previous_state['next_led'] == identifiers[added], 'Requested LED differs from newly revealed LED.')
                if state['next_led'] is not None:
                    _require(state['next_led'] in {identifiers[j] for j in np.flatnonzero(~mask)},
                             'Trace requested an observed or uninstalled LED.')
                    requested.append(state['next_led'])
                previous = mask
                previous_state = state
            final = item['trace'][-1]
            _require(final['stop'] and final['next_led'] is None and final['pulses'] <= 8 and len(requested) == len(set(requested)),
                     'Trace repetition or nontermination.')
            if final['pulses'] == 8:
                _require(abs(final['prediction'] - item['evaluator_only']['bank_prediction']) < 1e-10,
                         'Full-bank trace endpoint differs from its reference.')
            count += 1
    _require(count > 0, 'No decision traces.')
    return {'trace_rows_checked': count, 'only_acquired_readings_in_states': True,
            'assays_and_reference_outcomes_remain_evaluator_only': True}


def _resume():
    from .external import score_external
    before = _read('results/external_completion.json')
    with ExitStack() as stack:
        for target in ['mango.external.load_external', 'mango.external.load_external_features',
                       'mango.training.fit_bundle', 'mango.baselines.fit_static', 'mango.walsh_reference.fit_walsh']:
            stack.enter_context(patch(target, side_effect=_no_fit))
        returned = score_external()
    _require(returned == before == _read('results/external_completion.json'), 'Completed scorer resume changed results.')
    _external_hashes()
    interrupted = _read('results/resume_verification.json')
    fixture = _read('results/data_audit/external_fixture_verification.json')
    _require(interrupted.get('status') == 'passed' and interrupted.get('identical') is True,
             'Interrupted training resume evidence did not pass.')
    _require(interrupted.get('completed_checkpoints_reused', 0) > 0, 'No completed checkpoint reuse demonstrated.')
    _require(fixture.get('status') == 'passed' and any('incomplete export recovery' in s for s in fixture['checks']),
             'No interrupted-export recovery evidence.')
    return {'current_frozen_scorer_resume': 'passed with data readers and fit functions disabled',
            'interruption_evidence': interrupted, 'export_recovery_evidence': fixture,
            'scope': 'Training interruption evidence belongs to the archived preliminary run; current completed frozen scoring also resumes without reading outcomes, fitting, or modifying outputs.'}


def verify():
    """Verify completed artifacts, write reports, and raise on any required failure."""
    started = time.time()
    records, commands = [], []
    logs = ROOT / 'results/verification_logs'; logs.mkdir(parents=True, exist_ok=True)
    def check(name, function):
        before = time.time()
        try:
            details = function()
            row = {'name': name, 'status': 'passed', 'details': details}
        except PendingVerification as exc:
            row = {'name': name, 'status': 'pending', 'reason': str(exc)}
        except Exception as exc:
            row = {'name': name, 'status': 'failed', 'error': repr(exc), 'traceback': traceback.format_exc()}
        row['elapsed_seconds'] = time.time() - before
        records.append(row)
        event('Verification ' + row['status'] + ': ' + name)
        return row['status'] == 'passed'
    def command(args, label, timeout=300):
        call = shlex.join(map(str, args))
        path = logs / (label + '.log')
        record = {'command': call, 'returncode': None, 'log': str(path.relative_to(ROOT))}
        commands.append(record)
        try:
            result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ''
            if isinstance(output, bytes): output = output.decode(errors='replace')
            path.write_text(output + '\nTimed out after %d seconds.\n' % timeout)
            record['error'] = 'timeout after %d seconds' % timeout
            raise
        path.write_text(result.stdout)
        record['returncode'] = result.returncode
        _require(result.returncode == 0, 'Command failed: ' + call + '; see ' + str(path.relative_to(ROOT)))
        return result.stdout
    from .external import verify_lock
    locked = check('frozen_manifest_and_nested_hashes', lambda: {'manifest': verify_lock(), 'sealed_labels_loaded': False})
    scored = check('completed_external_output_hashes', _external_hashes) if locked else False
    if locked and scored:
        check('reporting_only_guarded_rerun', _report_without_fitting)
        check('real_data_reader_and_source_contracts', lambda: {'stdout': command(
            [str(ROOT / '.venv/bin/python'), '-m', 'results.data_audit.verify_data'], 'data_audit'),
            'scope': 'Development and target-free external features only; no external labels opened.'})
        check('software_contract_tests', lambda: {'stdout': command(
            [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', 'tests'], 'pytest'),
            'scope': 'Synthetic fixtures train tiny test networks; no research model or external assay is fitted.'})
        check('registered_partitions_and_all_oof_checkpoints', _partitions_and_oof)
        check('walsh_and_static_reference_training_boundaries', _reference_training_boundaries)
        check('real_development_runtime_and_optical_contracts', _real_runtime_and_optics)
        check('normal_cli_replay_entrypoint', lambda: {'stdout': command(
            ['python3', 'run_project.py', 'replay', '--example', '--trace-output', 'results/verification_cli_trace.json'], 'cli_replay')})
        check('normal_app_entrypoint', lambda: {'stdout': command(
            ['python3', 'run_project.py', 'app', '--self-test'], 'app_self_test')})
        def app_evidence():
            app = _read('results/app_test.json')
            _require(app['status'] == 'passed' and all(app['checks'].values()), 'App interaction checks failed.')
            _require(app['model_manifest_sha256'] == digest(ROOT / 'results/frozen/manifest.json'), 'App used another model.')
            cli = _read('results/verification_cli_trace.json')
            demo = _read('results/demo_trace.json')
            _require(cli['trace'] == demo['trace'], 'Normal CLI differs from the documented demo trace.')
            return app
        check('app_cli_manual_trace_equivalence', app_evidence)
        predictions = None
        def load_predictions():
            nonlocal predictions
            predictions = pd.read_csv(ROOT / 'results/external_predictions.csv', float_precision='round_trip')
            return {'rows': len(predictions), 'source': 'Previously scored saved table; sealed outcomes not reopened.'}
        if check('saved_prediction_table_loaded', load_predictions):
            check('comparison_completeness_and_duplicate_exclusion', lambda: _prediction_completeness(predictions))
            check('every_manuscript_cell_recomputed', lambda: _recompute_cells(predictions))
        check('uncertainty_and_calibration_denominators', _uncertainty_and_calibration)
        check('all_saved_trace_information_boundaries', _traces)
        check('interruption_and_current_frozen_resume', _resume)
        required = ['README.md', 'RUN_STATUS.md', 'requirements.txt', 'decision_report.md',
                    'docs/protocol.md', 'docs/optics_audit.md', 'docs/literature_audit.md',
                    'docs/model_methods.md', 'docs/app_usage.md', 'docs/walsh_reference.md',
                    'results/run_ledger.jsonl', 'results/environment.json', 'results/development_scores.csv',
                    'results/development_frontier.csv', 'results/static_development.csv', 'results/walsh_development.csv',
                    'results/decision_summary.json', 'results/pdf_compilation.json',
                    'manuscript/main.pdf', 'manuscript/supplement.pdf', 'manuscript/references.bib']
        def required_files():
            for name in required:
                _require((ROOT / name).is_file() and (ROOT / name).stat().st_size > 0, 'Required output missing: ' + name)
            for name in ['study_design', 'led_profiles', 'error_pulses', 'missed_and_bank_losses',
                         'calibration', 'example_trace', 'signed_gains']:
                for suffix in ['pdf', 'png']:
                    _require((ROOT / 'figures' / (name + '.' + suffix)).is_file(), 'Required figure missing: ' + name)
            from .reporting_diagnostics import ARTIFACTS
            for name in ARTIFACTS:
                _require((ROOT / 'results' / name).is_file(), 'Reporting diagnostic missing: ' + name)
            return {'required_outputs_present': len(required), 'required_figures': 14,
                    'reporting_diagnostics_present': len(ARTIFACTS)}
        check('required_deliverables', required_files)
        pdf_details = {}
        def pdf_checks():
            compile_record = _read('results/pdf_compilation.json')
            _require(compile_record['status'] == 'passed' and all(r['returncode'] == 0 for r in compile_record['commands']),
                     'Recorded PDF compilation failed.')
            for name in ['main', 'supplement']:
                relative = 'manuscript/' + name + '.pdf'
                info = command(['pdfinfo', relative], name + '_pdfinfo')
                count = re.search(r'^Pages:\s+(\d+)', info, flags=re.MULTILINE)
                _require(count is not None and int(count.group(1)) > 0, 'PDF has no pages.')
                text = command(['pdftotext', '-layout', relative, '-'], name + '_pdftotext')
                _require(len(text.strip()) > 500, 'PDF text appears missing/truncated.')
                for content in [text, (ROOT / 'manuscript' / (name + '.tex')).read_text()]:
                    _require(re.search(r'@@[A-Z_]+@@|\bTODO\b|\bTBD\b|\bFIXME\b|lorem ipsum|\?\?',
                                       content, flags=re.IGNORECASE) is None, 'Unresolved manuscript placeholder or reference.')
                pdf_details[relative] = {'pages': int(count.group(1)), 'sha256': digest(ROOT / relative),
                                         'text_characters': len(text)}
            return {'pdfs': pdf_details, 'declared_author_fields':
                    'Names, affiliations, contributions, funding, conflicts and institution-specific wording explicitly require author input; retained as declarations, not fabricated.'}
        check('pdf_structure_text_and_placeholder_checks', pdf_checks)
        def visual_qa():
            path = ROOT / 'results/pdf_visual_qa.json'
            if not path.exists():
                raise PendingVerification('Rendered page inspection is pending; no visual-completion claim is made.')
            qa = json.loads(path.read_text())
            _require(qa.get('status') in ['passed', 'complete'], 'PDF visual QA did not pass.')
            hashes = qa.get('hashes', qa.get('pdfs', {}))
            for relative, info in pdf_details.items():
                value = hashes.get(relative)
                if isinstance(value, dict): value = value.get('sha256')
                if value != info['sha256']:
                    raise PendingVerification('Visual QA is stale or lacks the current PDF hash: ' + relative)
            _require(len(pdf_details) == 2, 'PDF structure must pass before visual QA can be accepted.')
            return qa
        check('rendered_pdf_visual_qa', visual_qa)
        check('final_frozen_and_external_hash_recheck', lambda: (verify_lock(), _external_hashes()) and
              {'frozen_and_scored_artifacts_unchanged': True})
    failures = [r['name'] for r in records if r['status'] == 'failed']
    pending = [r['name'] for r in records if r['status'] == 'pending']
    status = 'failed' if failures else 'partial' if pending else 'passed'
    scope = 'blocked' if not locked or not scored else 'partial' if failures or pending else 'completed'
    result = {'status': status, 'computational_scope_status': scope, 'checks': records, 'commands': commands,
              'failures': failures, 'pending': pending, 'elapsed_seconds': time.time() - started,
              'invocation': 'python3 run_project.py verify (also called by all --resume after scoring/reporting)',
              'external_outcomes_reopened_by_verifier': False,
              'scientific_limitations': ['No physical acquisition, noise, energy, timing or repeatability measurements.',
                  'Six journal full-method sources remain unavailable; source audit records verified scope.',
                  'Instrument logarithm base is conventional base 10, not explicitly firmware-verified.',
                  'Fruit identities are unavailable; harvest groups constrain but cannot prove identity isolation.',
                  'External seasons were used in earlier local work and are reused benchmarks.',
                  'Author declarations remain pending; no release, submission, purchase or patent filing occurred.']}
    app_visual_path = ROOT / 'results/app_visual_qa.json'
    if app_visual_path.is_file():
        result['app_visual_qa'] = json.loads(app_visual_path.read_text())
        if result['app_visual_qa'].get('status') == 'unavailable':
            result['scientific_limitations'].append(
                'Live app screenshot inspection was attempted but the CUA browser access host was unavailable '
                '(results/app_visual_qa.json). Normal app HTTP, manual-entry and trace-export checks are recorded '
                'separately in results/app_test.json; optional screenshot unavailability is not a failed '
                'computational check.')
    atomic_json(ROOT / 'results/verification.json', result)
    lines = ['# Final verification report', '', '**Verification: ' + status + '. Computational scope: ' + scope + '.**',
             '', 'The verifier does not refit research models or reopen sealed external assays. It recomputes claims from the already-scored prediction table. Tiny synthetic networks inside the contract-test suite are software fixtures only.',
             '', '| Check | Status | Evidence |', '|---|---|---|']
    for row in records:
        note = row.get('reason', row.get('error', 'Recorded in results/verification.json'))
        lines.append('| ' + row['name'] + ' | ' + row['status'] + ' | ' + str(note).replace('|', '/') + ' |')
    lines += ['', '## Executed commands', '', '| Invocation | Return code | Captured output |', '|---|---:|---|']
    for item in commands:
        lines.append('| `' + item['command'] + '` | ' + str(item['returncode']) + ' | `' + item['log'] + '` |')
    lines += ['', 'Python checks also inspect every saved OOF model checkpoint, execute real development invariance checks, replay every saved external trace, rerun the frozen scorer with data readers disabled, and guard reporting against fitting. Reporting-only evidence is reused only when its exact dependencies and generated artifact hashes still match.',
              '', '## Scope and unresolved evidence', '']
    lines += ['- ' + item for item in result['scientific_limitations']]
    lines += ['', 'Computational completion does not mean an engineering criterion passed or that the proposed objective improved prediction. Scientific outcomes and budget comparability are reported in `decision_report.md`. Missing physical measurements and inaccessible full texts are evidence limits, not completed experimental stages.',
              '', 'The interrupted-training resume evidence is explicitly from the preserved preliminary run before bank-design isolation. Separate development-fixture interruption recovery and current frozen-scorer resume evidence are checked. No interrupted job is relabeled complete merely because newer results exist.',
              '', 'Machine-readable evidence: `results/verification.json`; all command outputs: `results/verification_logs/`.']
    (ROOT / 'verification_report.md').write_text('\n'.join(lines) + '\n')
    event('Final verification ' + status + '; computational scope ' + scope + '.')
    if failures:
        raise RuntimeError('Required verification checks failed: ' + ', '.join(failures))
    return result
