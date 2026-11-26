"""Isolated frozen-model scoring. No fitting or operating-point selection occurs here."""
from __future__ import annotations

import copy
import gzip
import io
import json
import os
import re
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .data import load_external, load_external_features
from .evaluation import choose_on_path, trajectory, visited_calibration
from .metrics import paired_cluster_uncertainty, policy_metrics, regression
from .models import controller_outputs, partial_predict, predict_bank, predict_rich
from .optics import channel_matrix, support_fraction
from .state import ROOT, atomic_json, canonical_hash, digest, event, ledger


ROLE_KEYS = {
    'primary': 'primary_rule', 'accuracy': 'accuracy_rule',
    'adaptive': 'adaptive_error_rule', 'mean': 'mean_season_rule',
    'independent': 'independent_rule',
}
CONTROLS = ['single_cnn_reference', 'uncertainty', 'fixed_order', 'random_order', 'fixed_length', 'lookahead']
OUTPUT_NAMES = [
    'external_predictions.csv', 'external_metrics.csv', 'frozen_curves.csv',
    'external_uncertainty.json', 'calibration.json', 'external_traces.jsonl.gz',
    'external_group_metrics.csv', 'external_gain_distributions.json',
    'external_one_step_diagnostics.csv', 'external_led_usage.csv',
    'external_delta_sensitivity.csv', 'external_sensitivity_exclusions.json',
    'external_evaluation_scope.json', 'action_diagnostics.json',
]


def verify_lock(manifest_path=None):
    """Verify the full frozen manifest and nested input manifests before scoring."""
    manifest_path = Path(manifest_path or ROOT/'results/frozen/manifest.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('status') != 'frozen' or not manifest.get('hashes'):
        raise PermissionError('Scoring requires a nonempty frozen artifact manifest.')
    for name, expected in manifest['hashes'].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            raise PermissionError('Frozen artifact hash differs: ' + name)
    data_manifest = json.loads((ROOT/'data/manifest.json').read_text())
    for name, expected in data_manifest['artifacts'].items():
        path = ROOT/'data'/name
        if not path.is_file() or digest(path) != expected:
            raise PermissionError('Prepared input hash differs: ' + name)
    # Imports execute the checkout copies. Require them to match their locked
    # snapshots, preventing changed runtime code from silently scoring old models.
    for source in (manifest_path.parent/'code').glob('*.py'):
        if source.name in {'reporting.py', 'reporting_diagnostics.py', 'verification.py'}:
            continue
        live = ROOT/source.name if source.name == 'run_project.py' else ROOT/'mango'/source.name
        if live.exists() and digest(live) != digest(source):
            raise PermissionError('Runtime code differs from frozen snapshot: ' + str(live.relative_to(ROOT)))
    catalog = json.loads((manifest_path.parent/'catalog.json').read_text())
    for row in catalog:
        path = ROOT/row['profile_path']
        declared = row.get('profile_sha256', row.get('curve_sha256'))
        if declared is not None and digest(path) != declared:
            raise PermissionError('Digitized optical profile differs: '+row['profile_path'])
    return manifest


def _atomic_csv(path, frame):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    frame.to_csv(temporary, index=False, float_format='%.17g')
    os.replace(temporary, path)


def _clean(value):
    if isinstance(value, dict):
        return {str(k):_clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return _clean(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _cached_prediction(key, dependency, action):
    """Feature-only resumable cache; never contains an external laboratory target."""
    folder = ROOT/'results/external_cache'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/(key+'.joblib')
    meta = folder/(key+'.json')
    if path.exists() and meta.exists():
        record = json.loads(meta.read_text())
        if record.get('dependency') == dependency and record.get('status') == 'complete' and record.get('sha256') == digest(path):
            return joblib.load(path)
    started = time.time()
    ledger({'stage':'external_features_only','key':key,'status':'running','dependency':dependency})
    try:
        value = action()
        temporary = path.with_suffix('.joblib.tmp')
        joblib.dump(value, temporary, compress=3)
        os.replace(temporary,path)
        record = {'dependency':dependency,'status':'complete','sha256':digest(path),
                  'external_outcomes_loaded':False,'elapsed_seconds':time.time()-started}
        atomic_json(meta,record)
        ledger(dict(record,stage='external_features_only',key=key))
        return value
    except BaseException as exc:
        ledger({'stage':'external_features_only','key':key,'status':'failed','error':repr(exc),'dependency':dependency})
        raise


def _thresholds(bundle, method, conf):
    if method == 'uncertainty':
        return list(bundle['uncertainty_thresholds'])
    if method == 'fixed_length':
        return list(range(len(bundle['initial_indices']),len(bundle['bank_indices'])+1))
    return list(conf['probability_threshold_grid'])


def _choice(path, threshold, method):
    return choose_on_path(path, threshold, method,
                          max_pulses=int(threshold) if method == 'fixed_length' else None)


def _summary(values):
    values = np.asarray(values,dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return {'n':0,'mean':None,'quantiles':None,'negative_n':0,'positive_n':0}
    return {'n':int(len(values)), 'mean':float(values.mean()), 'min':float(values.min()), 'max':float(values.max()),
            'quantile_probabilities':[.05,.25,.5,.75,.95],
            'quantiles':np.quantile(values,[.05,.25,.5,.75,.95]).tolist(),
            'negative_n':int((values<0).sum()), 'positive_n':int((values>0).sum()),
            'material_positive_n':int((values>.5).sum())}


def _methods_for(rule, seed, selection):
    methods = ['proposed','single']
    if rule == selection['primary_rule'] and seed == 42:
        methods += CONTROLS
    return methods


def _prepare_feature_predictions(manifest_hash, selection, conf, catalog):
    """Finish all nominal/ideal/perturbed paths before any call to load_external."""
    folder = ROOT/'results/frozen'
    bundles = {}
    for path in sorted(folder.glob('*_seed*.joblib')):
        match = re.fullmatch(r'(.+)_seed(\d+)\.joblib',path.name)
        if match and match.group(1) != 'ideal':
            bundles[(match.group(1),int(match.group(2)))] = joblib.load(path)
    expected_rules = set(selection[k] for k in ROLE_KEYS.values())
    if not expected_rules.issubset({rule for rule,seed in bundles if seed == 42}):
        raise ValueError('A selected role has no frozen seed-42 bundle.')
    static = joblib.load(folder/'static.joblib')
    walsh = joblib.load(folder/'walsh.joblib')
    ideal = joblib.load(folder/'ideal_seed42.joblib')
    scenarios, exclusions = [], []
    for season in [4,5]:
        data = load_external_features(season)
        channels = channel_matrix(data.X,data.wavelengths,catalog)
        dependency = canonical_hash([manifest_hash,season,digest(ROOT/'mango/external.py')])
        for (rule,seed),bundle in bundles.items():
            bankx = channels[:,bundle['bank_indices']]
            methods = _methods_for(rule,seed,selection)
            def predict_nominal(bundle=bundle, bankx=bankx, methods=methods):
                references = {'bank':predict_bank(bundle,bankx), 'rich':predict_rich(bundle,data.X),
                              'cnn':predict_rich(bundle,data.X,'cnn')}
                paths = {}
                for method in methods:
                    path_method = 'fixed_order' if method == 'fixed_length' else method
                    if path_method not in paths:
                        paths[path_method] = trajectory(bundle,bankx,path_method)
                return {'references':references,'paths':paths}
            value = _cached_prediction('s%d_%s_seed%d'%(season,rule,seed),dependency,predict_nominal)
            scenarios.append({'season':season,'rule':rule,'seed':seed,'scenario':'nominal',
                              'bundle':bundle,'data':data,'bankx':bankx,'methods':methods,**value})
        primary = bundles[(selection['primary_rule'],42)]
        bankx = channels[:,primary['bank_indices']]
        def predict_static_only():
            outputs = {}
            for name,obj in static.items():
                x = data.X if obj['family'] == 'ideal' else channels[:,obj['bank_indices']]
                outputs[name] = {'prediction':obj['model'].predict(x[:,obj['indices']]).ravel(),
                                 'pulses':int(obj['pulses']),'family':obj['family'],
                                 'selected_indices':obj['indices']}
            outputs['walsh_adapted'] = {'prediction':walsh.predict(data.X).ravel(), 'pulses':len(data.wavelengths), 'family':'full_grid', 'selected_indices':list(range(len(data.wavelengths)))}
            return outputs
        static_values = _cached_prediction('s%d_static'%season,dependency,predict_static_only)
        scenarios.append({'season':season,'rule':selection['primary_rule'],'seed':42,'scenario':'static',
                          'bundle':primary,'data':data,'bankx':bankx,'static':static_values})
        point_indices = [int(np.argmin(abs(data.wavelengths-c['center_nm']))) for c in catalog]
        idealx = data.X[:,point_indices][:,ideal['bank_indices']]
        def predict_ideal():
            return {'references':{'bank':predict_bank(ideal,idealx),'rich':predict_rich(ideal,data.X),
                                  'cnn':predict_rich(ideal,data.X,'cnn')},
                    'paths':{method:trajectory(ideal,idealx,method) for method in ['proposed','single']}}
        value = _cached_prediction('s%d_ideal'%season,dependency,predict_ideal)
        scenarios.append({'season':season,'rule':selection['primary_rule'],'seed':42,'scenario':'ideal_points',
                          'bundle':ideal,'data':data,'bankx':idealx,'methods':['proposed','single'],**value})
        variations = [('center_minus3',{'center_shift_nm':-3.}),('center_plus3',{'center_shift_nm':3.}),
                      ('width_times0p9',{'width_scale':.9}),('width_times1p1',{'width_scale':1.1}),
                      ('gaussian_approximation',{})]
        installed = [catalog[i] for i in primary['bank_indices']]
        for name,kwargs in variations:
            varied = copy.deepcopy(installed)
            if name == 'gaussian_approximation':
                for row in varied:
                    row['profile_type'] = 'gaussian_approximation'
            fractions = [support_fraction(c,float(data.wavelengths[0]),float(data.wavelengths[-1]),**kwargs) for c in varied]
            failed = [c['id'] for c,fraction in zip(varied,fractions) if fraction+1e-12 < conf['coverage_cutoff']]
            if failed:
                exclusions.append({'season':season,'scenario':name,'status':'support_excluded',
                                   'channels':failed,'support_fractions':dict(zip([c['id'] for c in varied],fractions)),
                                   'cutoff':conf['coverage_cutoff'],
                                   'reason':'Frozen installed bank contains a perturbed profile below the prespecified coverage cutoff; no unsupported renormalization or bank replacement.'})
                continue
            shifted = channel_matrix(data.X,data.wavelengths,varied,**kwargs)
            def predict_variation(shifted=shifted):
                return {'references':{'bank':predict_bank(primary,shifted),'rich':predict_rich(primary,data.X),
                                      'cnn':predict_rich(primary,data.X,'cnn')},
                        'paths':{method:trajectory(primary,shifted,method) for method in ['proposed','single']}}
            value = _cached_prediction('s%d_shift_%s'%(season,name),dependency,predict_variation)
            scenarios.append({'season':season,'rule':selection['primary_rule'],'seed':42,'scenario':name,
                              'bundle':primary,'data':data,'bankx':shifted,'methods':['proposed','single'],**value})
        event('Frozen feature-only predictions ready for external season %d; no assays opened in prediction stage.'%season)
    cache_records = {str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'results/external_cache').glob('*.json')}
    atomic_json(ROOT/'results/external_prediction_freeze.json',{
        'status':'predictions_frozen_before_outcome_access','model_manifest_sha256':manifest_hash,
        'prediction_cache_metadata_hashes':cache_records,'external_outcomes_loaded':False})
    return scenarios,exclusions


def _trace_records(scenario, method, op, path, chosen, references, y, threshold, catalog):
    bundle, data, bankx = scenario['bundle'],scenario['data'],scenario['bankx']
    ids = [catalog[j]['id'] for j in bundle['bank_indices']]
    for i,end in enumerate(chosen['index']):
        states=[]
        for d in range(int(end)+1):
            mask=path['mask'][i,d]
            next_local = None
            if d < int(end):
                added = np.flatnonzero(path['mask'][i,d+1] & ~mask)
                if len(added)!=1:
                    raise AssertionError('Trace does not acquire exactly one new channel.')
                next_local = int(added[0])
            states.append({'pulses':int(mask.sum()),'mask':mask.astype(int).tolist(),
                           'readings':{ids[j]:float(bankx[i,j]) for j in np.flatnonzero(mask)},
                           'prediction':float(path['prediction'][i,d]),
                           'p_stopgain':float(path['probability'][i,d]),
                           'predicted_error':float(path['risk'][i,d]) if np.isfinite(path['risk'][i,d]) else None,
                           'next_led':ids[next_local] if next_local is not None else None,'stop':d==int(end)})
        yield {'row_id':str(data.row_ids[i]),'season':int(scenario['season']),'group':str(data.groups[i]),
               'rule':scenario['rule'],'seed':scenario['seed'],'scenario':scenario['scenario'],
               'method':method,'operating_point':op,'threshold':float(threshold),'trace':states,
               'evaluator_only':{'assay':float(y[i]),'bank_prediction':float(references['bank'][i]),
                                 'rich_prediction':float(references['rich'][i]),'cnn_prediction':float(references['cnn'][i])}}


def _one_step_diagnostics(scenario,method,path,chosen,y):
    """Signed action diagnostics on forced trajectories, separately flagging visited continuations."""
    bundle, bankx, data = scenario['bundle'],scenario['bankx'],scenario['data']
    rows=[]
    objective = 'single_reference' if method == 'single' else 'two_reference'
    for depth in range(path['prediction'].shape[1]-1):
        selected = np.arange(len(y))
        if not len(selected):
            continue
        masks=path['mask'][selected,depth]
        values=bankx[selected]
        _,predicted=controller_outputs(bundle,values,masks,objective)
        actual=np.full(predicted.shape,np.nan)
        partial_error=np.abs(y[selected]-path['prediction'][selected,depth])
        for j in range(masks.shape[1]):
            take=np.flatnonzero(~masks[:,j])
            if len(take):
                updated=masks[take].copy();updated[:,j]=True
                prediction=partial_predict(bundle,values[take],updated)
                actual[take,j]=partial_error[take]-np.abs(y[selected[take]]-prediction)
        chosen_action=np.argmax(path['mask'][selected,depth+1]&~masks,axis=1)
        for r,i in enumerate(selected):
            a=int(chosen_action[r]);unread=np.flatnonzero(~masks[r]);oracle=float(np.nanmax(actual[r]))
            if len(unread)>1 and np.ptp(predicted[r,unread])>0 and np.ptp(actual[r,unread])>0:
                rank=float(spearmanr(predicted[r,unread],actual[r,unread]).statistic)
            else:
                rank=None
            rows.append({'season':scenario['season'],'row_id':str(data.row_ids[i]),'group':str(data.groups[i]),
                         'rule':scenario['rule'],'seed':scenario['seed'],'method':method,
                         'pulses_before':int(masks[r].sum()),'selected_local_channel':a,
                         'actually_visited':bool(chosen['index'][i]>=depth), 'actually_continued':bool(chosen['index'][i]>depth),
                         'predicted_selected_gain':float(predicted[r,a]),'actual_selected_gain':float(actual[r,a]),
                         'actual_selected_gain_positive':bool(actual[r,a]>0),'unread_action_count':len(unread),
                         'action_gain_rank_correlation':rank,'hindsight_best_gain':oracle,
                         'hindsight_selected_regret':oracle-float(actual[r,a]),
                         'scope':'Forced full trajectories; actually_continued distinguishes realized continuation from evaluator-only hypothetical acquisition.'})
    return rows


def score_external():
    started=time.time()
    manifest_path=ROOT/'results/frozen/manifest.json'
    verify_lock(manifest_path)
    manifest_hash=digest(manifest_path)
    completion_path=ROOT/'results/external_completion.json'
    if completion_path.exists():
        complete=json.loads(completion_path.read_text())
        if complete.get('freeze_sha256')!=manifest_hash:
            raise RuntimeError('Existing scored results belong to another lock. Preserve them and version any corrected evaluation.')
        if complete.get('status')=='complete' and all((ROOT/p).is_file() and digest(ROOT/p)==h for p,h in complete['outputs'].items()):
            event('External scoring already complete; verified checksums, no outcome reload or fitting.')
            return complete
    folder=ROOT/'results/frozen'
    selection=json.loads((folder/'selection.json').read_text())
    conf=json.loads((folder/'experiment.json').read_text())
    catalog=json.loads((folder/'catalog.json').read_text())
    ledger({'stage':'external_scoring','status':'running','freeze_sha256':manifest_hash})
    scenarios,exclusions=_prepare_feature_predictions(manifest_hash,selection,conf,catalog)
    # Only now are reference assays parsed. A failed model/trajectory must be
    # repaired before this boundary, and no prediction is fitted after it.
    outcomes={season:load_external(season,manifest_path) for season in [4,5]}
    predictions=[];metric_rows=[];curve_rows=[];group_rows=[];delta_rows=[];one_step=[];usage=[]
    calibration={};gains={};selected_pairs={}
    roles={rule:'|'.join(role for role,key in ROLE_KEYS.items() if selection[key]==rule)
           for rule in set(selection[key] for key in ROLE_KEYS.values())}
    trace_path=ROOT/'results/external_traces.jsonl.gz'
    trace_temp=trace_path.with_suffix(trace_path.suffix+'.tmp')
    raw_trace=trace_temp.open('wb')
    trace_zip=gzip.GzipFile(fileobj=raw_trace,mode='wb',mtime=0,filename='')
    trace_writer=io.TextIOWrapper(trace_zip,encoding='utf-8')
    nominal_refs={}
    for scenario in scenarios:
        if scenario['scenario']=='nominal':
            nominal_refs[(scenario['season'],scenario['rule'],scenario['seed'])]=scenario['references']
    try:
        for scenario in scenarios:
            season,rule,seed,kind=scenario['season'],scenario['rule'],scenario['seed'],scenario['scenario']
            data,bundle=scenario['data'],scenario['bundle']
            target=outcomes[season]
            if not np.array_equal(data.row_ids,target.row_ids):
                raise AssertionError('Frozen prediction and assay row orders differ.')
            y=target.y;capacity=len(bundle['bank_indices'])
            references=scenario.get('references',nominal_refs[(season,rule,seed)])
            base={'season':season,'rule':rule,'roles':roles.get(rule,''),'seed':seed,'scenario':kind}

            def add_selected(method,op,prediction,pulses,threshold=None,path=None,chosen=None):
                key=dict(base,method=method,operating_point=op)
                m=policy_metrics(y,prediction,pulses,references['bank'],references['rich'],capacity,conf['delta'])
                m.update(bank_rmsep=regression(y,references['bank'])['rmsep'],
                         rich_rmsep=regression(y,references['rich'])['rmsep'],cnn_rmsep=regression(y,references['cnn'])['rmsep'])
                metric_rows.append(dict(key,threshold=threshold,**m))
                ep=np.abs(y-prediction);eb=np.abs(y-references['bank']);ef=np.abs(y-references['rich'])
                table=pd.DataFrame({'row_id':data.row_ids,'group':data.groups,'y':y,'prediction':prediction,
                                    'pulses':pulses,'bank_prediction':references['bank'],'rich_prediction':references['rich'],
                                    'cnn_prediction':references['cnn'],'g_stop':ep-eb,'g_bank':eb-ef})
                for name,value in key.items():table[name]=value
                predictions.append(table)
                for group in np.unique(data.groups):
                    take=data.groups==group
                    group_rows.append(dict(key,group=str(group),**policy_metrics(y[take],prediction[take],pulses[take],
                                          references['bank'][take],references['rich'][take],capacity,conf['delta'])))
                for delta in conf.get('sensitivity_deltas',[.25,1.]):
                    delta_rows.append(dict(key,delta=float(delta),**policy_metrics(y,prediction,pulses,
                                      references['bank'],references['rich'],capacity,float(delta))))
                gain_key='|'.join(map(str,[season,rule,seed,kind,method,op]))
                gains[gain_key]={'g_stop':_summary(ep-eb),'g_bank':_summary(eb-ef),
                                'g_stop_early_stops':_summary((ep-eb)[np.asarray(pulses)<capacity])}
                if kind=='nominal' and method in ['proposed','single'] and op=='scientific':
                    selected_pairs[(season,rule,seed,method)]={'prediction':prediction,'pulses':pulses,'bank':references['bank']}
                if path is not None and chosen is not None:
                    if kind=='nominal':
                        for trace in _trace_records(scenario,method,op,path,chosen,references,y,threshold,catalog):
                            trace_writer.write(json.dumps(_clean(trace),sort_keys=True,separators=(',',':'))+'\n')
                    if method!='uncertainty' and method!='fixed_length':
                        correct_reference=references['rich'] if method=='single' else references['cnn'] if method=='single_cnn_reference' else references['bank']
                        calibration[gain_key]=dict(visited_calibration(y,correct_reference,path,chosen,conf['delta']),
                                                  label_reference='rich_cnn' if method=='single_cnn_reference' else 'rich_plsr' if method=='single' else 'bank',
                                                  **key)
                    for depth in range(path['mask'].shape[1]):
                        visited=chosen['index']>=depth
                        if not visited.any():continue
                        previous=np.zeros_like(path['mask'][:,depth]) if depth==0 else path['mask'][:,depth-1]
                        added=path['mask'][:,depth]&~previous
                        for j,candidate in enumerate(bundle['bank_indices']):
                            usage.append(dict(key,depth=int(path['mask'][0,depth].sum()),led_id=catalog[candidate]['id'],
                                              visits=int(visited.sum()),acquisition_count=int((visited&added[:,j]).sum())))
                    if kind=='nominal' and rule==selection['primary_rule'] and seed==42 and method in ['proposed','single'] and op=='scientific':
                        diagnostic=_one_step_diagnostics(scenario,method,path,chosen,y)
                        one_step.extend(diagnostic)
                        gains[gain_key]['g_chosen_next_continued']=_summary([row['actual_selected_gain'] for row in diagnostic if row['actually_continued']])
                return key

            if kind=='static':
                for name,obj in scenario['static'].items():
                    add_selected(name,'reference',np.asarray(obj['prediction']),np.full(len(y),obj['pulses']))
                continue
            for name,pulse in [('bank',capacity),('rich',len(data.wavelengths)),('cnn',len(data.wavelengths))]:
                add_selected({'bank':'full_bank','rich':'rich_pls','cnn':'rich_cnn'}[name],
                             'reference' if kind=='nominal' else 'ideal_reference' if kind=='ideal_points' else 'response_shift_reference',references[name],np.full(len(y),pulse))
            for method in scenario['methods']:
                path=scenario['paths']['fixed_order' if method=='fixed_length' else method]
                thresholds=_thresholds(bundle,method,conf)
                for index,threshold in enumerate(thresholds):
                    chosen=_choice(path,threshold,method)
                    curve_rows.append(dict(base,method=method,threshold_index=index,threshold=float(threshold),
                                           **policy_metrics(y,chosen['predictions'],chosen['pulses'],references['bank'],references['rich'],capacity,conf['delta'])))
                selection_key=('ideal' if kind=='ideal_points' else rule)+'|'+method
                if selection_key not in selection['scientific_operating_indices']:
                    raise ValueError('No development-selected operating index for '+selection_key)
                selected_index=int(selection['scientific_operating_indices'][selection_key])
                selected_threshold=thresholds[selected_index]
                chosen=_choice(path,selected_threshold,method)
                op='scientific' if kind=='nominal' else 'ideal_scientific' if kind=='ideal_points' else 'response_shift'
                add_selected(method,op,chosen['predictions'],chosen['pulses'],float(selected_threshold),path,chosen)
                if kind=='nominal' and rule==selection['primary_rule'] and seed==42 and method=='proposed':
                    engineering_threshold=thresholds[int(selection['engineering_operating_index'])]
                    engineering=_choice(path,engineering_threshold,method)
                    add_selected(method,'engineering',engineering['predictions'],engineering['pulses'],float(engineering_threshold),path,engineering)
            event('Scored frozen outputs: season %d, %s, seed %d, %s.'%(season,rule,seed,kind))
    finally:
        trace_writer.close()
        raw_trace.close()
    os.replace(trace_temp,trace_path)
    uncertainty={}
    for season,rule,seed,method in sorted(selected_pairs):
        if method!='proposed':continue
        a=selected_pairs[(season,rule,seed,'proposed')];b=selected_pairs[(season,rule,seed,'single')]
        data=outcomes[season]
        result=paired_cluster_uncertainty(data.y,a['prediction'],b['prediction'],a['pulses'],b['pulses'],
                                          data.groups,a['bank'],conf['capacity'],seed=seed,n_boot=conf['bootstrap_replicates'])
        gap=float(np.mean(a['pulses'])-np.mean(b['pulses']))
        result.update(season=season,rule=rule,roles=roles.get(rule,''),seed=seed,
                      contrast='proposed_minus_single',operating_point='scientific',
                      achieved_budget_comparable=abs(gap)<=conf['pulse_comparability_margin'],
                      pulse_comparability_margin=conf['pulse_comparability_margin'],
                      interpretation='Negative RMSEP difference favors proposed; a budget gap outside the frozen margin makes an isolated efficiency claim inconclusive. Frozen curves supplied; no external threshold tuning.')
        uncertainty['%d|%s|%d'%(season,rule,seed)]=result
    frames={'external_predictions.csv':pd.concat(predictions,ignore_index=True),
            'external_metrics.csv':pd.DataFrame(metric_rows),'frozen_curves.csv':pd.DataFrame(curve_rows),
            'external_group_metrics.csv':pd.DataFrame(group_rows),'external_one_step_diagnostics.csv':pd.DataFrame(one_step),
            'external_led_usage.csv':pd.DataFrame(usage),'external_delta_sensitivity.csv':pd.DataFrame(delta_rows)}
    key_columns=['season','rule','seed','scenario','method','operating_point','row_id']
    if frames['external_predictions.csv'].duplicated(key_columns).any():
        raise AssertionError('Duplicate scored prediction keys detected.')
    for name,frame in frames.items():
        _atomic_csv(ROOT/'results'/name,frame)
    atomic_json(ROOT/'results/external_uncertainty.json',_clean(uncertainty))
    atomic_json(ROOT/'results/calibration.json',_clean(calibration))
    atomic_json(ROOT/'results/external_gain_distributions.json',_clean(gains))
    diagnostics = pd.DataFrame(one_step)
    action_summary = []
    if len(diagnostics):
        for scope_name, scoped in [('forced_full_trajectory',diagnostics), ('visited_continuations',diagnostics[diagnostics.actually_continued])]:
            for (season, method, depth), group in scoped.groupby(['season','method','pulses_before']):
                predicted = group.predicted_selected_gain.to_numpy()
                actual = group.actual_selected_gain.to_numpy()
                variable = len(group)>1 and np.ptp(predicted)>0 and np.ptp(actual)>0
                action_summary.append({'season':int(season),'method':method,'pulses_before':int(depth),
                    'scope':scope_name,'n':len(group), 'predicted_mean':float(predicted.mean()),
                    'actual_mean':float(actual.mean()), 'mae':float(np.mean(np.abs(predicted-actual))),
                    'pearson':float(np.corrcoef(predicted,actual)[0,1]) if variable else None,
                    'spearman':float(spearmanr(predicted,actual).statistic) if variable else None,
                    'sign_agreement':float(np.mean((predicted>0)==(actual>0))),
                    'actual_improvement_fraction':float(np.mean(actual>0)),
                    'actual_material_improvement_fraction':float(np.mean(actual>.5)),
                    'mean_action_rank_correlation':float(group.action_gain_rank_correlation.mean()) if group.action_gain_rank_correlation.notna().any() else None,
                    'hindsight_regret_mean':float(group.hindsight_selected_regret.mean())})
    atomic_json(ROOT/'results/action_diagnostics.json',_clean({'rows':action_summary,
        'scope':'Predictors and action choices frozen. Forced future actions are evaluator-only diagnostics; visited continuation summaries describe choices actually taken.'}))

    atomic_json(ROOT/'results/external_sensitivity_exclusions.json',_clean(exclusions))
    scope={'fit_calls_in_evaluator':0,'prediction_cache_before_outcomes':True,'primary_scenario':'nominal',
           'point_sensitivity':'Separate frozen point-channel predictor/controller at nearest 3-nm channels to physical nominal centers. Own operating indices selected using three outer development folds at the same four-reading target.',
           'profile_sensitivity':'Deployment response shift through the same frozen physical model, scaler, calibration and threshold; no retraining. Uniform center and width changes separately. Gaussian approximation separately labeled.',
           'trace_boundaries':'Decision states contain acquired channel readings only. Assays and unattained reference predictions are exclusively in evaluator_only.',
           'seed_variability':'Seeds 7/42/99 retained separately; primary inferential seed 42. Cluster uncertainty is not seed variability.',
           'lookahead':'Frozen training-only conditional two-step approximation, not author ACO replication.',
           'large_absolute_error_definition':conf['large_absolute_error_threshold'],
           'season5_intervals':'Population intervals suppressed for two harvest populations; group-specific paired estimates supplied.',
           'static_models':'Fixed physical budgets 4/8 and ideal budgets 4/8/16 from frozen development-only sparse selection; units differ between finite-band LEDs and point wavelengths.'}
    atomic_json(ROOT/'results/external_evaluation_scope.json',scope)
    verify_lock(manifest_path)
    outputs={str((ROOT/'results'/name).relative_to(ROOT)):digest(ROOT/'results'/name) for name in OUTPUT_NAMES}
    outputs['results/external_prediction_freeze.json']=digest(ROOT/'results/external_prediction_freeze.json')
    complete={'status':'complete','freeze_sha256':manifest_hash,'outputs':outputs,
              'elapsed_seconds':time.time()-started,'prediction_rows':len(frames['external_predictions.csv']),
              'metric_rows':len(frames['external_metrics.csv']),'curve_rows':len(frames['frozen_curves.csv']),
              'external_seasons':[4,5],'no_training_or_selection_calls':True}
    atomic_json(completion_path,complete)
    ledger(dict(complete,stage='external_scoring'))
    event('Isolated external scoring complete; all outputs atomically replaced and checksummed.')
    return complete
