"""Independent arithmetic audit of already-scored tables; never loads models or raw data."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def basic(frame):
    y=frame.y.to_numpy(float);p=frame.prediction.to_numpy(float)
    residual=p-y;absolute=np.abs(residual)
    bank_error=np.abs(y-frame.bank_prediction.to_numpy(float))
    rich_error=np.abs(y-frame.rich_prediction.to_numpy(float))
    pulses=frame.pulses.to_numpy(float)
    early=pulses<8
    missed=early&((absolute-bank_error)>.5)
    scale=np.sum((y-y.mean())**2)
    return {'n':len(y),'rmsep':float(np.sqrt(np.mean(residual**2))),
            'mae':float(np.mean(absolute)),'bias':float(np.mean(residual)),
            'r2':float(1-np.sum(residual**2)/scale) if scale else None,
            'mean_pulses':float(np.mean(pulses)),'median_pulses':float(np.median(pulses)),
            'p95_pulses':float(np.percentile(pulses,95)),'early_n':int(early.sum()),
            'early_fraction':float(early.mean()),'missed_n':int(missed.sum()),
            'missed_rate':float(missed.sum()/early.sum()) if early.sum() else None,
            'missed_unconditional':float(missed.mean()),'bank_loss_n':int(np.sum(bank_error-rich_error>.5)),
            'bank_loss_rate':float(np.mean(bank_error-rich_error>.5)),
            'large_absolute_error_n':int(np.sum(absolute>2)),
            'large_absolute_error_rate':float(np.mean(absolute>2)),
            'bank_rmsep':float(np.sqrt(np.mean(bank_error**2))),
            'rich_rmsep':float(np.sqrt(np.mean(rich_error**2)))}


def pair_values(paired, weights=None):
    if weights is None:weights=np.ones(len(paired),dtype=float)
    y=paired.y_a.to_numpy(float)
    ea=np.abs(y-paired.prediction_a.to_numpy(float));eb=np.abs(y-paired.prediction_b.to_numpy(float))
    bank=np.abs(y-paired.bank_prediction_a.to_numpy(float))
    xa=paired.pulses_a.to_numpy(float);xb=paired.pulses_b.to_numpy(float)
    aa=xa<8;ab=xb<8
    ma=aa&((ea-bank)>.5);mb=ab&((eb-bank)>.5)
    mean=lambda a:float(np.sum(weights*a)/weights.sum())
    n_a=np.sum(weights*aa);n_b=np.sum(weights*ab)
    conditional=(float(np.sum(weights*ma)/n_a-np.sum(weights*mb)/n_b) if n_a and n_b else None)
    return [float(np.sqrt(mean(ea**2))-np.sqrt(mean(eb**2))),mean(xa-xb),conditional,mean(ma)-mean(mb)]


def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,np.integer):return int(value)
    if isinstance(value,np.bool_):return bool(value)
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    return value


def run():
    completion=ROOT/'results/external_completion.json'
    if not completion.exists():
        print('PENDING: external completion does not exist; no prediction tables opened.')
        return None
    completed=json.loads(completion.read_text())
    assert completed['status']=='complete'
    assert completed['freeze_sha256']==sha(ROOT/'results/frozen/manifest.json')
    for rel,digest in completed['outputs'].items():assert sha(ROOT/rel)==digest,(rel,'hash mismatch')
    selection=json.loads((ROOT/'results/frozen/selection.json').read_text())
    primary=selection['primary_rule']
    predictions=pd.read_csv(ROOT/'results/external_predictions.csv',float_precision='round_trip')
    metrics=pd.read_csv(ROOT/'results/external_metrics.csv',float_precision='round_trip')
    uncertainty=json.loads((ROOT/'results/external_uncertainty.json').read_text())
    issues=[];checks=[];season_results={};max_error=0.
    def require(condition,message):
        checks.append({'check':message,'passed':bool(condition)})
        if not condition:issues.append(message)
    def equal(a,b,label,tolerance=1e-10):
        nonlocal max_error
        if a is None or b is None:
            require(a is None and (b is None or (isinstance(b,float) and np.isnan(b))),label)
            return
        if isinstance(a,list):
            require(len(a)==len(b),label+' dimensions')
            for i,(aa,bb) in enumerate(zip(a,b)):equal(aa,bb,label+'[%d]'%i,tolerance)
            return
        error=abs(float(a)-float(b));max_error=max(max_error,error)
        require(error<=tolerance,label)
    require(primary=='swap_mid','final primary bank equals expected development-selected swap_mid')
    for season in [4,5]:
        base=predictions[(predictions.season==season)&(predictions.rule==primary)&(predictions.seed==42)]
        saved=metrics[(metrics.season==season)&(metrics.rule==primary)&(metrics.seed==42)]
        by_method={};frames={}
        for method in ['proposed','single','full_bank','rich_pls','rich_cnn','walsh_adapted']:
            op='scientific' if method in ['proposed','single'] else 'reference'
            scenario='static' if method=='walsh_adapted' else 'nominal'
            take=(base.method==method)&(base.operating_point==op)&(base.scenario==scenario)
            frame=base.loc[take].sort_values('row_id').reset_index(drop=True)
            expected=saved[(saved.method==method)&(saved.operating_point==op)&(saved.scenario==scenario)]
            require(len(expected)==1,'season%d %s has one summary row'%(season,method))
            require(len(frame)=={4:1448,5:320}[season] and frame.row_id.nunique()==len(frame),
                    'season%d %s has unique complete scan records'%(season,method))
            found=basic(frame)
            for key,val in found.items():
                b=expected.iloc[0][key]
                equal(val,None if pd.isna(b) else float(b),'season%d %s %s recomputed'%(season,method,key))
            equal(float(np.max(np.abs(frame.g_stop-(np.abs(frame.y-frame.prediction)-np.abs(frame.y-frame.bank_prediction))))),0.,
                  'season%d %s signed g_stop preserved'%(season,method))
            equal(float(np.max(np.abs(frame.g_bank-(np.abs(frame.y-frame.bank_prediction)-np.abs(frame.y-frame.rich_prediction))))),0.,
                  'season%d %s signed g_bank preserved'%(season,method))
            frames[method]=frame;by_method[method]=found
        paired=frames['proposed'].merge(frames['single'],on='row_id',suffixes=('_a','_b'),validate='one_to_one')
        require(np.array_equal(paired.y_a,paired.y_b),'season%d paired assays agree'%season)
        require(np.array_equal(paired.group_a,paired.group_b),'season%d paired harvest groups agree'%season)
        require(np.array_equal(paired.bank_prediction_a,paired.bank_prediction_b),'season%d same frozen bank reference'%season)
        observed=pair_values(paired)
        record=uncertainty['%d|%s|42'%(season,primary)]
        equal(observed,record['point'],'season%d proposed-minus-single point orientation'%season)
        comparable=abs(observed[1])<=.25
        require(comparable==record['achieved_budget_comparable'],'season%d achieved budget comparability'%season)
        unique=np.unique(paired.group_a.to_numpy())
        require(len(unique)=={4:18,5:2}[season],'season%d group denominator'%season)
        interval=None;group_estimates=None
        if season==4:
            rng=np.random.RandomState(42)
            samples=[]
            for _ in range(1000):
                draw=rng.choice(unique,len(unique),replace=True)
                counts={g:int(np.sum(draw==g)) for g in unique}
                weights=np.array([counts[g] for g in paired.group_a],dtype=float)
                samples.append(pair_values(paired,weights))
            interval=[]
            for k in range(4):
                values=[row[k] for row in samples if row[k] is not None]
                interval.append(np.percentile(values,[2.5,97.5]).tolist() if values else None)
            equal(interval,record['intervals'],'season4 independent cluster-weight bootstrap intervals')
        else:
            require(record['intervals'] is None,'season5 population intervals suppressed')
            group_estimates={str(g):pair_values(paired.loc[paired.group_a==g]) for g in unique}
            for key,value in group_estimates.items():equal(value,record['group_estimates'][key],'season5 group '+key)
        engineering=base[(base.method=='proposed')&(base.operating_point=='engineering')&(base.scenario=='nominal')]
        em=basic(engineering)
        prototype={'engineering_policy_rmsep':em['rmsep'],'full_bank_rmsep':by_method['full_bank']['rmsep'],
                   'rmsep_increase':em['rmsep']-by_method['full_bank']['rmsep'],
                   'mean_pulses':em['mean_pulses'],'pulse_reduction':1-em['mean_pulses']/8,
                   'rmsep_increase_within_0p25':em['rmsep']-by_method['full_bank']['rmsep']<=.25,
                   'at_least_25percent_pulse_reduction':1-em['mean_pulses']/8>=.25}
        prototype['both_numerical_prototype_criteria_pass']=prototype['rmsep_increase_within_0p25'] and prototype['at_least_25percent_pulse_reduction']
        season_results[str(season)]={'n_harvest_groups':len(unique),'primary_scientific_and_references':by_method,
            'paired_estimands':record['estimands'],'independently_recomputed_points':observed,
            'independently_recomputed_intervals':interval,'season5_group_estimates':group_estimates,
            'achieved_budget_comparable':comparable,'engineering_criteria':prototype,
            'orientation':'proposed minus single; negative RMSEP difference favors proposed',
            'interpretation_limit':'A pulse gap greater than 0.25 precludes an unqualified matched-budget superiority interpretation; external thresholds were not retuned.'}
    result={'status':'passed' if not issues else 'failed','scope':'Independent saved-table arithmetic only; no model, sealed data, evaluation or fitting code imported.',
            'primary_rule':primary,'primary_seed':42,'sources':{name:sha(ROOT/name) for name in ['results/external_predictions.csv','results/external_metrics.csv','results/external_uncertainty.json','results/external_completion.json','results/frozen/manifest.json']},
            'script_sha256':sha(__file__),'checks':checks,'failed_checks':issues,'maximum_absolute_numeric_discrepancy':max_error,
            'season_results':season_results,'external_assays_reopened':False}
    target=ROOT/'results/independent_numerical_audit.json';temporary=target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(clean(result),indent=2,sort_keys=True,allow_nan=False)+'\n');temporary.replace(target)
    print(json.dumps({'status':result['status'],'primary_rule':primary,'checks':len(checks),'maximum_discrepancy':max_error,'results':season_results},indent=2))
    if issues:raise AssertionError(issues)
    return result


if __name__=='__main__':run()
