"""Verified version-3 mango data, with external assays separated from fitting."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAVELENGTHS = np.arange(684, 991, 3, dtype=int)
SOURCE_NAME = 'NAnderson2020MendeleyMangoNIRDataV3.csv'
CANONICAL_SHA256 = '1e0e450417ed96b47b3808556706afa84a2e6441a76e380a8b64b18d85fddee1'
SOURCE_DOI = '10.17632/46htwnp833.3'
METADATA = ['Set', 'Season', 'Region', 'Date', 'Type', 'Cultivar', 'Pop', 'Temp']


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def _atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(value)
    os.replace(temporary, path)


def _json(path, obj):
    _atomic(path, (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())


def _download(url):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 Mango-adaptive-scan-data-audit/1.0',
        'Accept': 'application/vnd.mendeley-public-dataset.1+json, */*',
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _data_dir(data_dir):
    return Path(data_dir) if data_dir is not None else ROOT / 'data'


@dataclass
class DataSet:
    X: np.ndarray
    y: np.ndarray | None
    seasons: np.ndarray
    groups: np.ndarray
    row_ids: np.ndarray
    wavelengths: np.ndarray
    metadata: pd.DataFrame

    def subset(self, index):
        index = np.asarray(index)
        return DataSet(self.X[index], None if self.y is None else self.y[index],
                       self.seasons[index], self.groups[index], self.row_ids[index],
                       self.wavelengths.copy(), self.metadata.iloc[np.flatnonzero(index) if index.dtype == bool else index].reset_index(drop=True))

    def __len__(self):
        return len(self.X)


def prepare_data(data_dir=None, data_path=None, force=False):
    """Download/cache the official CSV and segregate external outcomes.

    Data validity checks are schema-only. External DM strings are copied to a
    sealed CSV without conversion, summary, imputation, or outcome filtering.
    The returned audit contains counts and metadata only for external seasons.
    A local override must match the official version-3 content checksum.
    """
    base = _data_dir(data_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    provenance = base / 'provenance'
    provenance.mkdir(exist_ok=True)
    manifest_path = base / 'manifest.json'
    implementation = sha256(__file__)
    if manifest_path.exists() and data_path is None and not force:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('preparation_code_sha256') == implementation:
            if all((base / p).is_file() and sha256(base / p) == digest for p, digest in manifest['artifacts'].items()):
                return manifest
    records, listings, retrieval_failures = {}, {}, []
    for version in [3, 4, 6]:
        for kind, url in [
            ('record', f'https://data.mendeley.com/public-api/datasets/46htwnp833/snapshot/{version}'),
            ('files', f'https://data.mendeley.com/public-api/datasets/46htwnp833/files?folder_id=root&version={version}&$start=0&$limit=1000'),
        ]:
            target = provenance / f'{kind}_v{version}.json'
            try:
                if not target.exists():
                    _atomic(target, _download(url))
                obj = json.loads(target.read_text())
                (records if kind == 'record' else listings)[version] = obj
            except Exception as exc:
                retrieval_failures.append({'url': url, 'error': str(exc)})
    if 3 not in records or records[3].get('version') != 3 or records[3].get('id') != '46htwnp833':
        raise RuntimeError('Version-3 provider record unavailable or invalid; supply cached official provenance.')
    if records[3]['licence']['short_name'] != 'CC BY 4.0':
        raise ValueError('Unexpected source license.')
    source_entries = [f for f in listings.get(3, []) if f['filename'] == SOURCE_NAME]
    if not source_entries:
        source_entries = [f for version in [4, 6] for f in listings.get(version, [])
                          if f['filename'] in [SOURCE_NAME, 'MangoDMC_NIR_Data_v3.csv']]
    if not source_entries:
        raise RuntimeError('Official version-3 CSV missing from all resolved official listings.')
    entry = source_entries[0]
    raw = base / 'sealed' / SOURCE_NAME
    raw.parent.mkdir(parents=True, exist_ok=True)
    if data_path is not None:
        original = Path(data_path).expanduser().resolve()
        if sha256(original) != CANONICAL_SHA256:
            raise ValueError('Offline override is not the verified official V3 CSV (SHA256 mismatch).')
        if original != raw.resolve():
            _atomic(raw, original.read_bytes())
    elif not raw.exists():
        _atomic(raw, _download(entry['content_details']['download_url']))
    if sha256(raw) != CANONICAL_SHA256 or entry['content_details']['sha256_hash'] != CANONICAL_SHA256:
        raise ValueError('Downloaded/cached file checksum differs from the official V3 data.')
    raw.chmod(0o600)
    with raw.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        required = METADATA + ['DM'] + [str(w) for w in WAVELENGTHS]
        if header is None or len(header) != len(set(header)) or any(c not in header for c in required):
            raise ValueError('Missing required column or duplicate CSV header.')
        all_wave = [int(c) for c in header if c.isdigit()]
        if [int(c) for c in header if c in set(map(str, WAVELENGTHS))] != WAVELENGTHS.tolist():
            raise ValueError('Common comparison wavelengths are not exactly 684:3:990 in order.')
        development, features, labels, metadata, invalid = [], [], [], [], []
        seen_spectra = defaultdict(list)
        exact_rows = Counter()
        all_spectra_missing = Counter()
        for number, row in enumerate(reader, 1):
            season = int(row['Season'])
            row_id = f'v3_{number:06d}'
            if season not in [1, 2, 3, 4, 5]:
                raise ValueError(f'Unregistered season in source row {number}.')
            group = f's{season}_pop{row["Pop"].strip()}'
            if not row['Pop'].strip():
                raise ValueError(f'Population missing for source row {number}.')
            x = np.asarray([float(row[str(w)]) for w in WAVELENGTHS], dtype='<f8')
            if not np.isfinite(x).all():
                invalid.append({'row_id': row_id, 'season': season, 'reason': 'nonfinite_common_spectrum'})
                continue
            for w in all_wave:
                try:
                    missing = not np.isfinite(float(row[str(w)]))
                except ValueError:
                    missing = True
                all_spectra_missing[str(w)] += int(missing)
            x[x == 0] = 0.0
            spectrum_hash = hashlib.sha256(x.tobytes()).hexdigest()
            seen_spectra[spectrum_hash].append((row_id, season, group))
            # Only metadata and spectra enter this audit; external assay strings
            # never enter exact-row comparisons or reported summaries.
            exact_rows[tuple(row[c] for c in METADATA) + tuple(x)] += 1
            meta = {'row_id': row_id, 'source_row': number, 'season': season, 'group': group,
                    'spectrum_sha256': spectrum_hash, **{c: row[c] for c in METADATA}}
            metadata.append(meta)
            common = {'row_id': row_id, 'season': season, 'group': group,
                      **{str(w): float(v) for w, v in zip(WAVELENGTHS, x)}}
            if season <= 3:
                y = float(row['DM'])
                if not np.isfinite(y):
                    raise ValueError(f'Development assay missing/nonfinite at source row {number}.')
                development.append({**common, 'DM': y})
            else:
                features.append(common)
                labels.append({'row_id': row_id, 'season': season, 'DM': row['DM']})
    for name, rows in [('development.csv', development), ('external_features.csv', features), ('metadata.csv', metadata)]:
        _atomic(base / 'processed' / name, pd.DataFrame(rows).to_csv(index=False, float_format='%.17g').encode())
    # Deliberately use csv writer rather than numeric conversion of external DM.
    label_buffer = io.StringIO(newline='')
    label_writer = csv.DictWriter(label_buffer, fieldnames=['row_id', 'season', 'DM'])
    label_writer.writeheader()
    label_writer.writerows(labels)
    _atomic(base / 'sealed' / 'external_labels.csv', label_buffer.getvalue().encode())
    (base / 'sealed' / 'external_labels.csv').chmod(0o600)
    _atomic(base / 'sealed' / 'README.txt', b'Raw data and external assays. Do not read in training, selection, calibration, or troubleshooting. Only the frozen isolated evaluator may load external_labels.csv. OS permissions alone are not a cryptographic access control.\n')
    md = pd.DataFrame(metadata)
    duplicates = [{'spectrum_sha256': key, 'rows': [{'row_id': r, 'season': s, 'group': g} for r,s,g in items]}
                  for key, items in seen_spectra.items() if len(items) > 1]
    cross_season = [d for d in duplicates if len(set(r['season'] for r in d['rows'])) > 1]
    cross_group = [d for d in duplicates if len(set(r['group'] for r in d['rows'])) > 1]
    # Report metadata-only composition; never any external outcome distribution.
    composition = md.groupby(['season', 'group', 'Cultivar', 'Region', 'Type', 'Temp'], dropna=False).size().rename('scans').reset_index()
    _atomic(base / 'processed' / 'composition.csv', composition.to_csv(index=False).encode())
    audit = {
        'rows_are': 'recorded spectra (scans), not verified unique fruits',
        'scan_count': len(md), 'development_scan_count': len(development),
        'season_scan_counts': {str(s): int(len(g)) for s,g in md.groupby('season')},
        'season_population_counts': {str(s): int(g.group.nunique()) for s,g in md.groupby('season')},
        'season_cultivars': {str(s): sorted(g.Cultivar.unique().tolist()) for s,g in md.groupby('season')},
        'fruit_id_available': False, 'verified_unique_fruit_count': None,
        'grouping': 'source harvest population Pop nested in Season; no identities inferred from assay equality',
        'group_id_format': 's{Season}_pop{Pop}',
        'documented_repeat_scans': 'Provider v6 states duplicate scans and 744 samples at approximately 15, 25 and 35 C; rowwise fruit IDs are absent.',
        'temperature': 'Temp category is supplied (No/Low/Mid/High); no exact per-row temperature.',
        'instrument': 'F750 from original papers; same instrument for season 5 per Walsh thesis; no rowwise serial ID.',
        'cultivar_available': True, 'raw_wavelengths_nm': all_wave, 'comparison_wavelengths_nm': WAVELENGTHS.tolist(),
        'wavelength_discrepancy': 'CSV provides 285 through 1200 nm; v3 page says 309-1149, v4/v6 says 309-149 (typographical). Analysis uses verified common 684-990 nm only.',
        'missing_common_spectrum_rows': invalid,
        'missing_raw_spectral_cells_by_wavelength': {k:v for k,v in all_spectra_missing.items() if v},
        'missing_metadata_cells': {c: int((md[c].astype(str).str.strip() == '').sum()) for c in METADATA},
        'exact_common_spectrum_duplicate_sets': len(duplicates),
        'exact_metadata_and_common_spectrum_extra_rows': sum(v-1 for v in exact_rows.values()),
        'cross_season_exact_spectrum_sets': len(cross_season),
        'cross_group_exact_spectrum_sets': len(cross_group),
        'duplicates': duplicates,
        'external_outcomes_inspected': False,
        'outcome_unit': 'dry-matter percentage of fresh weight; error unit percentage point',
        'preparation': 'Select raw apparent absorbance columns, validate finite common spectrum and population, split by season; no spectral pretreatment or outcome-based external filtering.',
    }
    audit_dir = base.parent / 'results' / 'data_audit'
    _json(audit_dir / 'audit.json', audit)
    _json(audit_dir / 'duplicates.json', {'duplicate_sets': duplicates, 'cross_season_sets': cross_season, 'cross_group_sets': cross_group})
    official_copies = []
    for version, listing in listings.items():
        for item in listing:
            if item['content_details'].get('sha256_hash') == CANONICAL_SHA256:
                official_copies.append({'version': version, 'filename': item['filename'], 'file_id': item['id'], 'sha256': CANONICAL_SHA256})
    artifacts = {str(p.relative_to(base)): sha256(p) for p in [raw, base/'processed/development.csv', base/'processed/external_features.csv', base/'processed/metadata.csv', base/'processed/composition.csv', base/'sealed/external_labels.csv']}
    manifest = {
        'schema_version': 1, 'dataset_doi': SOURCE_DOI,
        'dataset_url': 'https://data.mendeley.com/datasets/46htwnp833/3',
        'official_file': entry, 'official_identical_copies': official_copies,
        'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'raw_sha256': CANONICAL_SHA256, 'source_bytes': raw.stat().st_size,
        'preparation_code_sha256': implementation, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
        'local_override': str(Path(data_path).resolve()) if data_path else None,
        'artifacts': artifacts, 'audit_path': str(audit_dir/'audit.json'),
        'scan_counts': audit['season_scan_counts'], 'population_counts': audit['season_population_counts'],
        'expanded_multi_instrument_release_used': False,
        'external_labels_summarized_or_used_for_preparation_decisions': False,
        'retrieval_failures': retrieval_failures,
    }
    _json(manifest_path, manifest)
    return manifest


def _load_frame(path, base, y=None):
    frame = pd.read_csv(path, float_precision='round_trip')
    md = pd.read_csv(base / 'processed' / 'metadata.csv').set_index('row_id').loc[frame.row_id].reset_index()
    if y is None and 'DM' in frame:
        y = frame.DM.to_numpy(dtype=float)
    return DataSet(frame[[str(w) for w in WAVELENGTHS]].to_numpy(dtype=float), y,
                   frame.season.to_numpy(dtype=int), frame.group.to_numpy(dtype=str),
                   frame.row_id.to_numpy(dtype=str), WAVELENGTHS.copy(), md)


def load_development(data_dir=None):
    base = _data_dir(data_dir)
    if not (base / 'processed' / 'development.csv').exists():
        prepare_data(base)
    data = _load_frame(base / 'processed' / 'development.csv', base)
    if not set(data.seasons).issubset({1, 2, 3}) or data.y is None:
        raise ValueError('Invalid development partition.')
    return data


def load_external_features(season=None, data_dir=None):
    base = _data_dir(data_dir)
    data = _load_frame(base / 'processed' / 'external_features.csv', base)
    if data.y is not None or not set(data.seasons).issubset({4, 5}):
        raise ValueError('External feature partition contains an outcome or invalid season.')
    return data if season is None else data.subset(data.seasons == int(season))


def load_external(season, freeze_manifest, data_dir=None):
    """Explicit scoring-only outcome access after a verified frozen artifact lock."""
    if int(season) not in [4, 5]:
        raise ValueError('External season must be 4 or 5.')
    lock_path = Path(freeze_manifest).resolve()
    lock = json.loads(lock_path.read_text())
    if lock.get('status') != 'frozen':
        raise PermissionError('External assays require manifest status=frozen.')
    hashes = lock.get('hashes', lock.get('artifacts', lock.get('files', {})))
    if not isinstance(hashes, dict) or not hashes:
        raise PermissionError('Frozen manifest must supply artifact hashes.')
    for name, expected in hashes.items():
        expected = expected.get('sha256') if isinstance(expected, dict) else expected
        candidates = [Path(name), ROOT / name, lock_path.parent / name]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None or sha256(path) != expected:
            raise PermissionError(f'Frozen artifact checksum mismatch: {name}')
    base = _data_dir(data_dir)
    data = load_external_features(season, base)
    labels = pd.read_csv(base / 'sealed' / 'external_labels.csv', float_precision='round_trip').set_index('row_id')
    data.y = labels.loc[data.row_ids, 'DM'].to_numpy(dtype=float)
    if not np.isfinite(data.y).all():
        raise ValueError('External assay missing/nonfinite; preserve and report rather than silently impute.')
    access = {'time_utc': datetime.now(timezone.utc).isoformat(), 'season': int(season),
              'freeze_manifest': str(lock_path), 'freeze_manifest_sha256': sha256(lock_path),
              'purpose': 'explicit frozen isolated scoring', 'n_scans': len(data)}
    access_path = base.parent / 'results' / 'data_audit' / 'external_access.jsonl'
    with access_path.open('a') as stream:
        stream.write(json.dumps(access, sort_keys=True) + '\n')
    return data


if __name__ == '__main__':
    result = prepare_data()
    print(json.dumps({'raw_sha256': result['raw_sha256'], 'scan_counts': result['scan_counts'], 'population_counts': result['population_counts']}, indent=2))
