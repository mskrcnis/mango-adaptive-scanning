"""Descriptive reporting from frozen outputs; no model fitting or new selection."""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .state import ROOT, atomic_json, digest


ROLE_KEYS = {'primary': 'primary_rule', 'full_bank_accuracy': 'accuracy_rule',
             'adaptive_error': 'adaptive_error_rule', 'mean_season': 'mean_season_rule',
             'independent_catalog': 'independent_rule'}
ARTIFACTS = ['selected_bank_parts.csv', 'calibrator_summary.json', 'paired_examples.json',
             'paired_examples.csv', 'reference_agreement_errors.json',
             'reference_agreement_errors.csv', 'diagnostic_summary.md']


def _csv(path, records):
    temporary = path.with_suffix(path.suffix + '.tmp')
    pd.DataFrame(records).to_csv(temporary, index=False, float_format='%.17g')
    os.replace(temporary, path)


def _rate(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def agreement_errors(predictions, delta=.5, large_error=2.):
    """Retrospective fixed-definition diagnostic, retaining every scored group."""
    keys = ['season', 'rule', 'seed', 'scenario', 'method', 'operating_point']
    rows = []
    for identity, frame in predictions.groupby(keys, sort=True):
        y, p, b, f = [frame[c].to_numpy(float) for c in ['y', 'prediction', 'bank_prediction', 'rich_prediction']]
        agree = np.abs(b - f) <= delta
        triple = np.max(np.column_stack([p, b, f]), axis=1) - np.min(np.column_stack([p, b, f]), axis=1) <= delta
        large = np.abs(y - p) > large_error
        row = dict(zip(keys, identity))
        row['season'], row['seed'] = int(row['season']), int(row['seed'])
        row.update(n=len(frame), reference_agreement_n=int(agree.sum()),
                   reference_agreement_fraction=float(agree.mean()),
                   large_absolute_error_n=int(large.sum()), large_absolute_error_rate=float(large.mean()),
                   large_error_with_reference_agreement_n=int((large & agree).sum()),
                   large_error_with_reference_agreement_unconditional_rate=float((large & agree).mean()),
                   large_error_given_reference_agreement_rate=_rate((large & agree).sum(), agree.sum()),
                   three_prediction_agreement_n=int(triple.sum()),
                   large_error_with_three_prediction_agreement_n=int((large & triple).sum()),
                   large_error_given_three_prediction_agreement_rate=_rate((large & triple).sum(), triple.sum()),
                   both_reference_errors_large_and_agree_n=int((agree & (np.abs(y-b)>large_error) &
                                                               (np.abs(y-f)>large_error)).sum()))
        rows.append(row)
    return rows


def _select_examples(predictions, diagnostics, selection, delta):
    primary = predictions[(predictions.rule == selection['primary_rule']) & (predictions.seed == 42) &
                          (predictions.scenario == 'nominal') & (predictions.operating_point == 'scientific') &
                          (predictions.method == 'proposed')].copy()
    records = []
    for season in [4, 5]:
        frame = primary[primary.season == season]
        for category, column, condition in [
                ('premature_stop', 'g_stop', (frame.pulses < 8) & (frame.g_stop > delta)),
                ('full_bank_limitation', 'g_bank', frame.g_bank > delta)]:
            candidates = frame[condition].copy()
            record = {'season': season, 'category': category, 'candidate_count': len(candidates),
                      'selection_rule': 'Qualifying event nearest within-season median gain; row ID breaks ties.'}
            if len(candidates):
                median = float(candidates[column].median())
                chosen = candidates.assign(distance=abs(candidates[column]-median)).sort_values(['distance', 'row_id']).iloc[0]
                record.update(status='selected', row_id=str(chosen.row_id), selected_gain=float(chosen[column]),
                              qualifying_event_median_gain=median)
            else:
                record.update(status='no_qualifying_event', row_id=None)
            records.append(record)
        continued = diagnostics.actually_continued.astype(str).str.lower().isin(['true', '1'])
        candidates = diagnostics[(diagnostics.season == season) & (diagnostics.rule == selection['primary_rule']) &
                                 (diagnostics.seed == 42) & (diagnostics.method == 'proposed') & continued &
                                 (diagnostics.actual_selected_gain > delta)].copy()
        record = {'season': season, 'category': 'useful_continuation', 'candidate_count': len(candidates),
                  'selection_rule': 'Actually continued material improvement nearest within-season median; row ID/depth break ties.'}
        if len(candidates):
            median = float(candidates.actual_selected_gain.median())
            chosen = candidates.assign(distance=abs(candidates.actual_selected_gain-median)).sort_values(
                ['distance', 'row_id', 'pulses_before']).iloc[0]
            record.update(status='selected', row_id=str(chosen.row_id), pulses_before=int(chosen.pulses_before),
                          selected_gain=float(chosen.actual_selected_gain), qualifying_event_median_gain=median,
                          selected_local_channel=int(chosen.selected_local_channel))
        else:
            record.update(status='no_qualifying_event', row_id=None)
        records.append(record)
    return records


def _pair_examples(records, predictions, trace_path, primary_rule):
    selected = {(r['season'], r['row_id']) for r in records if r['status'] == 'selected'}
    traces = {}
    with gzip.open(trace_path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if ((row['season'], row['row_id']) in selected and row['rule'] == primary_rule and
                    row['seed'] == 42 and row['scenario'] == 'nominal' and row['operating_point'] == 'scientific' and
                    row['method'] in ['proposed', 'single']):
                traces[(row['season'], row['row_id'], row['method'])] = row['trace']
    matched = predictions[(predictions.rule == primary_rule) & (predictions.seed == 42) &
                          (predictions.scenario == 'nominal') & (predictions.operating_point == 'scientific') &
                          predictions.method.isin(['proposed', 'single'])]
    for record in records:
        if record['status'] != 'selected': continue
        frame = matched[(matched.season == record['season']) & (matched.row_id == record['row_id'])]
        if len(frame) != 2 or set(frame.method) != {'proposed', 'single'}:
            raise AssertionError('Paired example is missing one method for ' + record['row_id'])
        proposed = frame[frame.method == 'proposed'].iloc[0]
        single = frame[frame.method == 'single'].iloc[0]
        if proposed.y != single.y: raise AssertionError('Paired example assay mismatch.')
        record.update(group=str(proposed['group']), assay=float(proposed.y),
                      proposed_prediction=float(proposed.prediction), single_prediction=float(single.prediction),
                      proposed_pulses=int(proposed.pulses), single_pulses=int(single.pulses),
                      proposed_absolute_error=float(abs(proposed.y-proposed.prediction)),
                      single_absolute_error=float(abs(single.y-single.prediction)),
                      bank_prediction=float(proposed.bank_prediction), rich_prediction=float(proposed.rich_prediction),
                      g_stop=float(proposed.g_stop), g_bank=float(proposed.g_bank),
                      interpretation='Evaluator-only illustrative pairing; selected by a fixed descriptive rule, not inferential evidence.')
        record['traces'] = {method: traces.get((record['season'], record['row_id'], method), [])
                            for method in ['proposed', 'single']}
        if record['category'] != 'useful_continuation': continue
        before = next((s for s in record['traces']['proposed'] if s['pulses'] == record['pulses_before']), None)
        after = next((s for s in record['traces']['proposed'] if s['pulses'] == record['pulses_before'] + 1), None)
        if before is None or after is None:
            record.update(continuation_states_available=False,
                          continuation_state_limit='Before/after saved states unavailable; no missing prediction was imputed.')
            continue
        actual_gain = abs(record['assay']-before['prediction']) - abs(record['assay']-after['prediction'])
        if abs(actual_gain-record['selected_gain']) > 1e-8:
            raise AssertionError('Saved useful-continuation gain differs from its before/after trace.')
        record.update(continuation_states_available=True, next_led=before['next_led'],
                      prediction_before=float(before['prediction']), prediction_after=float(after['prediction']),
                      absolute_error_before=float(abs(record['assay']-before['prediction'])),
                      absolute_error_after=float(abs(record['assay']-after['prediction'])),
                      recomputed_actual_one_step_gain=float(actual_gain))
        paired = next((s for s in record['traces']['single'] if s['pulses'] == record['pulses_before']), None)
        record['single_prediction_at_same_depth'] = None if paired is None else float(paired['prediction'])
        record['single_same_depth_note'] = ('Single-reference policy did not reach this depth; no hypothetical state is shown.'
                                            if paired is None else 'Actual visited state; channel masks may differ between policies.')
    return records


def generate_diagnostics(root=None):
    """Create reporting-only summaries after completed, checksummed scoring."""
    base = ROOT if root is None else Path(root)
    def read(name): return json.loads((base / name).read_text())
    manifest_path = base / 'results/frozen/manifest.json'
    manifest, completion = read('results/frozen/manifest.json'), read('results/external_completion.json')
    if manifest.get('status') != 'frozen' or completion.get('status') != 'complete':
        raise RuntimeError('Descriptive diagnostics require completed frozen scoring.')
    if completion['freeze_sha256'] != digest(manifest_path):
        raise RuntimeError('Diagnostics inputs have mismatched freeze and scoring records.')
    inputs = ['results/external_predictions.csv', 'results/external_one_step_diagnostics.csv',
              'results/external_traces.jsonl.gz']
    for name in inputs:
        if digest(base / name) != completion['outputs'].get(name):
            raise RuntimeError('Scored diagnostic source changed: ' + name)
    def frozen(name):
        relative = 'results/frozen/' + name
        if digest(base / relative) != manifest['hashes'].get(relative):
            raise RuntimeError('Frozen reporting input changed: ' + relative)
        return base / relative
    selection = json.loads(frozen('selection.json').read_text())
    catalog = json.loads(frozen('catalog.json').read_text())
    configuration = json.loads(frozen('experiment.json').read_text())
    delta, large = float(configuration['delta']), float(configuration['large_absolute_error_threshold'])
    membership, calibrators, models = [], [], {}
    for role, selection_key in ROLE_KEYS.items():
        rule = selection[selection_key]
        if rule not in models: models[rule] = joblib.load(frozen(rule + '_seed42.joblib'))
        bundle = models[rule]
        for position, index in enumerate(bundle['bank_indices']):
            part = catalog[index]
            membership.append({'role': role, 'rule': rule, 'seed': 42, 'installed_position': position,
                               'catalog_index': int(index), 'initial_reading': position in bundle['initial_indices'],
                               'part_id': part['id'], 'manufacturer': part['manufacturer'],
                               'nominal_center_nm': part['center_nm'], 'nominal_fwhm_nm': part['fwhm_nm'],
                               'digitized_peak_nm': part['digitized_peak_nm'],
                               'digitized_fwhm_nm': part['digitized_fwhm_nm'],
                               'modeled_support_fraction': part['support_fraction'],
                               'profile_type': part['profile_type'], 'source_url': part['source'],
                               'source_sha256': part['source_sha256'], 'profile_sha256': part['profile_sha256']})
    for rule, bundle in sorted(models.items()):
        for objective, record in bundle['calibration_records'].items():
            method = {'two_reference': 'proposed', 'single_reference': 'single'}.get(objective, objective)
            index = selection['scientific_operating_indices'].get(rule + '|' + method)
            calibrators.append({'rule': rule, 'seed': 42, 'objective': objective,
                                'calibration_groups': bundle['calibration_groups'],
                                'scientific_threshold_index': index,
                                'scientific_threshold': None if index is None else configuration['probability_threshold_grid'][index],
                                **record})
    predictions = pd.read_csv(base / inputs[0], float_precision='round_trip')
    diagnostics = pd.read_csv(base / inputs[1], float_precision='round_trip')
    examples = _pair_examples(_select_examples(predictions, diagnostics, selection, delta), predictions,
                              base / inputs[2], selection['primary_rule'])
    agreement = agreement_errors(predictions, delta, large)
    definitions = {
        'scope': 'Retrospective descriptive diagnostics from frozen predictions; no fitting, threshold selection or outcome-driven change.',
        'reference_agreement': '|bank prediction - rich PLS prediction| <= %.8g pp' % delta,
        'three_prediction_agreement': 'max(policy, bank, rich PLS) - min(policy, bank, rich PLS) <= %.8g pp' % delta,
        'large_error': '|assay - policy prediction| > %.8g pp' % large,
        'unconditional_rate': 'Joint event count divided by all scans in the corresponding scored comparison.',
        'conditional_rate': 'Joint event count divided by scans satisfying the stated agreement definition; null for zero denominator.',
        'interpretation': 'Agreement between learned references does not establish accuracy. These auxiliary summaries are not new primary estimands or evidence for recalibration.'}
    folder = base / 'results'
    _csv(folder / 'selected_bank_parts.csv', membership)
    atomic_json(folder / 'calibrator_summary.json', {'scope': 'Disjoint training-calibration fit diagnostics, not held-out calibration performance.', 'rows': calibrators})
    atomic_json(folder / 'paired_examples.json', {'scope': definitions['scope'], 'rows': examples})
    _csv(folder / 'paired_examples.csv', [{k: v for k, v in row.items() if k != 'traces'} for row in examples])
    atomic_json(folder / 'reference_agreement_errors.json', {'definitions': definitions, 'rows': agreement})
    _csv(folder / 'reference_agreement_errors.csv', agreement)
    lines = ['# Frozen-output diagnostic summaries', '', definitions['scope'], '',
             '## Large errors despite reference agreement', '',
             definitions['reference_agreement'] + '; ' + definitions['large_error'] + '.', '',
             '| Season | Method | All scans | Reference agreement | Large errors within agreement | Conditional rate | Unconditional joint rate |',
             '|---|---|---:|---:|---:|---:|---:|']
    for row in agreement:
        if (row['rule'] == selection['primary_rule'] and row['seed'] == 42 and row['scenario'] == 'nominal' and
                row['method'] in ['proposed', 'single'] and row['operating_point'] == 'scientific'):
            rate = row['large_error_given_reference_agreement_rate']
            lines.append('| %d | %s | %d | %d | %d | %s | %.4f |' %
                         (row['season'], row['method'], row['n'], row['reference_agreement_n'],
                          row['large_error_with_reference_agreement_n'], 'undefined' if rate is None else '%.4f' % rate,
                          row['large_error_with_reference_agreement_unconditional_rate']))
    lines += ['', 'The CSV/JSON retain every scored comparison and a separate stricter three-prediction agreement definition. These descriptions do not imply that agreement is a safe stopping rule.',
              '', '## Paired examples', '',
              'Each category uses the qualifying event nearest its within-season median gain, with row ID/depth tie-breaks. A missing category is reported as no qualifying event. Useful continuations must have actually occurred; missing single-policy depths are not imputed.', '',
              '| Season | Category | Scan | Proposed / single final estimate | Proposed / single readings | Before / after actual continuation |',
              '|---|---|---|---|---|---|']
    for row in examples:
        if row['status'] != 'selected':
            lines.append('| %d | %s | No qualifying event | — | — | — |' % (row['season'], row['category']))
            continue
        continuation = ('%.3f / %.3f' % (row['prediction_before'], row['prediction_after'])
                        if row.get('continuation_states_available') else 'Not applicable' if row['category'] != 'useful_continuation'
                        else 'Saved states unavailable')
        lines.append('| %d | %s | %s | %.3f / %.3f | %d / %d | %s |' %
                     (row['season'], row['category'], row['row_id'], row['proposed_prediction'], row['single_prediction'],
                      row['proposed_pulses'], row['single_pulses'], continuation))
    lines += ['', 'The JSON supplies assays, bank/rich references, signed gaps and both actual traces; all are evaluator-only diagnostics. These selected examples illustrate mechanisms and cannot establish average efficacy.',
              '', '## Exact bank membership and calibration', '',
              '`selected_bank_parts.csv` lists every role, its final seed-42 bank, installed position, initial-reading flag, real part ID, nominal and digitized center/width, modeled support, and source/profile hashes. The role assignments are development-selected.',
              '', '`calibrator_summary.json` preserves the isotonic knots, sample/state counts, positive-label frequency, fitting Brier scores and selected scientific threshold for each final role bank. These are training-calibration diagnostics; external visited-state reliability remains in `calibration.json`.',
              '', 'No physical spectrum, detector noise, energy or timing has been measured by this report.']
    (folder / 'diagnostic_summary.md').write_text('\n'.join(lines) + '\n')
    return {'status': 'generated', 'artifacts': ['results/' + name for name in ARTIFACTS],
            'paired_example_rows': len(examples), 'reference_agreement_rows': len(agreement),
            'bank_part_rows': len(membership), 'definitions': definitions}
