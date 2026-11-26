"""Independent numerical/provenance audit of a frozen research candidate.

No external data are parsed. Three registered LOPO fits are reconstructed only
as audit calculations; they cannot alter selection, checkpoints or the bundle.
Development prediction replay establishes software parity, not test accuracy.
"""
import csv
import json
import os
from itertools import combinations
from pathlib import Path
import subprocess
import sys
import time

import joblib
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
ROOT = HERE.parents[1]
CHECKS = []
COMMANDS = []


def check(name, condition, detail=None):
    record = {'name': name, 'passed': bool(condition)}
    if detail is not None:
        record['detail'] = detail
    CHECKS.append(record)
    return bool(condition)


def close(name, actual, expected, atol=1e-10):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    finite = np.isfinite(a).all() and np.isfinite(b).all()
    same = a.shape == b.shape
    error = float(np.max(np.abs(a - b))) if same and finite and a.size else None
    return check(name, same and finite and np.allclose(a, b, atol=atol, rtol=0),
                 {'shape_actual': list(a.shape), 'shape_expected': list(b.shape),
                  'max_absolute_error': error, 'absolute_tolerance': atol})


def command(args, name):
    path = OUT / 'verification_logs' / (name + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(args, cwd=str(ROOT), text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    path.write_text(run.stdout)
    COMMANDS.append({'argv': args, 'returncode': run.returncode, 'output': str(path.relative_to(HERE))})
    check('command/' + name, run.returncode == 0, run.stdout[-1500:] if run.returncode else None)
    return run


def checkpoint(p, name, dependency):
    path = OUT / 'checkpoints' / (name + '.joblib')
    metadata = json.loads(path.with_suffix('.json').read_text())
    valid = (metadata.get('status') == 'complete' and metadata.get('dependency') == dependency
             and metadata.get('sha256') == p.digest(path))
    check('checkpoint/' + name, valid)
    if not valid:
        raise AssertionError('Unverified checkpoint: ' + name)
    return joblib.load(path)


def selection_audit(p, data, registration):
    dependency = registration['dependency']
    selected = checkpoint(p, 'selection', p.canonical_hash([dependency, 'selection']))
    n = len(data['y'])
    candidates = [(0,) + middle + (7,) for middle in combinations(range(1, 7), 4)]
    check('selection/exact15_subsets', [tuple(s) for s in selected['subsets']] == candidates)
    for key in ('row_ids', 'groups', 'seasons', 'y'):
        check('selection/source_' + key, np.array_equal(selected[key], data[key]))
    predictions = np.asarray(selected['predictions'])
    check('selection/prediction_shape_finite', predictions.shape == (n, 15) and np.isfinite(predictions).all())
    unique = np.unique(data['groups'])
    coverage = np.zeros(n, dtype=int)
    warning_count = 0
    for fold, group in enumerate(unique):
        train = np.flatnonzero(data['groups'] != group)
        target = np.flatnonzero(data['groups'] == group)
        value = checkpoint(p, 'cv_%03d' % fold, p.canonical_hash([dependency, 'lopo', fold, str(group)]))
        prefix = 'lopo/%03d' % fold
        check(prefix + '/row_partition', np.array_equal(value['fit_indices'], train)
              and np.array_equal(value['target_indices'], target))
        check(prefix + '/population_isolation', set(value['fit_groups']) == set(data['groups'][train])
              and value['target_groups'] == [str(group)] and not set(value['fit_groups']) & set(value['target_groups']))
        check(prefix + '/row_identity', np.array_equal(value['fit_row_ids'], data['row_ids'][train])
              and np.array_equal(value['target_row_ids'], data['row_ids'][target]))
        check(prefix + '/fold_assignment', np.all(selected['fold_ids'][target] == fold))
        close(prefix + '/prediction_assignment', value['predictions'], predictions[target], atol=0)
        check(prefix + '/warnings_retained', len(value['warnings']) == 15 and all(
            row['subset_index'] == j and tuple(row['indices']) == candidates[j] for j, row in enumerate(value['warnings'])))
        warning_count += sum(len(row['warnings']) for row in value['warnings'])
        coverage[target] += 1
    close('lopo/exactly_once', coverage, np.ones(n), atol=0)
    check('lopo/94_populations', len(unique) == 94 and set(selected['fold_ids']) == set(range(94)))
    mse = np.mean((predictions - data['y'][:, None]) ** 2, axis=0)
    ranking = sorted(range(15), key=lambda j: (mse[j], candidates[j]))
    result = selected['selection']
    check('selection/global_minimum_and_tie', result['selected_index'] == ranking[0]
          and tuple(result['selected_indices']) == candidates[ranking[0]] and result['runner_up_index'] == ranking[1])
    for field, expected in [('selected_mse', mse[ranking[0]]), ('selected_rmsep', np.sqrt(mse[ranking[0]])),
                            ('margin', mse[ranking[1]] - mse[ranking[0]]), ('exact_best_ties', np.sum(mse == mse[ranking[0]]))]:
        close('selection/' + field, result[field], expected, atol=1e-12)
    check('selection/all_scores_present', len(result['scores']) == 15)
    exported = pd.read_csv(OUT / 'selection_scores.csv', float_precision='round_trip')
    check('selection/export15_unique_rows', len(exported) == 15 and exported['index'].is_unique)
    exported = exported.set_index('index')
    centers = registration['spec']['bank_centers_nm']
    for j, indices in enumerate(candidates):
        row = result['scores'][j]
        check('selection/%d/indices' % j, row['index'] == j and tuple(row['indices']) == indices)
        close('selection/%d/mse' % j, row['mse'], mse[j], atol=1e-12)
        close('selection/%d/rmsep' % j, row['rmsep'], np.sqrt(mse[j]), atol=1e-12)
        saved = exported.loc[j]
        close('selection/%d/exported_mse' % j, saved.mse, mse[j], atol=1e-12)
        close('selection/%d/exported_rmsep' % j, saved.rmsep, np.sqrt(mse[j]), atol=1e-12)
        check('selection/%d/exported_identity' % j,
              [int(v) for v in str(saved.indices).split(',')] == list(indices)
              and [float(v) for v in str(saved.centers_nm).split(',')] == [centers[i] for i in indices]
              and saved.selected == (j == ranking[0]))
    composition = pd.DataFrame({'season': data['seasons'], 'group': data['groups']}).groupby(
        ['season', 'group']).size().rename('n_scans').reset_index()
    check('selection/composition', selected['composition'] == composition.to_dict('records'))
    saved_composition = pd.read_csv(OUT / 'development_composition.csv')
    check('selection/exported_composition', saved_composition.to_dict('records') == composition.to_dict('records'))
    return selected, warning_count


def transform(values, rich=False):
    values = np.asarray(values, dtype=np.float32).astype(np.float64)
    if rich:
        values = (values - values.mean(1, keepdims=True)) / np.maximum(values.std(1, keepdims=True), 1e-8)
        values = savgol_filter(values, window_length=11, polyorder=2, deriv=2, delta=3., axis=1)
    return values


def runtime_audit(p, data, selected, registration, manifest):
    dependency = registration['dependency']
    selection_path = OUT / 'checkpoints/selection.joblib'
    bundle = checkpoint(p, 'models', p.canonical_hash([dependency, 'models', p.digest(selection_path)]))
    indices = selected['selection']['selected_indices']
    check('freeze/selected_membership', manifest['selected_indices'] == indices == bundle['selected_indices']
          == bundle['candidate_indices'])
    check('freeze/checkpoint_hashes', manifest['selection_checkpoint_sha256'] == p.digest(selection_path)
          and manifest['model_checkpoint_sha256'] == p.digest(OUT / 'checkpoints/models.joblib')
          == p.digest(p.FROZEN / 'models.joblib'))
    check('freeze/fitting_rows', np.array_equal(bundle['fit_row_ids'], data['row_ids'])
          and set(bundle['fit_groups']) == set(data['groups']) and bundle['n_fit'] == len(data['y']))
    rows = pd.read_csv(p.FROZEN / 'training_rows.csv')
    check('freeze/training_row_file', rows.columns.tolist() == ['row_id', 'group', 'season']
          and rows.row_id.tolist() == data['row_ids'].tolist() and rows.group.tolist() == data['groups'].tolist()
          and rows.season.tolist() == data['seasons'].tolist())
    portable = json.loads((p.FROZEN / 'portable_models.json').read_text())
    check('freeze/portable_matches_checkpoint', portable == bundle['portable'])
    check('freeze/source_snapshots', all(p.digest(p.FROZEN / name) == p.digest(HERE / name)
          for name in ['inference.py', 'selection_protocol.md', 'selection_spec.json', 'environment.json']))
    frozen = {}
    exec(compile((p.FROZEN / 'inference.py').read_text(), str(p.FROZEN / 'inference.py'), 'exec'), frozen)
    response = json.loads((p.FROZEN / 'response_weights.json').read_text())
    weights = np.asarray(response['weights'])
    check('optics/grid_and_shape', response['wavelengths_nm'] == data['wavelengths'].tolist() and weights.shape == (103, 8))
    check('optics/finite_nonnegative', np.isfinite(weights).all() and np.all(weights >= 0))
    close('optics/normalized_columns', weights.sum(0), np.ones(8), atol=1e-12)
    from mango.optics import get_catalog, response_weights
    catalog = get_catalog()
    bank = [catalog[i] for i in registration['spec']['bank_catalog_indices']]
    check('optics/exact_source_catalog', response['bank'] == bank)
    close('optics/official_profile_weights', weights, response_weights(data['wavelengths'], bank), atol=0)
    raw = data['xfull']
    shifted = raw.min(1, keepdims=True)
    xbank = -np.log10(np.power(10., -(raw - shifted)) @ weights) + shifted
    close('optics/frozen_emulation_all_development', frozen['emulate_channels'](raw, weights), xbank, atol=1e-12)
    schema = json.loads((p.FROZEN / 'feature_schema.json').read_text())
    check('freeze/feature_schema', schema['candidate'] == ['led_%d' % bank[i]['center_nm'] for i in indices]
          and schema['full_bank'] == ['led_%d' % c['center_nm'] for c in bank]
          and schema['rich'] == list(map(str, data['wavelengths'])) and schema['candidate_indices'] == indices
          and schema['scan_identifier'] == 'scan_id' and schema['harvest_recommendations_enabled'] is False)
    check('freeze/selected_nominal_centers', manifest['selected_centers_nm'] == [bank[i]['center_nm'] for i in indices])
    for kind, values, components in [('candidate', xbank[:, indices], 6), ('full_bank', xbank, 6), ('rich', raw, 12)]:
        model = bundle['models'][kind]
        state = portable['models'][kind]
        transformed = transform(values, rich=kind == 'rich')
        check('model/' + kind + '/fixed_specification', model.model.n_components == state['n_components'] == components
              and model.model.scale and model.model.max_iter == 500 and model.model.tol == 1e-6
              and model.n_features == values.shape[1] and model.rich == (kind == 'rich'))
        close('model/' + kind + '/all_fitting_mean', state['x_mean'], transformed.mean(0), atol=1e-10)
        close('model/' + kind + '/all_fitting_scale', state['x_std'], transformed.std(0, ddof=1), atol=1e-10)
        close('model/' + kind + '/coefficients', state['coefficients'], np.asarray(model.model.coef_).reshape(-1), atol=0)
        independent = ((transformed - np.asarray(state['x_mean'])) / np.asarray(state['x_std'])) @ np.asarray(state['coefficients']) + state['intercept']
        expected = model.predict(values)
        portable_prediction = (frozen['predict_spectrum'](portable, values) if kind == 'rich'
                               else frozen['predict_channels'](portable, values, kind))
        close('runtime/' + kind + '/portable_vs_sklearn_10243', portable_prediction, expected, atol=1e-9)
        close('runtime/' + kind + '/independent_equation_10243', independent, expected, atol=1e-9)
    # A narrow reconstruction of registered fits, never a new candidate/model.
    audited_folds = [0, len(np.unique(data['groups'])) // 2, len(np.unique(data['groups'])) - 1]
    with threadpool_limits(limits=2):
        for fold in audited_folds:
            group = np.unique(data['groups'])[fold]
            train, target = np.flatnonzero(data['groups'] != group), np.flatnonzero(data['groups'] == group)
            estimator = PLSRegression(n_components=6, scale=True, max_iter=500, tol=1e-6)
            estimator.fit(transform(xbank[train][:, indices]), data['y'][train].astype(np.float32))
            prediction = estimator.predict(transform(xbank[target][:, indices])).ravel()
            close('audit_refit/registered_fold_%03d' % fold, prediction,
                  selected['predictions'][target, selected['selection']['selected_index']], atol=1e-9)
    return bundle, portable, frozen, xbank, audited_folds


def guard_audit():
    script = """import json
from revisions.candidate_v4 import pipeline as p
p.install_guard()
names=['data/sealed/external_labels.csv','data/processed/external_features.csv','data/processed/metadata.csv','results/external_metrics.csv','revisions/methodology_v2/results/metrics.csv','revisions/fixed_design_v3/results/metrics.csv']
denied=[]
for name in names:
    try:
        with open(name,'rb'): raise RuntimeError('Forbidden data opened')
    except PermissionError: denied.append(name)
try:
    with open('mango/models.py','r+'): raise RuntimeError('Prior source opened for writing')
except PermissionError: denied.append('prior_write')
print(json.dumps(denied))
"""
    run = command([sys.executable, '-c', script], 'real_read_and_write_guard')
    if run.returncode == 0:
        check('guard/seven_actual_denials', len(json.loads(run.stdout)) == 7)
    allowed = {'data/processed/development.csv', 'data/manifest.json', 'data/catalog/catalog.json'}
    for name in ['selection_read_audit.json', 'fitting_read_audit.json']:
        audit = json.loads((OUT / name).read_text())
        check('guard/' + name, audit['external_outcome_parsing'] is False and audit['prior_result_parsing'] is False
              and all(path in allowed or path.startswith('data/catalog/profiles/') for path in audit['paths']))


def validation_scope_audit():
    readiness = json.loads((HERE / 'validation/readiness.json').read_text())
    check('validation/no_unperformed_claims', all(readiness[key] is False for key in
          ['new_data_collected', 'new_outcomes_read', 'new_predictions_generated', 'physical_device_validated',
           'practical_acceptance_ready']) and readiness['practical_go_no_go'] == 'not_evaluable'
          and readiness['harvest_decision']['validated_pick_recommendation_available'] is False)
    check('validation/no_invented_tolerances', readiness['absolute_rmsep_limit_pp'] is None
          and readiness['comparative_rmsep_margin_pp'] is None)
    check('validation/old_seasons_ineligible', readiness['analysis']['old_dataset_seasons_ineligible'] == [1, 2, 3, 4, 5])
    files = sorted((HERE / 'validation').glob('*.csv'))
    schemas = json.loads((HERE / 'validation/schemas.json').read_text())['schemas']
    check('validation/collection_templates_exist', len(files) == 13 and set(schemas) == {path.name for path in files})
    for path in files:
        with path.open(newline='') as stream:
            records = list(csv.reader(stream))
        check('validation/' + path.name + '/header_only', len(records) == 1 and bool(records[0])
              and len(records[0]) == len(set(records[0])))
        check('validation/' + path.name + '/declared_schema', records[0] == [field['name'] for field in schemas[path.name]])
    return readiness


def resume_audit(p, protected):
    path = OUT / 'resume_verification.json'
    if not path.exists():
        return {'status': 'pending'}
    resume = json.loads(path.read_text())
    before, after = resume.get('before_sha256', {}), resume.get('after_sha256', {})
    check('resume/executed_successfully', resume.get('passed') is True and resume.get('exit_code') == 0
          and not resume.get('changed') and bool(resume.get('command')))
    check('resume/matching_complete_hash_sets', bool(before) and set(before) == set(after)
          and resume.get('files_checked') == len(before) and set(protected).issubset(before))
    current = {}
    for name in before:
        artifact = (HERE / name).resolve()
        allowed = HERE.resolve() in artifact.parents and artifact.is_file()
        check('resume/registered_file/' + name, allowed)
        if allowed:
            current[name] = p.digest(artifact)
    check('resume/before_after_and_current_bytes_identical', before == after == current)
    return resume


def verify():
    from . import pipeline as p
    started = time.time()
    CHECKS.clear()
    COMMANDS.clear()
    # Opaque preservation hashing is separate from every measurement read.
    prior = p.verify_preservation()
    check('preservation/all_prior_versions', prior['passed'], prior)
    registration = json.loads((OUT / 'registration.json').read_text())
    check('registration/self_hash', registration['dependency'] == p.canonical_hash(registration['dependencies']))
    check('registration/current_dependencies', registration['dependencies'] == p.dependencies())
    check('environment/pinned_python_and_packages', p.check_environment() ==
          json.loads((p.FROZEN / 'environment.json').read_text())['packages'])
    check('registration/no_external_or_harvest_claim', registration['spec']['external_evaluation'] is False
          and registration['spec']['harvest_recommendations_enabled'] is False)
    manifest = p.check_frozen()
    check('freeze/registration', manifest['registration_dependency'] == registration['dependency'])
    check('freeze/no_external_or_harvest_claim', manifest['external_evaluation'] is False
          and manifest['harvest_recommendations_enabled'] is False)
    required = {'models.joblib', 'portable_models.json', 'inference.py', 'response_weights.json', 'feature_schema.json',
                'selection_protocol.md', 'selection_spec.json', 'training_rows.csv', 'model_card.md', 'environment.json'}
    check('freeze/exact_artifact_set', set(manifest['files']) == required)
    protected = {str(path.relative_to(HERE)): p.digest(path) for directory in [p.FROZEN, OUT / 'checkpoints']
                 for path in directory.rglob('*') if path.is_file()}
    data = p.load_development()
    check('development/exact_scope', len(data['y']) == 10243 and len(set(data['groups'])) == 94
          and set(data['seasons']) == {1, 2, 3} and len(set(data['row_ids'])) == 10243)
    raw_frame = pd.read_csv(ROOT / 'data/processed/development.csv', float_precision='round_trip')
    check('development/independent_row_identity', raw_frame.row_id.tolist() == data['row_ids'].tolist()
          and raw_frame.group.tolist() == data['groups'].tolist() and raw_frame.season.tolist() == data['seasons'].tolist())
    close('development/independent_assay_identity', raw_frame.DM, data['y'], atol=0)
    close('development/independent_spectral_identity', raw_frame[list(map(str, data['wavelengths']))], data['xfull'], atol=0)
    selection, warning_count = selection_audit(p, data, registration)
    bundle, portable, frozen, xbank, audited_folds = runtime_audit(p, data, selection, registration, manifest)
    guard_audit()
    readiness = validation_scope_audit()
    check('validation/candidate_freeze_hash', readiness.get('candidate_manifest_sha256') == p.digest(p.FROZEN / 'manifest.json'))
    check('validation/model_bundle_hash', readiness.get('model_bundle_sha256') == p.digest(p.FROZEN / 'models.joblib'))
    check('validation/selection_registration_hash', readiness.get('candidate_selection_registration_sha256') ==
          p.digest(OUT / 'registration.json'))
    run = command([sys.executable, '-m', 'pytest', '-q', 'revisions/candidate_v4/test_candidate.py'], 'software_tests')
    if run.returncode == 0:
        check('software/test_source_recorded', True, p.digest(HERE / 'test_candidate.py'))
    test_record = json.loads((OUT / 'software_tests.json').read_text())
    check('software/saved_test_evidence_current', test_record['passed'] is True and test_record['exit_code'] == 0
          and test_record['tests_passed'] == 22 and test_record['test_source_sha256'] == p.digest(HERE / 'test_candidate.py'))
    cli_output = OUT / 'cli_example_predictions.csv'
    command([sys.executable, 'revisions/candidate_v4/predict.py', '--input',
             'revisions/candidate_v4/examples/development_channels.csv', '--mode', 'candidate',
             '--output', str(cli_output.relative_to(ROOT))], 'normal_candidate_cli')
    if cli_output.exists():
        cli = pd.read_csv(cli_output, float_precision='round_trip')
        check('cli/row_identity', cli.scan_id.tolist() == data['row_ids'][:3].tolist())
        close('cli/prediction_parity', cli.prediction_dm_percent,
              frozen['predict_channels'](portable, xbank[:3, manifest['selected_indices']]), atol=1e-9)
        check('cli/representation_label', set(cli['mode']) == {'candidate'} and cli.representation.notna().all())
    portable_execution = json.loads((OUT / 'portable_execution.json').read_text())
    check('portable_execution/current_copied_bundle_evidence', portable_execution['passed'] is True
          and portable_execution['rows'] == 3 and bool(portable_execution.get('method'))
          and portable_execution['candidate_manifest_sha256'] == p.digest(p.FROZEN / 'manifest.json')
          and portable_execution['cli_source_sha256'] == p.digest(HERE / 'predict.py'))
    close('portable_execution/saved_predictions', portable_execution['predictions'],
          frozen['predict_channels'](portable, xbank[:3, manifest['selected_indices']]), atol=1e-9)
    replay = pd.read_csv(OUT / 'cli_replay_predictions.csv', float_precision='round_trip')
    check('cli/replay_identity', replay.scan_id.tolist() == data['row_ids'][:3].tolist()
          and set(replay['mode']) == {'replay'} and replay.representation.notna().all())
    for field, expected in [('candidate_dm_percent', frozen['predict_channels'](portable, xbank[:3, manifest['selected_indices']])),
                            ('full_bank_dm_percent', frozen['predict_channels'](portable, xbank[:3], kind='full_bank')),
                            ('rich_dm_percent', frozen['predict_spectrum'](portable, data['xfull'][:3]))]:
        close('cli/replay_' + field, replay[field], expected, atol=1e-9)
    after = {str(path.relative_to(HERE)): p.digest(path) for directory in [p.FROZEN, OUT / 'checkpoints']
             for path in directory.rglob('*') if path.is_file()}
    check('verification/frozen_and_checkpoints_unchanged', protected == after)
    check('verification/final_frozen_hash_check', p.check_frozen() == manifest)
    resume = resume_audit(p, protected)
    result = {'passed': all(row['passed'] for row in CHECKS), 'n_checks': len(CHECKS),
              'failed_checks': [row for row in CHECKS if not row['passed']], 'checks': CHECKS,
              'commands': COMMANDS, 'elapsed_seconds': time.time() - started,
              'prior_versions_preservation': prior, 'freeze_manifest_sha256': p.digest(p.FROZEN / 'manifest.json'),
              'verification_source_sha256': p.digest(__file__), 'software_test_source_sha256': p.digest(HERE / 'test_candidate.py'),
              'lopo_folds': 94, 'candidate_subsets': 15, 'runtime_parity_rows': 10243,
              'fold_warning_records': warning_count, 'final_fit_warnings': bundle['warnings'],
              'limited_independent_audit_refit_folds': audited_folds,
              'audit_refit_scope': 'Three registered selected-subset LOPO reconstruction fits; no selection changes, saved models, or new performance claim.',
              'external_outcomes_parsed': False, 'new_validation_accuracy_estimated': False,
              'scientific_status': 'Frozen research candidate; independent, physical and harvest-decision validation remain incomplete.',
              'resume': resume}
    p.atomic_json(OUT / 'verification.json', result)
    resumed = (resume.get('passed') is True and not resume.get('changed') and resume.get('files_checked', 0) > 0)
    lines = ['# Candidate v4: independent freeze verification', '',
             '**%s: %d checks; %d failures.**' % ('PASS' if result['passed'] else 'FAIL', len(CHECKS), len(result['failed_checks'])), '',
             '- Reconstructed all 94 leave-population-out partitions, checkpoint hashes, 15 subset scores and exact selection ties.',
             '- Verified the frozen candidate, full-bank and rich-spectrum models use the same 10,243 development fitting rows.',
             '- Compared portable inference, saved sklearn models and independent equations on all 10,243 development inputs. This is software parity, not independent accuracy.',
             '- Reconstructed the selected-subset fit in registered LOPO folds 0, 47 and 93 as limited audit calculations; all frozen/checkpoint bytes remained unchanged.',
             '- Executed the synthetic software suite, actual read/write guards and the normal six-channel prediction CLI; command records are in results/verification.json.',
             '- %d prior-version files were checked without parsing their data; previous studies remain unchanged.' % prior['files'], '',
             ('Completed full resume: %d files remained byte-identical.' % resume['files_checked']) if resumed else
             'Full resume byte-preservation evidence is pending. Numerical freeze verification alone does not establish a completed resume.', '',
             'The LOPO selection minimum remains a tuning statistic. No external seasons were rescored. New independent populations, physical calibration, practical error tolerances and a validated harvest decision remain unresolved.', '',
             'Machine-readable evidence: results/verification.json. Freeze: frozen/manifest.json.']
    p.write_bytes(HERE / 'verification_report.md', ('\n'.join(lines) + '\n').encode())
    print(json.dumps({key: result[key] for key in ['passed', 'n_checks', 'failed_checks']}, indent=2))
    if not result['passed']:
        raise AssertionError('Candidate freeze verification failed; see results/verification.json')
    return result


if __name__ == '__main__':
    verify()
