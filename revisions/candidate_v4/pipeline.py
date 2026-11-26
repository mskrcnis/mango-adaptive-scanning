"""Checkpointed development-only finalization with an immutable candidate lock."""
import hashlib
import io
import json
import os
import platform
from importlib.metadata import version
from pathlib import Path
import shutil
import sys
import time

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from mango.optics import get_catalog, response_weights
from . import engine, inference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'results'
FROZEN = HERE / 'frozen'
READ_PATHS = set()
GUARDED = False


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_bytes(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == value:
        return
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(value)
    temporary.replace(path)


def atomic_json(path, value):
    write_bytes(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())


def csv(path, frame):
    write_bytes(path, frame.to_csv(index=False, float_format='%.17g').encode())


def event(message):
    HERE.mkdir(parents=True, exist_ok=True)
    with (HERE / 'RUN_STATUS.md').open('a') as stream:
        stream.write('\n- %s: %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S %z'), message))
    print(message, flush=True)


def prior_files():
    files = []
    for name in ('data', 'results', 'mango', 'config', 'docs', 'figures', 'manuscript', 'tests',
                 'revisions/methodology_v2', 'revisions/fixed_design_v3'):
        files.extend(f for f in (ROOT / name).rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    files.extend(f for f in ROOT.iterdir() if f.is_file() and f.name != 'RUN_STATUS.md')
    return sorted(files)


def snapshot_prior():
    path = HERE / 'prior_versions_preservation.json'
    if not path.exists():
        atomic_json(path, {'sha256': {str(f.relative_to(ROOT)): digest(f) for f in prior_files()},
                           'scope': 'Opaque-byte integrity hashing only, including old sealed files; no data parsing. Root status and runtime caches excluded.'})


def verify_preservation():
    expected = json.loads((HERE / 'prior_versions_preservation.json').read_text())['sha256']
    changed = [n for n, h in expected.items() if not (ROOT / n).is_file() or digest(ROOT / n) != h]
    added = sorted(set(str(p.relative_to(ROOT)) for p in prior_files()) - set(expected))
    return {'passed': not changed and not added, 'files': len(expected), 'changed': changed, 'added': added}


def dependencies():
    names = ['revisions/candidate_v4/' + n for n in
             ('pipeline.py', 'engine.py', 'inference.py', 'selection_protocol.md', 'selection_spec.json', 'environment.json')]
    names += ['mango/optics.py', 'data/manifest.json', 'data/processed/development.csv',
              'data/catalog/catalog.json']
    names += [str(f.relative_to(ROOT)) for f in sorted((ROOT / 'data/catalog/profiles').glob('*.csv'))]
    return {name: digest(ROOT / name) for name in names}


def register():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot_prior()
    deps = dependencies()
    value = {'dependency': canonical_hash(deps), 'dependencies': deps,
             'spec': json.loads((HERE / 'selection_spec.json').read_text())}
    path = OUT / 'registration.json'
    if path.exists() and json.loads(path.read_text()) != value:
        raise RuntimeError('Registered fitting dependencies changed. Preserve this candidate and create a new revision.')
    atomic_json(path, value)
    return value


def check_environment():
    expected = json.loads((HERE / 'environment.json').read_text())
    actual = {name: version(name) for name in expected['packages']}
    if platform.python_version() != expected['python'] or actual != expected['packages']:
        raise RuntimeError('The registered scientific environment changed; restore it or use a new revision')
    return actual


def install_guard():
    global GUARDED
    if GUARDED:
        return
    allowed_data = {'data/processed/development.csv', 'data/manifest.json', 'data/catalog/catalog.json'}
    allowed_data.update(str(p.relative_to(ROOT)) for p in (ROOT / 'data/catalog/profiles').glob('*.csv'))
    previous = (ROOT / 'results', ROOT / 'revisions/methodology_v2/results',
                ROOT / 'revisions/fixed_design_v3/results')
    def hook(name, args):
        if name != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        try:
            relative = str(path.relative_to(ROOT))
        except ValueError:
            return
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
        if writing:
            if HERE not in path.parents:
                raise PermissionError('Previous project versions are read-only: ' + relative)
            return
        if relative.startswith('data/'):
            if relative not in allowed_data:
                raise PermissionError('Only registered development and optical inputs allowed: ' + relative)
            READ_PATHS.add(relative)
        if any(old in path.parents for old in previous):
            raise PermissionError('Earlier scored results are excluded: ' + relative)
    sys.addaudithook(hook)
    GUARDED = True


def load_development():
    path = ROOT / 'data/processed/development.csv'
    source = json.loads((ROOT / 'data/manifest.json').read_text())
    if source['dataset_doi'] != '10.17632/46htwnp833.3' or digest(path) != source['artifacts']['processed/development.csv']:
        raise AssertionError('Official development provenance mismatch')
    frame = pd.read_csv(path, float_precision='round_trip')
    wave = np.arange(684, 991, 3)
    required = ['row_id', 'season', 'group', 'DM'] + list(map(str, wave))
    if set(frame.columns) != set(required):
        raise ValueError('Unexpected development schema')
    if len(frame) != 10243 or frame.row_id.nunique() != len(frame) or frame.group.nunique() != 94:
        raise ValueError('Unexpected development population/scan identity')
    if set(frame.season) != {1, 2, 3} or frame.groupby('group').season.nunique().max() != 1:
        raise ValueError('Only season-nested development populations allowed')
    x = frame[list(map(str, wave))].to_numpy(float)
    y = frame.DM.to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite development measurements')
    spectrum_groups = {}
    for row, group in zip(x, frame.group):
        key = hashlib.sha256(row.astype('<f8').tobytes()).hexdigest()
        if key in spectrum_groups and spectrum_groups[key] != group:
            raise ValueError('Exact spectral duplicate crosses population groups')
        spectrum_groups[key] = group
    return {'xfull': x, 'y': y, 'row_ids': frame.row_id.to_numpy(str),
            'groups': frame.group.to_numpy(str), 'seasons': frame.season.to_numpy(int), 'wavelengths': wave}


def optical_inputs(data):
    spec = json.loads((HERE / 'selection_spec.json').read_text())
    catalog = get_catalog()
    bank = [catalog[i] for i in spec['bank_catalog_indices']]
    if [c['center_nm'] for c in bank] != spec['bank_centers_nm']:
        raise AssertionError('Catalog membership/order changed')
    weights = response_weights(data['wavelengths'], bank)
    xbank = inference.emulate_channels(data['xfull'], weights)
    return bank, weights, xbank


def checkpoint(name, key, fn):
    path = OUT / 'checkpoints' / (name + '.joblib')
    meta = path.with_suffix('.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and meta.exists():
        saved = json.loads(meta.read_text())
        if saved.get('status') == 'complete' and saved.get('dependency') == key and saved.get('sha256') == digest(path):
            event('Reused ' + name)
            return joblib.load(path)
    if (FROZEN / 'manifest.json').exists():
        raise RuntimeError('Cannot refit/repair a checkpoint after candidate freeze: ' + name)
    started = time.perf_counter()
    atomic_json(meta, {'status': 'running', 'dependency': key})
    event('Started ' + name)
    try:
        value = fn()
        temporary = path.with_suffix('.joblib.tmp')
        joblib.dump(value, temporary, compress=3)
        temporary.replace(path)
        atomic_json(meta, {'status': 'complete', 'dependency': key, 'sha256': digest(path),
                           'seconds': time.perf_counter() - started})
        event('Completed %s in %.2fs' % (name, time.perf_counter() - started))
        return value
    except BaseException as exc:
        atomic_json(meta, {'status': 'failed', 'dependency': key, 'error': repr(exc)})
        event('FAILED ' + name + ': ' + repr(exc))
        raise


def select(pilot=False):
    check_environment()
    reg = register()
    install_guard()
    data = load_development()
    bank, weights, xbank = optical_inputs(data)
    groups = np.unique(data['groups'])
    predicted = np.full((len(xbank), 15), np.nan)
    fold_ids = np.full(len(xbank), -1, dtype=int)
    with threadpool_limits(limits=2):
        for fold, group in enumerate(groups):
            fit = np.flatnonzero(data['groups'] != group)
            target = np.flatnonzero(data['groups'] == group)
            def fit_one():
                result = engine.fit_fold(xbank, data['y'], fit, target)
                result.update(fit_groups=sorted(set(data['groups'][fit])), target_groups=[str(group)],
                              fit_row_ids=data['row_ids'][fit], target_row_ids=data['row_ids'][target])
                return result
            value = checkpoint('cv_%03d' % fold, canonical_hash([reg['dependency'], 'lopo', fold, str(group)]), fit_one)
            if not np.array_equal(value['fit_indices'], fit) or not np.array_equal(value['target_indices'], target):
                raise AssertionError('Checkpoint rows do not match LOPO assignment')
            predicted[target] = value['predictions']
            fold_ids[target] = fold
            if pilot:
                event('Real-data pilot complete: one of 94 registered folds; no selection yet.')
                return
    if np.any(fold_ids < 0) or not np.isfinite(predicted).all():
        raise AssertionError('Incomplete selection predictions')
    composition = pd.DataFrame({'season': data['seasons'], 'group': data['groups']}).groupby(
        ['season', 'group']).size().rename('n_scans').reset_index().to_dict('records')
    value = checkpoint('selection', canonical_hash([reg['dependency'], 'selection']), lambda: {
        **{k: data[k] for k in ('row_ids', 'groups', 'seasons', 'y')}, 'predictions': predicted,
        'subsets': engine.candidate_subsets(), 'selection': engine.select_subset(predicted, data['y']),
        'fold_ids': fold_ids, 'composition': composition})
    atomic_json(OUT / 'selection_read_audit.json', {'stage': 'development_selection', 'paths': sorted(READ_PATHS),
        'external_outcome_parsing': False, 'prior_result_parsing': False})
    event('All 94 LOPO folds complete; one fixed-six candidate selected by the locked rule.')
    return value


def check_frozen():
    manifest = json.loads((FROZEN / 'manifest.json').read_text())
    if manifest.get('status') != 'frozen' or not manifest.get('files'):
        raise ValueError('Incomplete frozen manifest')
    for name, expected in manifest['files'].items():
        path = (FROZEN / name).resolve()
        if FROZEN.resolve() not in path.parents or not path.is_file() or digest(path) != expected:
            raise ValueError('Frozen artifact mismatch: ' + name)
    actual = {str(f.relative_to(FROZEN)) for f in FROZEN.rglob('*') if f.is_file() and f.name != 'manifest.json'}
    if actual != set(manifest['files']):
        raise ValueError('Frozen bundle has missing or unregistered files')
    return manifest


def freeze():
    check_environment()
    reg = register()
    if (FROZEN / 'manifest.json').exists():
        manifest = check_frozen()
        if manifest['registration_dependency'] != reg['dependency']:
            raise ValueError('Frozen dependency mismatch')
        event('Reused intact frozen candidate; no fitting occurred.')
        return manifest
    install_guard()
    selection_path = OUT / 'checkpoints/selection.joblib'
    selection_meta = json.loads(selection_path.with_suffix('.json').read_text())
    if selection_meta.get('status') != 'complete' or selection_meta.get('dependency') != canonical_hash([reg['dependency'], 'selection']) or selection_meta.get('sha256') != digest(selection_path):
        raise ValueError('Selection checkpoint incomplete or changed')
    selected = joblib.load(selection_path)
    indices = selected['selection']['selected_indices']
    data = load_development()
    if not np.array_equal(selected['row_ids'], data['row_ids']):
        raise ValueError('Final fitting rows differ from registered selection rows')
    bank, weights, xbank = optical_inputs(data)
    def fit_models():
        with threadpool_limits(limits=2):
            result = engine.fit_final(xbank, data['xfull'], data['y'], indices)
        result.update(fit_row_ids=data['row_ids'], fit_groups=sorted(set(data['groups'])), selected_indices=indices)
        return result
    fitted = checkpoint('models', canonical_hash([reg['dependency'], 'models', digest(selection_path)]), fit_models)
    staging = HERE / 'frozen_staging'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    write_bytes(staging / 'models.joblib', (OUT / 'checkpoints/models.joblib').read_bytes())
    atomic_json(staging / 'portable_models.json', fitted['portable'])
    atomic_json(staging / 'response_weights.json', {'wavelengths_nm': data['wavelengths'].tolist(),
        'weights': weights.tolist(), 'bank': bank, 'detector': 'flat assumed', 'reference': 'flat assumed',
        'input': 'inherited base-10 apparent absorbance convention; physical transfer unvalidated'})
    schema = {'candidate': ['led_%d' % bank[i]['center_nm'] for i in indices],
              'full_bank': ['led_%d' % c['center_nm'] for c in bank],
              'rich': list(map(str, data['wavelengths'])), 'scan_identifier': 'scan_id',
              'candidate_indices': indices, 'units': 'reference-normalized finite-band apparent absorbance',
              'prediction_units': 'dry-matter percentage points (percent fresh weight)',
              'harvest_recommendations_enabled': False}
    atomic_json(staging / 'feature_schema.json', schema)
    for name in ('inference.py', 'selection_protocol.md', 'selection_spec.json', 'environment.json'):
        write_bytes(staging / name, (HERE / name).read_bytes())
    csv(staging / 'training_rows.csv', pd.DataFrame({'row_id': data['row_ids'], 'group': data['groups'], 'season': data['seasons']}))
    centers = [bank[i]['center_nm'] for i in indices]
    card = ['# Frozen fixed-channel research candidate', '',
            'Selected nominal centers: **%s nm**.' % ', '.join(map(str, centers)), '',
            'Intended research use: estimate mango dry matter and assess limits for future harvest-timing support. No validated pick/wait rule is supplied.', '',
            'Selection: 15 endpoint-preserving subsets; 94 leave-population-out folds on seasons 1–3. Final fitting: all 10,243 development scans. No independent accuracy claim is attached to this final fit.', '',
            'Candidate: six-component autoscaled PLS on exactly six channels. Comparators: six-component full-eight PLS and twelve-component full-spectrum PLS with SNV and second derivative. All use identical fitting rows.', '',
            'The optical integration weights describe simulated channels from digitized nominal emitter curves. Detector/reference responses are assumed flat. Physical instruments require separate calibration/transfer evidence; measured energy and timing are unavailable.', '',
            'Dry matter is returned in percent fresh weight. Application error tolerance, cultivar/market harvest threshold, and prospective sampling plan remain unresolved. No per-fruit uncertainty interval or calibrated decision probability is provided.', '',
            'Use portable_models.json with inference.py for sparse inference; models.joblib is the fitted reference for trusted-local verification. Do not unpickle unknown external model files.', '',
            'The local manifest verifies file integrity. New fitting dependencies or physical recalibration require a new version.']
    write_bytes(staging / 'model_card.md', ('\n'.join(card) + '\n').encode())
    manifest = {'schema_version': 1, 'status': 'frozen', 'registration_dependency': reg['dependency'],
                'files': {str(f.relative_to(staging)): digest(f) for f in sorted(staging.rglob('*')) if f.is_file()},
                'selected_indices': indices, 'selected_centers_nm': centers,
                'selection_checkpoint_sha256': digest(selection_path),
                'model_checkpoint_sha256': digest(OUT / 'checkpoints/models.joblib'),
                'scientific_status': 'research candidate frozen; independent and physical validation not performed',
                'external_evaluation': False, 'harvest_recommendations_enabled': False}
    atomic_json(staging / 'manifest.json', manifest)
    if FROZEN.exists():
        raise RuntimeError('Unexpected pre-existing frozen directory; preserve and investigate')
    staging.replace(FROZEN)
    atomic_json(OUT / 'fitting_read_audit.json', {'stage': 'final_fitting', 'paths': sorted(READ_PATHS),
        'external_outcome_parsing': False, 'prior_result_parsing': False})
    check_frozen()
    event('Candidate and both references frozen: ' + ', '.join(map(str, centers)) + ' nm.')
    return manifest


def report():
    manifest = check_frozen()
    selection = joblib.load(OUT / 'checkpoints/selection.joblib')
    schema = json.loads((FROZEN / 'feature_schema.json').read_text())
    scores = pd.DataFrame(selection['selection']['scores'])
    centers = json.loads((HERE / 'selection_spec.json').read_text())['bank_centers_nm']
    scores['centers_nm'] = scores['indices'].map(lambda row: ','.join(str(centers[i]) for i in row))
    scores['selected'] = scores['index'] == selection['selection']['selected_index']
    scores['indices'] = scores['indices'].map(lambda row: ','.join(map(str, row)))
    csv(OUT / 'selection_scores.csv', scores)
    csv(OUT / 'development_composition.csv', pd.DataFrame(selection['composition']))
    data = load_development()
    optical = json.loads((FROZEN / 'response_weights.json').read_text())
    xbank = inference.emulate_channels(data['xfull'][:3], optical['weights'])
    example = pd.DataFrame(xbank[:, manifest['selected_indices']], columns=schema['candidate'])
    example.insert(0, 'scan_id', data['row_ids'][:3])
    csv(HERE / 'examples/development_channels.csv', example)
    rich = pd.DataFrame(data['xfull'][:3], columns=schema['rich'])
    rich.insert(0, 'scan_id', data['row_ids'][:3])
    csv(HERE / 'examples/development_spectra.csv', rich)
    chosen = ', '.join(map(str, manifest['selected_centers_nm']))
    text = ['# Candidate freeze report', '', '**Frozen research candidate: %s nm.**' % chosen, '',
            'One configuration was selected by the predeclared finalization rule, then fitted with two comparison models on the same 10,243 development scans. All 94 LOPO folds and all 15 subset scores are retained.', '',
            'The LOPO minimum is a selection statistic, not independently validated performance. This final artifact differs from the fold-specific v3 models. No external outcomes were parsed, no seasons 4–5 were rescored, and no new independent accuracy result is claimed.', '',
            'The candidate consumes exactly six finite-band readings. The full-eight comparator and full-spectrum PLS are separate models with separate input contracts. The example CSVs contain three training-development rows for software demonstration only.', '',
            'Research-paper scope: preserve the established fixed-design improvement and the negative adaptive-objective finding. Harvest-timing scope: estimate dry matter now; validate any cultivar/market-specific pick/wait rule on new data before claiming decision support.', '',
            'Application error tolerance, a justified harvest threshold, sampling precision, new fruit-identified populations and physical calibration/transfer remain unresolved. See validation_protocol.md and validation/readiness.json. No universal harvest cutoff, per-fruit confidence interval or hardware saving is supplied.', '',
            'Portable bundle: frozen/manifest.json, portable_models.json, inference.py, response_weights.json and feature_schema.json. Reference fitted models and training row provenance are included. Full subset scores: results/selection_scores.csv. Independent checks: verification_report.md.', '',
            'Resume: .venv/bin/python revisions/candidate_v4/run.py all --resume.']
    write_bytes(HERE / 'decision_report.md', ('\n'.join(text) + '\n').encode())
    event('Candidate report and real development software examples generated; no accuracy claim added.')
