"""Atomic dependency-aware checkpoints and append-only attempt history."""
import hashlib
import json
import os
import platform
import subprocess
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str, allow_nan=False) + '\n')
    os.replace(str(temp), str(path))


def event(message):
    stamp = time.strftime('%Y-%m-%d %H:%M:%S %z')
    print('[' + stamp + '] ' + message, flush=True)
    with (ROOT / 'RUN_STATUS.md').open('a') as stream:
        stream.write('\n- ' + stamp + ': ' + message + '\n')


def ledger(record):
    path = ROOT / 'results/run_ledger.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        stream.write(json.dumps(record, default=str, allow_nan=False) + '\n')


def checkpoint(key, fingerprint, action):
    import joblib
    path = ROOT / 'results/checkpoints' / (key + '.joblib')
    meta = path.with_suffix('.json')
    if path.exists() and meta.exists():
        old = json.loads(meta.read_text())
        if old['fingerprint'] == fingerprint and old['sha256'] == digest(path) and old['status'] == 'complete':
            return joblib.load(path)
        event('Invalidating stale checkpoint ' + key + ' and dependent results on next execution.')
        archive = ROOT / 'results/attempts/stale_checkpoints' / old['fingerprint'][:16]
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, archive / path.name)
        shutil.copy2(meta, archive / meta.name)
    started = time.time()
    attempt = {'key': key, 'fingerprint': fingerprint, 'started': started, 'status': 'running'}
    ledger(attempt)
    event('Started ' + key)
    try:
        value = action()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.joblib.tmp')
        joblib.dump(value, temp, compress=3)
        os.replace(str(temp), str(path))
        record = dict(attempt, status='complete', elapsed_seconds=time.time() - started, sha256=digest(path))
        atomic_json(meta, record)
        ledger(record)
        event('Completed ' + key + ' in %.1f seconds' % record['elapsed_seconds'])
        return value
    except BaseException as exc:
        record = dict(attempt, status='failed', elapsed_seconds=time.time() - started, error=repr(exc))
        ledger(record)
        event('FAILED ' + key + ': ' + repr(exc))
        raise


def environment():
    import importlib
    out = {'python': sys.version, 'executable': sys.executable, 'base_prefix': sys.base_prefix,
           'platform': platform.platform(), 'logical_cpus': os.cpu_count(),
           'threads': {k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
           'packages': {}}
    for name in ('numpy', 'pandas', 'scipy', 'sklearn', 'torch', 'matplotlib', 'joblib', 'requests', 'pytest'):
        m = importlib.import_module(name)
        out['packages'][name] = m.__version__
    import torch
    out['cuda_available'] = torch.cuda.is_available()
    out['gpu'] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    out['ram_bytes'] = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    info=Path('/proc/cpuinfo')
    if info.exists():
        out['cpu_model']=next((line.split(':',1)[1].strip() for line in info.read_text().splitlines() if line.startswith('model name')),None)
    out['cuda_runtime']=torch.version.cuda
    out['cudnn_version']=torch.backends.cudnn.version()
    return out
