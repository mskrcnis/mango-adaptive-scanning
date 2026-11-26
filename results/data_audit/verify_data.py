"""Executed data-boundary checks; never opens external assay content."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

from mango.data import ROOT, load_development, load_external, load_external_features, prepare_data, sha256


def run():
    checks = {}
    original_read = pd.read_csv

    def guarded_read(path, *args, **kwargs):
        assert 'sealed' not in Path(path).parts, 'Training/feature reader attempted sealed access'
        return original_read(path, *args, **kwargs)

    with patch('pandas.read_csv', guarded_read):
        data = load_development()
        external = load_external_features()
    checks['development_and_feature_readers_do_not_open_sealed_files'] = True
    checks['external_features_have_no_target'] = external.y is None
    checks['common_grid_103_and_exact_units'] = np.array_equal(data.wavelengths, np.arange(684, 991, 3))
    checks['development_seasons_exactly_1_2_3'] = set(data.seasons) == {1, 2, 3}
    checks['external_seasons_exactly_4_5'] = set(external.seasons) == {4, 5}
    checks['development_external_groups_disjoint'] = not set(data.groups) & set(external.groups)
    checks['source_rows_unique'] = len(set(data.row_ids) | set(external.row_ids)) == len(data) + len(external)
    for season in [1, 2, 3]:
        train = np.flatnonzero(data.seasons != season)
        test = np.flatnonzero(data.seasons == season)
        assert not set(data.groups[train]) & set(data.groups[test])
        split = GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42)
        fit, cal = next(split.split(data.X[train], groups=data.groups[train]))
        assert not set(data.groups[train[fit]]) & set(data.groups[train[cal]])
        for fit_fold, validation_fold in GroupKFold(n_splits=3).split(data.X[train[fit]], groups=data.groups[train[fit]]):
            assert not set(data.groups[train[fit][fit_fold]]) & set(data.groups[train[fit][validation_fold]])
    checks['repeat_population_groups_do_not_cross_outer_inner_or_calibration_splits'] = True
    for status, hashes in [('draft', {'README.md':'invalid'}), ('frozen', {}), ('frozen', {'nonexistent.model':'invalid'})]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_text(json.dumps({'status':status, 'hashes':hashes}))
            try:
                with patch('pandas.read_csv', guarded_read):
                    load_external(4, path)
            except PermissionError:
                pass
            else:
                raise AssertionError('External outcomes accepted an invalid freeze manifest')
    checks['external_outcomes_reject_draft_empty_and_invalid_locks'] = True
    before = json.loads((ROOT/'data/manifest.json').read_text())
    returned = prepare_data()
    after = json.loads((ROOT/'data/manifest.json').read_text())
    checks['resume_does_not_change_prepared_artifacts_or_manifest'] = before == after == returned
    checks['all_prepared_hashes_verified'] = all(sha256(ROOT/'data'/name) == value for name,value in after['artifacts'].items())
    audit = json.loads((ROOT/'results/data_audit/audit.json').read_text())
    checks['no_exact_spectra_cross_partitions'] = audit['cross_season_exact_spectrum_sets'] == 0 and audit['cross_group_exact_spectrum_sets'] == 0
    assert all(checks.values()), checks
    output = {'command': '.venv/bin/python -m results.data_audit.verify_data', 'checks':checks, 'status':'passed', 'external_outcomes_opened':False}
    (ROOT/'results/data_audit/verification.json').write_text(json.dumps(output,indent=2)+'\n')
    return output


if __name__ == '__main__':
    print(json.dumps(run(),indent=2))
