#!/usr/bin/env python3
"""Sparse candidate inference or explicit offline spectral replay, without fitting."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_bundle(bundle):
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if manifest.get('status') != 'frozen' or not manifest.get('files'):
        raise ValueError('A complete frozen bundle is required')
    for name, expected in manifest['files'].items():
        path = (bundle / name).resolve()
        if bundle not in path.parents or not path.is_file() or sha(path) != expected:
            raise ValueError('Frozen artifact mismatch: ' + name)
    actual = {str(f.relative_to(bundle)) for f in bundle.rglob('*') if f.is_file() and f.name != 'manifest.json'}
    if actual != set(manifest['files']):
        raise ValueError('Unregistered or missing bundle files')
    module = importlib.util.spec_from_file_location('frozen_mango_inference', bundle / 'inference.py')
    runtime = importlib.util.module_from_spec(module)
    module.loader.exec_module(runtime)
    return runtime, json.loads((bundle / 'portable_models.json').read_text()), json.loads(
        (bundle / 'feature_schema.json').read_text()), manifest


def run(bundle, input_path, mode):
    runtime, portable, schema, manifest = load_bundle(bundle)
    features = schema['rich' if mode == 'replay' else mode]
    with Path(input_path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != {'scan_id', *features}:
            raise ValueError('Input requires exactly scan_id and the registered feature columns; assays, metadata and extra channels are rejected')
        rows = list(reader)
    if not rows or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('Input must contain complete rows of registered width')
    ids = [row['scan_id'] for row in rows]
    if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Nonempty unique scan_id values are required')
    values = [[float(row[name]) for name in features] for row in rows]
    if mode == 'replay':
        optics = json.loads((Path(bundle) / 'response_weights.json').read_text())
        bank = runtime.emulate_channels(values, optics['weights'])
        outputs = {
            'candidate_dm_percent': runtime.predict_channels(portable, bank[:, manifest['selected_indices']]),
            'full_bank_dm_percent': runtime.predict_channels(portable, bank, kind='full_bank'),
            'rich_dm_percent': runtime.predict_spectrum(portable, values)}
    elif mode == 'rich':
        outputs = {'prediction_dm_percent': runtime.predict_spectrum(portable, values)}
    else:
        outputs = {'prediction_dm_percent': runtime.predict_channels(portable, values, kind=mode)}
    result = []
    for index, identifier in enumerate(ids):
        result.append({'scan_id': identifier, **{key: float(value[index]) for key, value in outputs.items()},
                       'mode': mode, 'representation': 'research spectral simulation; physical transfer unvalidated'})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent / 'frozen')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--mode', choices=['candidate', 'full_bank', 'rich', 'replay'], default='candidate')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None and (args.output.resolve() == args.input.resolve() or
                                   args.bundle.resolve() in args.output.resolve().parents):
        raise ValueError('Output must not overwrite input or a frozen artifact')
    rows = run(args.bundle, args.input, args.mode)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        value = buffer.getvalue()
        if not args.output.exists() or args.output.read_text() != value:
            args.output.write_text(value)
    else:
        print(buffer.getvalue(), end='')


if __name__ == '__main__':
    main()
