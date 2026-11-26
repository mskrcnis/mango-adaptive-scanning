"""Bounded development search, calibration, immutable lock, and full workflow."""
import copy
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from .state import ROOT, atomic_json, canonical_hash, checkpoint, digest, environment, event
from .data import load_development, prepare_data
from .optics import channel_matrix, get_catalog
from .models import predict_bank, predict_rich
from .training import DEFAULT_CONFIG, fit_bundle
from .evaluation import trajectory, calibrate, choose_on_path
from .metrics import policy_metrics, regression


def configuration():
    return json.loads((ROOT/'config/experiment.json').read_text())


def bank_rules(channels, y, capacity=8):
    n=channels.shape[1]
    if n<=capacity:
        raise RuntimeError('Preregistered hardware search needs more eligible profiles than bank slots.')
    uniform=sorted(set(np.round(np.linspace(0,n-1,capacity)).astype(int)))
    corr=np.abs(np.nan_to_num(np.corrcoef(channels.T,y)[-1,:-1]))
    top=sorted(np.argsort(-corr,kind='stable')[:capacity].tolist())
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    coef=np.abs(Ridge(alpha=10).fit(StandardScaler().fit_transform(channels),y).coef_)
    ridge=sorted(np.argsort(-coef,kind='stable')[:capacity].tolist())
    return {'uniform':uniform,'swap_low':[0,1,2,3,4,6,8,9],
            'swap_mid':[0,2,3,4,5,7,8,9], 'swap_high':[0,1,2,4,5,6,7,9],
            'correlation':top,'ridge':ridge}


def split_indices(data, held_season=None):
    available=np.arange(len(data)) if held_season is None else np.flatnonzero(data.seasons!=held_season)
    splitter=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=31415)
    a,b=next(splitter.split(available,groups=data.groups[available]))
    pool,cal=available[a],available[b]
    design_split=GroupShuffleSplit(n_splits=1,test_size=.15,random_state=2718)
    train_id,_=next(design_split.split(pool,groups=data.groups[pool]))
    fit=pool[train_id]
    valid=np.flatnonzero(data.seasons==held_season) if held_season is not None else np.empty(0,dtype=int)
    assert not set(data.groups[fit])&set(data.groups[cal])
    assert not (set(data.groups[fit])|set(data.groups[cal]))&set(data.groups[valid])
    return fit,cal,valid


def design_indices(data,held_season=None):
    fit,cal,valid=split_indices(data,held_season)
    available=np.arange(len(data)) if held_season is None else np.flatnonzero(data.seasons!=held_season)
    design=np.setdiff1d(available,np.concatenate([fit,cal]))
    assert not set(data.groups[design])&(set(data.groups[fit])|set(data.groups[cal])|set(data.groups[valid]))
    return design


def model_settings():
    settings=dict(DEFAULT_CONFIG)
    settings.update(group_equal_weight=False,threads=4)
    return settings


def registration(data,catalog):
    assignments=[]
    for fold in [1,2,3,None]:
        fit,cal,valid=split_indices(data,fold)
        assignments.append({'held_season':fold,'fit_row_ids':data.row_ids[fit].tolist(),
                            'bank_design_row_ids':data.row_ids[design_indices(data,fold)].tolist(),
                            'bank_design_groups':sorted(set(data.groups[design_indices(data,fold)])),
                            'calibration_row_ids':data.row_ids[cal].tolist(),'validation_row_ids':data.row_ids[valid].tolist(),
                            'fit_groups':sorted(set(data.groups[fit])), 'calibration_groups':sorted(set(data.groups[cal])),
                            'validation_groups':sorted(set(data.groups[valid]))})
    atomic_json(ROOT/'results/fold_assignments.json',assignments)
    record={'status':'registered','configuration':configuration(),'model_settings':model_settings(),
            'catalog':catalog,'data_manifest_sha256':digest(ROOT/'data/manifest.json'),
            'fold_assignments_sha256':digest(ROOT/'results/fold_assignments.json'),
            'protocol_sha256':digest(ROOT/'docs/protocol.md'),
            'models_sha256':digest(ROOT/'mango/models.py'),'training_sha256':digest(ROOT/'mango/training.py')}
    record['optics_code_sha256']=digest(ROOT/'mango/optics.py')
    record['bank_design_amendment']='Reserve 15% of non-calibration training groups, seed2718, exclusively for supervised bank construction; never use their rows in controller target cross-fitting.'
    lock=ROOT/'results/protocol_lock.json'
    if lock.exists():
        old=json.loads(lock.read_text())
        if canonical_hash(old)!=canonical_hash(record):
            if (ROOT/'results/frozen/manifest.json').exists():
                raise RuntimeError('Registered development dependencies changed after external freeze; preserve original run.')
            shutil.copy2(lock,ROOT/'results/attempts'/('protocol_before_'+str(int(time.time()))+'.json'))
            event('Protocol dependency amendment before external scoring; previous registration retained.')
    atomic_json(lock,record)
    return canonical_hash(record)


def fit_calibrated(data,channels,fit,cal,indices,seed,settings):
    bundle=fit_bundle(channels[fit],data.X[fit],data.y[fit],data.groups[fit],indices,seed=seed,config=settings)
    bundle=calibrate(bundle,channels[cal][:,indices],data.X[cal],data.y[cal])
    bundle['fit_row_ids']=data.row_ids[fit]
    bundle['calibration_row_ids']=data.row_ids[cal]
    bundle['fit_groups']=np.unique(data.groups[fit]).tolist()
    bundle['calibration_groups']=np.unique(data.groups[cal]).tolist()
    return bundle


def bundle_key(fold,rule,seed):
    return 'model_%s_%s_seed%d'%('final' if fold is None else 'season%d'%fold,rule,seed)


def get_bundle(data,channels,fold,rule,seed,dependency):
    fit,cal,valid=split_indices(data,fold)
    design=design_indices(data,fold)
    indices=bank_rules(channels[design],data.y[design])[rule]
    fingerprint=canonical_hash([dependency,fold,rule,seed,indices,model_settings()])
    key=bundle_key(fold,rule,seed)
    bundle=checkpoint(key,fingerprint,lambda:fit_calibrated(data,channels,fit,cal,indices,seed,model_settings()))
    return bundle,fingerprint,valid


def score_development(data,channels,bundle,valid,rule,fold,seed,fingerprint,methods):
    conf=configuration()
    bankx=channels[valid][:,bundle['bank_indices']]
    y=data.y[valid]
    bank=predict_bank(bundle,bankx)
    rich=predict_rich(bundle,data.X[valid])
    cnn=predict_rich(bundle,data.X[valid],'cnn')
    base={'bank_rmsep':regression(y,bank)['rmsep'],'rich_rmsep':regression(y,rich)['rmsep'],
          'cnn_rmsep':regression(y,cnn)['rmsep'],'rule':rule,'fold':fold,'seed':seed,
          'bank_indices':','.join(map(str,bundle['bank_indices']))}
    rows=[]
    for method in methods:
        path=checkpoint('path_s%d_%s_%s_seed%d'%(fold,rule,method,seed),
                        canonical_hash([fingerprint,method,digest(ROOT/'mango/evaluation.py')]),
                        lambda:trajectory(bundle,bankx,'fixed_order' if method=='fixed_length' else method))
        thresholds=bundle['uncertainty_thresholds'] if method=='uncertainty' else conf['probability_threshold_grid']
        if method=='fixed_length':thresholds=list(range(2,9))
        for ti,threshold in enumerate(thresholds):
            chosen=choose_on_path(path,threshold,method,max_pulses=threshold if method=='fixed_length' else None)
            m=policy_metrics(y,chosen['predictions'],chosen['pulses'],bank,rich,8)
            rows.append(dict(base,method=method,threshold_index=ti,threshold=float(threshold),**m))
    return rows


def aggregate(frame):
    rows=[]
    for (rule,method,ti),g in frame.groupby(['rule','method','threshold_index'],sort=True):
        misses=g['missed_rate'].fillna(np.inf)
        violations=np.maximum.reduce([misses.to_numpy()/.1,g.bank_loss_rate.to_numpy()/.1,
                                     np.maximum((g.rmsep-g.rich_rmsep).to_numpy(),0)/.25,g.mean_pulses.to_numpy()/4])
        rows.append({'rule':rule,'method':method,'threshold_index':int(ti),
                     'mean_pulses':float(g.mean_pulses.mean()),'worst_rmsep':float(g.rmsep.max()),
                     'mean_rmsep':float(g.rmsep.mean()),'worst_missed_rate':float(misses.max()),
                     'worst_bank_loss_rate':float(g.bank_loss_rate.max()),
                     'max_normalized_violation':float(np.max(violations)), 'feasible':bool(np.max(violations)<=1),
                     'bank_worst_rmsep':float(g.bank_rmsep.max()),'bank_mean_rmsep':float(g.bank_rmsep.mean())})
    return pd.DataFrame(rows)


def select(frame):
    agg=aggregate(frame[frame.seed==42])
    proposed=agg[agg.method=='proposed'].copy()
    feasible=proposed[proposed.feasible]
    if len(feasible):
        eng=feasible.sort_values(['mean_pulses','worst_rmsep','rule','threshold_index']).iloc[0]
    else:
        eng=proposed.sort_values(['max_normalized_violation','worst_rmsep','mean_pulses','rule','threshold_index']).iloc[0]
    bank=proposed.sort_values(['bank_worst_rmsep','bank_mean_rmsep','rule']).iloc[0]['rule']
    scientific={}
    for (rule,method),g in agg.groupby(['rule','method']):
        t=g.assign(budget_gap=np.abs(g.mean_pulses-4)).sort_values(['budget_gap','worst_rmsep','threshold_index']).iloc[0]
        scientific[rule+'|'+method]=int(t.threshold_index)
    target=proposed[proposed.apply(lambda r:scientific[r['rule']+'|proposed']==r['threshold_index'],axis=1)]
    adaptive=target.sort_values(['worst_rmsep','mean_rmsep','rule']).iloc[0]['rule']
    mean=target.sort_values(['mean_rmsep','worst_rmsep','rule']).iloc[0]['rule']
    result={'primary_rule':str(eng.rule),'accuracy_rule':str(bank),'adaptive_error_rule':str(adaptive),
            'mean_season_rule':str(mean),'independent_rule':'uniform', 'scientific_operating_indices':scientific,
            'engineering_operating_index':int(eng.threshold_index),'development_engineering_feasible':bool(eng.feasible),
            'fallback_max_normalized_violation':float(eng.max_normalized_violation),
            'selection_basis':'three outer development seasons, seed 42 only; lower is better; no external outcomes'}
    agg.replace([np.inf,-np.inf],np.nan).to_csv(ROOT/'results/development_frontier.csv',index=False)
    atomic_json(ROOT/'results/selection.json',result)
    return result


def run(args):
    started=time.time()
    prepare_data(data_path=args.data_path)
    data=load_development()
    catalog=get_catalog()
    atomic_json(ROOT/'results/environment.json',environment())
    channels=channel_matrix(data.X,data.wavelengths,catalog)
    if args.command=='smoke':
        smoke(data,channels,catalog)
        return
    if (ROOT/'results/frozen/manifest.json').exists():
        event('Found frozen study: verifying lock and resuming scoring/reporting without refitting.')
        from .external import score_external
        score_external()
        finish()
        return
    smoke(data,channels,catalog)
    dependency=registration(data,catalog)
    event('Registered protocol and exact partitions; starting complete development search (6 bank rules x 3 seasons).')
    rows=[]
    for fold in [1,2,3]:
        for rule in ['uniform','swap_low','swap_mid','swap_high','correlation','ridge']:
            bundle,fp,valid=get_bundle(data,channels,fold,rule,42,dependency)
            rows.extend(score_development(data,channels,bundle,valid,rule,fold,42,fp,['proposed','single','single_cnn_reference']))
            pd.DataFrame(rows).to_csv(ROOT/'results/development_scores.csv',index=False)
    selection=select(pd.DataFrame(rows))
    primary,independent=selection['primary_rule'],'uniform'
    event('Development-only primary bank rule '+primary+'; engineering feasible='+str(selection['development_engineering_feasible']))
    for fold in [1,2,3]:
        bundle,fp,valid=get_bundle(data,channels,fold,primary,42,dependency)
        rows.extend(score_development(data,channels,bundle,valid,primary,fold,42,fp,
                                      ['uncertainty','fixed_order','random_order','fixed_length','lookahead']))
    for seed in [7,99]:
        for fold in [1,2,3]:
            for rule in sorted(set([primary,independent])):
                bundle,fp,valid=get_bundle(data,channels,fold,rule,seed,dependency)
                rows.extend(score_development(data,channels,bundle,valid,rule,fold,seed,fp,['proposed','single']))
    devframe=pd.DataFrame(rows)
    devframe.to_csv(ROOT/'results/development_scores.csv',index=False)
    selection=select(devframe)
    point_indices=[int(np.argmin(abs(data.wavelengths-c['center_nm']))) for c in catalog]
    point_channels=data.X[:,point_indices]
    ideal_rows=[]
    for fold in [1,2,3]:
        fit,cal,valid=split_indices(data,fold)
        design=design_indices(data,fold)
        indices=bank_rules(channels[design],data.y[design])[primary]
        fp=canonical_hash([dependency,'ideal',fold,indices])
        bundle=checkpoint('model_ideal_season%d_seed42'%fold,fp,
                          lambda:fit_calibrated(data,point_channels,fit,cal,indices,42,model_settings()))
        ideal_rows.extend(score_development(data,point_channels,bundle,valid,'ideal',fold,42,fp,['proposed','single']))
    ideal_frame=pd.DataFrame(ideal_rows)
    ideal_frame.to_csv(ROOT/'results/ideal_development_scores.csv',index=False)
    for method,g in aggregate(ideal_frame).groupby('method'):
        op=g.assign(budget_gap=np.abs(g.mean_pulses-4)).sort_values(['budget_gap','worst_rmsep','threshold_index']).iloc[0]
        selection['scientific_operating_indices']['ideal|'+method]=int(op.threshold_index)
    atomic_json(ROOT/'results/selection.json',selection)
    from .baselines import fit_static,predict_static
    static_dev=[]
    for fold in [1,2,3]:
        fit,cal,valid=split_indices(data,fold)
        design=design_indices(data,fold)
        indices=bank_rules(channels[design],data.y[design])[primary]
        models=checkpoint('static_season%d'%fold,canonical_hash([dependency,fold,indices,digest(ROOT/'mango/baselines.py')]),
                          lambda:fit_static(channels[fit],data.X[fit],data.y[fit],data.groups[fit],indices))
        for name,p in predict_static(models,channels[valid],data.X[valid]).items():
            static_dev.append(dict(fold=fold,method=name,**regression(data.y[valid],p)))
    pd.DataFrame(static_dev).to_csv(ROOT/'results/static_development.csv',index=False)
    from .walsh_reference import fit_walsh
    walsh_dev=[]
    for fold in [1,2,3]:
        fit,cal,valid=split_indices(data,fold)
        model=checkpoint('walsh_season%d_seed42'%fold,canonical_hash([dependency,fold,digest(ROOT/'mango/walsh_reference.py')]),
                         lambda:fit_walsh(data.X[fit],data.y[fit],data.groups[fit],seed=42))
        walsh_dev.append(dict(fold=fold,method='walsh_adapted',**regression(data.y[valid],model.predict(data.X[valid]))))
    pd.DataFrame(walsh_dev).to_csv(ROOT/'results/walsh_development.csv',index=False)
    final={}
    roles=sorted(set([selection[k] for k in ['primary_rule','accuracy_rule','adaptive_error_rule','mean_season_rule','independent_rule']]))
    for rule in roles:
        for seed in ([42,7,99] if rule in {primary,independent} else [42]):
            bundle,fp,_=get_bundle(data,channels,None,rule,seed,dependency)
            final[rule+'|'+str(seed)]=bundle
    fit,cal,_=split_indices(data,None)
    indices=final[primary+'|42']['bank_indices']
    static=checkpoint('static_final',canonical_hash([dependency,'final',indices,digest(ROOT/'mango/baselines.py')]),
                      lambda:fit_static(channels[fit],data.X[fit],data.y[fit],data.groups[fit],indices))
    walsh=checkpoint('walsh_final_seed42',canonical_hash([dependency,'walsh_final',digest(ROOT/'mango/walsh_reference.py')]),
                     lambda:fit_walsh(data.X[fit],data.y[fit],data.groups[fit],seed=42))
    # Ideal point comparison at the same physical nominal centers; separately fitted and calibrated.
    ideal=checkpoint('model_ideal_final_seed42',canonical_hash([dependency,'ideal',indices]),
                     lambda:fit_calibrated(data,point_channels,fit,cal,indices,42,model_settings()))
    freeze(final,static,ideal,walsh,selection,data,channels,catalog,dependency)
    event('All models and operating points frozen before opening external assays; elapsed %.1f minutes'%((time.time()-started)/60))
    from .external import score_external
    score_external()
    finish()


def freeze(final,static,ideal,walsh,selection,data,channels,catalog,dependency):
    folder=ROOT/'results/frozen'
    folder.mkdir(exist_ok=True,parents=True)
    for key,bundle in final.items():
        # Target assays and OOF arrays are development artifacts, excluded from runtime bundles.
        runtime={k:v for k,v in bundle.items() if k!='oof'}
        joblib.dump(runtime,folder/(key.replace('|','_seed')+'.joblib'),compress=3)
    joblib.dump({k:v for k,v in ideal.items() if k!='oof'},folder/'ideal_seed42.joblib',compress=3)
    joblib.dump(static,folder/'static.joblib',compress=3)
    joblib.dump(walsh,folder/'walsh.joblib',compress=3)
    atomic_json(folder/'selection.json',selection)
    atomic_json(folder/'catalog.json',catalog)
    shutil.copy2(ROOT/'config/experiment.json',folder/'experiment.json')
    shutil.copy2(ROOT/'results/protocol_lock.json',folder/'protocol_lock.json')
    shutil.copy2(ROOT/'results/fold_assignments.json',folder/'fold_assignments.json')
    code=folder/'code';code.mkdir(exist_ok=True)
    for source in sorted((ROOT/'mango').glob('*.py')):
        shutil.copy2(source,code/source.name)
    shutil.copy2(ROOT/'run_project.py',code/'run_project.py')
    primary=final[selection['primary_rule']+'|42']
    ex=0
    # No assay is distributed in the public-facing replay fixture.
    atomic_json(folder/'demo_example.json',{'row_id':str(data.row_ids[ex]),'season':int(data.seasons[ex]),
                'group':str(data.groups[ex]),'readings':channels[ex,primary['bank_indices']].tolist(),
                'note':'Real development scan, simulated channels; assay intentionally omitted.'})
    files={str(p.relative_to(ROOT)):digest(p) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
    for p in (ROOT/'data/catalog').rglob('*'):
        if p.is_file():files[str(p.relative_to(ROOT))]=digest(p)
    data_manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for relative,checksum in data_manifest['artifacts'].items():
        files['data/'+relative]=checksum
    files['data/manifest.json']=digest(ROOT/'data/manifest.json')
    files['results/fold_assignments.json']=digest(ROOT/'results/fold_assignments.json')
    manifest={'status':'frozen','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'protocol_dependency':dependency,'hashes':files,'external_scoring_started':False,
              'code_revision':'SHA256 source snapshot (workspace was not a Git repository)',
              'external_outcomes_used_for_selection':False}
    atomic_json(folder/'manifest.json',manifest)
    for p in folder.rglob('*'):
        if p.is_file():p.chmod(0o444)
    event('Immutable manifest written: '+str(len(files))+' artifact hashes.')


def smoke(data,channels,catalog):
    assert data.X.shape[1]==103 and len(catalog)>8
    assert np.max(np.abs(channel_matrix(np.ones((2,103))*.73,data.wavelengths,catalog)-.73))<1e-10
    for fold in [1,2,3,None]:split_indices(data,fold)
    subprocess.check_call([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_models.py'],cwd=ROOT)
    atomic_json(ROOT/'results/smoke.json',{'status':'passed','development_scans':len(data),'eligible_channels':len(catalog),
                                         'checks':['real schema','constant spectrum','group separation','model contract tests']})
    event('Real-data smoke checks passed; external assays unopened by smoke.')


def finish():
    from .app import replay,serve
    replay(trace_output='results/demo_trace.json')
    serve(self_test=True)
    from .reporting import generate_reports
    generate_reports()
    from .verification import verify
    verify()
    event('All runnable stages completed; see verification_report.md for evidence and scoped limitations.')


def status():
    print((ROOT/'RUN_STATUS.md').read_text())
    paths=list((ROOT/'results/checkpoints').glob('*.json'))
    complete=sum(json.loads(p.read_text()).get('status')=='complete' for p in paths)
    print('\nValidated checkpoint metadata:',complete)
    print('Frozen:',(ROOT/'results/frozen/manifest.json').exists())
    print('External results:',(ROOT/'results/external_metrics.csv').exists())
