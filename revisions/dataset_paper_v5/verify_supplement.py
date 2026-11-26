"""Independently reconcile every supplementary table against saved sources.

This checks rendered LaTeX values, keys, complete source-row coverage, declared
hashes, and tuning/evaluation labels. It does not call the supplement generator,
fit models, load raw datasets, or modify manuscripts or earlier artifacts.
"""

from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = HERE / 'results/supplement_numeric_verification.json'
BANK = {'P':'swap_mid','U':'uniform','C':'correlation'}
FAMILY = {'Hybrid':'mlp_hybrid','PLS':'pls','Ridge':'ridge'}
VARIANT = {'Catalog':'catalog','Designed':'designed','Subset':'selected_subset'}
POINT = {'S':'scientific','E':'engineering','Ref':'reference','4':'depth_4','6':'depth_6','7':'depth_7'}
OBJECTIVE = {'B':'two_reference','R':'single_reference'}
SCENARIO = {'N':'nominal','Static':'static','Points':'ideal_points','C-':'center_minus3',
            'C+':'center_plus3','W-':'width_times0p9','W+':'width_times1p1','Gauss':'gaussian_approximation'}
CHECKS = []
NUMERIC = []
TABLE_SUMMARIES = {}


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1<<20),b''):
            h.update(data)
    return h.hexdigest()


def require(ok, name):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS.append(name)


def text(value):
    value=value.strip().replace(r'\_', '_')
    return re.sub(r'\\texttt\{([^}]*)\}',r'\1',value)


def number(token, expected, context):
    token=token.strip()
    if pd.isna(expected):
        require(token=='--',context+': missing value must be --')
        return
    require(token!='--',context+': finite value missing')
    actual=float(token)
    decimals=len(token.split('.')[1]) if '.' in token else 0
    tolerance=(0.5*10**(-decimals)+1e-10) if decimals else 1e-10
    difference=abs(actual-float(expected))
    require(difference<=tolerance,context+': displayed '+token+' vs source '+repr(float(expected)))
    NUMERIC.append({'context':context,'displayed':token,'source':float(expected),
                    'absolute_difference':difference,'rounding_tolerance':tolerance})


def boolean(token, expected, context):
    wanted='--' if pd.isna(expected) else ('yes' if bool(expected) else 'no')
    require(token==wanted,context+': '+token+' vs '+wanted)


def interval(token, expected, context):
    match=re.fullmatch(r'(-?\d+\.\d+) \[(-?\d+\.\d+), (-?\d+\.\d+)\]',token)
    require(match is not None,context+': invalid interval formatting')
    for name,value,wanted in zip(('estimate','lower','upper'),match.groups(),expected):
        number(value,wanted,context+':'+name)


def ratio(token, numerator, denominator, context):
    values=token.replace(' ','').split('/')
    require(len(values)==2,context+': invalid ratio')
    number(values[0],numerator,context+':numerator')
    number(values[1],denominator,context+':denominator')


def centers(token, expected, context):
    actual=[float(value.strip()) for value in token.split(',')]
    wanted=[float(value.strip()) for value in str(expected).split(',')]
    require(actual==wanted,context+': channel order/membership mismatch')


def load(relative):
    return pd.read_csv(ROOT/relative)


def lookup(frame, seen, context, **filters):
    subset=frame
    for name,value in filters.items():
        subset=subset[subset[name]==value]
    require(len(subset)==1,context+': unique source row '+repr(filters))
    index=subset.index[0]
    require(index not in seen,context+': duplicated source row')
    seen.add(index)
    return subset.iloc[0]


def coverage(label, rows, seen, expected, source):
    require(seen==set(expected.index),label+': complete source-row coverage')
    TABLE_SUMMARIES[label]={'display_rows':len(rows),'source_rows_checked':len(seen),
                             'source':source,'coverage':'complete'}


def parse_tables(document):
    tables={}
    for block in re.findall(r'\\begin\{longtable\}.*?\\end\{longtable\}',document,re.S):
        label=re.search(r'\\label\{([^}]+)\}',block).group(1)
        require(label not in tables,'unique table label '+label)
        body=block.split(r'\endlastfoot')[1].split(r'\end{longtable}')[0].strip()
        rows=[]
        for line in body.splitlines():
            if '&' not in line:
                continue
            require(line.rstrip().endswith(r'\\'),label+': terminated table row')
            rows.append([text(token) for token in line.rstrip()[:-2].split('&')])
        tables[label]=rows
    return tables


def main():
    review_path=HERE/'results/supplement_review.json'
    manuscript=HERE/'manuscript/supplement.tex'
    review=json.loads(review_path.read_text())
    review_hash=sha256(review_path)
    manuscript_hash=sha256(manuscript)
    require(manuscript_hash==review['supplement_sha256'],'supplement SHA256 matches review')
    for relative,wanted in review['source_files'].items():
        require(sha256(ROOT/relative)==wanted,'declared source SHA256 '+relative)
    document=manuscript.read_text()
    tables=parse_tables(document)
    metadata={row['label']:row for row in review['tables']}
    require(set(tables)==set(metadata),'table label inventory matches review')
    require(len(tables)==review['table_count']==17,'17 table count')
    require(sum(map(len,tables.values()))==review['displayed_table_rows']==1237,'1237 displayed table rows')
    for label,rows in tables.items():
        require(len(rows)==metadata[label]['rows'],label+': row count')
        require(all(len(row)==metadata[label]['columns'] for row in rows),label+': column counts')

    # Role counts are reconstructed from exact saved row/group lists.
    roles=json.loads((ROOT/'results/fold_assignments.json').read_text())
    for row in tables['tab:roles']:
        held=None if row[0]=='Final O' else int(row[0])
        matching=[item for item in roles if item['held_season']==held]
        require(len(matching)==1,'unique split-role assignment')
        value=matching[0]
        for token,role in zip(row[1:],('fit','bank_design','calibration','validation')):
            ratio(token,len(value[role+'_row_ids']),len(value[role+'_groups']),'role '+str(held)+' '+role)
    TABLE_SUMMARIES['tab:roles']={'display_rows':4,'source_rows_checked':4,'coverage':'complete',
                                 'source':'results/fold_assignments.json'}

    original=load('results/external_metrics.csv')
    delta=load('results/external_delta_sensitivity.csv')
    for label,frame in [('tab:original',original),('tab:delta',delta)]:
        seen=set()
        for i,row in enumerate(tables[label]):
            key=dict(season=int(row[0]),rule=BANK[row[1]],seed=int(row[2]),scenario=SCENARIO[row[3]],
                     method=row[4],operating_point=POINT[row[5]])
            if key['scenario']=='ideal_points':
                key['operating_point']='ideal_'+key['operating_point']
            elif key['scenario'] not in ('nominal','static'):
                key['operating_point']=('response_shift_reference' if row[5]=='Ref' else 'response_shift')
            context=label+' row'+str(i)
            if label=='tab:original':
                source=lookup(frame,seen,context,**key)
                number(row[6],source.rmsep,context+' RMSEP')
                number(row[7],source.mean_pulses,context+' readings')
                ratio(row[8],source.missed_n,source.early_n,context+' missed/early')
                number(row[9],source.missed_rate,context+' missed_rate')
            else:
                low=lookup(frame,seen,context+' delta.25',delta=.25,**key)
                high=lookup(frame,seen,context+' delta1',delta=1.,**key)
                for token,value,name in zip(row[6:],(low.missed_rate,high.missed_rate,low.bank_loss_rate,high.bank_loss_rate),
                                            ('missed.25','missed1','bank.25','bank1')):
                    number(token,value,context+' '+name)
        coverage(label,tables[label],seen,frame,'results/external_'+('metrics' if label=='tab:original' else 'delta_sensitivity')+'.csv')

    groups=load('results/external_group_metrics.csv')
    groups=groups[(groups.season==5)&(groups.rule=='swap_mid')&(groups.seed==42)&
                  (((groups.scenario=='nominal')&(groups.method.isin(['full_bank','rich_pls','proposed','single'])))|
                   ((groups.scenario=='static')&(groups.method=='physical_plsr_4')))]
    seen=set()
    for i,row in enumerate(tables['tab:season5groups']):
        context='season5 group '+str(i)
        value=lookup(groups,seen,context,group=row[0],method=row[2],operating_point=POINT[row[3]])
        for token,name in zip([row[1]]+row[4:],('n','rmsep','mae','bias','mean_pulses')):
            number(token,value[name],context+' '+name)
    coverage('tab:season5groups',tables['tab:season5groups'],seen,groups,'results/external_group_metrics.csv')

    action=pd.DataFrame(json.loads((ROOT/'results/action_diagnostics.json').read_text())['rows']);seen=set()
    for i,row in enumerate(tables['tab:action']):
        context='action row'+str(i)
        value=lookup(action,seen,context,season=int(row[0]),method={'B':'proposed','R':'single'}[row[1]],
                     scope={'F':'forced_full_trajectory','A':'visited_continuations'}[row[2]],pulses_before=int(row[3]))
        for token,name in zip(row[4:],('n','predicted_mean','actual_mean','actual_improvement_fraction',
                                      'actual_material_improvement_fraction','mean_action_rank_correlation','hindsight_regret_mean')):
            number(token,value[name],context+' '+name)
    coverage('tab:action',tables['tab:action'],seen,action,'results/action_diagnostics.json')

    predictor=load('revisions/methodology_v2/results/predictor_metrics.csv')
    predictor=predictor[predictor.split=='valid'];seen=set()
    for i,row in enumerate(tables['tab:v2predictors']):
        context='v2 predictor row'+str(i)
        for depth,token in zip(range(2,9),row[6:]):
            value=lookup(predictor,seen,context,held_season=int(row[0]),bank=BANK[row[1]],seed=int(row[2]),
                         family=FAMILY[row[3]],scope={'All masks':'all_masks','Order':'common_order'}[row[4]],depth=depth)
            number(row[5],value.n_scans,context+' n_scans')
            number(token,value.rmsep,context+' depth'+str(depth))
    coverage('tab:v2predictors',tables['tab:v2predictors'],seen,predictor,'revisions/methodology_v2/results/predictor_metrics.csv')

    endpoint=load('revisions/methodology_v2/results/endpoint_summary.csv');seen=set()
    for i,row in enumerate(tables['tab:endpoint']):
        context='endpoint row'+str(i)
        value=lookup(endpoint,seen,context,held_season=int(row[0]),bank=BANK[row[1]],seed=int(row[2]))
        number(row[3],value.n_groups,context+' groups')
        for token,key in zip(row[4:],('total','estimator','measurement')):
            interval(token,[value[key+suffix] for suffix in ('_mean','_ci_low','_ci_high')],context+' '+key)
    coverage('tab:endpoint',tables['tab:endpoint'],seen,endpoint,'revisions/methodology_v2/results/endpoint_summary.csv')

    v2=load('revisions/methodology_v2/results/policy_metrics.csv')
    v3=load('revisions/fixed_design_v3/results/metrics.csv')
    for label,frame,revision in [('tab:v2adaptive',v2,2),('tab:v3adaptive',v3,3)]:
        frame=frame[frame.objective!='fixed_length'];seen=set()
        for i,row in enumerate(tables[label]):
            context=label+' row'+str(i)
            if revision==2:
                key=dict(held_season=int(row[0]),bank=BANK[row[1]],seed=int(row[2]),family=FAMILY[row[3]])
            else:
                key=dict(held_season=int(row[0]),bank=BANK[row[1]],family=FAMILY[row[2]],variant=VARIANT[row[3]])
            key.update(objective=OBJECTIVE[row[4]],operating_point=POINT[row[5]])
            value=lookup(frame,seen,context,**key)
            for token,name in zip(row[6:9],('threshold','rmsep','mean_pulses')):
                number(token,value[name],context+' '+name)
            ratio(row[9],value.missed_n,value.early_n,context+' missed/early')
            boolean(row[10],value.calibration_engineering_feasible,context+' calibration feasibility')
            boolean(row[11],value.evaluation_engineering_pass,context+' held success')
        coverage(label,tables[label],seen,frame,'revisions/'+('methodology_v2/results/policy_metrics.csv' if revision==2 else 'fixed_design_v3/results/metrics.csv'))

    for label,path,revision in [('tab:v2paired','revisions/methodology_v2/results/paired_comparisons.csv',2),
                               ('tab:v3paired','revisions/fixed_design_v3/results/comparisons.csv',3)]:
        frame=load(path);seen=set()
        for i,row in enumerate(tables[label]):
            context=label+' row'+str(i)
            if revision==2:
                key=dict(held_season=int(row[0]),bank=BANK[row[1]],seed=int(row[2]),family=FAMILY[row[3]],
                         comparison={'BR':'two_minus_single','B4':'two_minus_fixed4','PM':'predictor_minus_mlp'}[row[4]],
                         operating_point=POINT[row[5]])
                start=6
            else:
                key=dict(held_season=int(row[0]),bank=BANK[row[1]],family=FAMILY[row[2]],
                         comparison={'DC':'designed_fixed_minus_catalog','SC':'selected_subset_minus_catalog',
                                     'BR':'two_minus_single','AS':'adaptive_minus_selected_subset'}[row[3]],
                         operating_point=POINT[row[4]])
                start=5
            value=lookup(frame,seen,context,**key)
            interval(row[start],[value.delta_rmsep,value.rmsep_ci_low,value.rmsep_ci_high],context+' RMSEP interval')
            number(row[start+1],value.delta_pulses,context+' reading difference')
            boolean(row[start+2],value.budget_comparable,context+' budget comparability')
        coverage(label,tables[label],seen,frame,path)

    composition=load('revisions/fixed_design_v3/results/design_composition.csv')
    aggregates=composition.groupby(['held_season','bank','season']).agg(groups=('group','nunique'),scans=('n','sum')).reset_index()
    for row in tables['tab:designcomposition']:
        for bank in ('swap_mid','uniform'):
            value=aggregates[(aggregates.held_season==int(row[0]))&(aggregates.season==int(row[1]))&(aggregates.bank==bank)]
            require(len(value)==1,'unique design-composition source')
            number(row[2],value.iloc[0]['groups'],'composition groups '+bank)
            number(row[3],value.iloc[0]['scans'],'composition scans '+bank)
    require(len(tables['tab:designcomposition'])*2==len(aggregates),'design-composition complete cross-bank coverage')
    TABLE_SUMMARIES['tab:designcomposition']={'display_rows':6,'source_rows_checked':len(composition),
                                             'coverage':'complete aggregated by source season, both banks',
                                             'source':'revisions/fixed_design_v3/results/design_composition.csv'}

    orders=load('revisions/fixed_design_v3/results/selected_designs.csv');seen=set()
    for i,row in enumerate(tables['tab:orders']):
        context='order row'+str(i)
        value=lookup(orders,seen,context,held_season=int(row[0]),bank=BANK[row[1]],family=FAMILY[row[2]])
        centers(row[3],value.order_nm,context)
        for token,name in zip(row[4:],('order_score','catalog_order_score','order_margin')):
            number(token,value[name],context+' '+name)
    coverage('tab:orders',tables['tab:orders'],seen,orders,'revisions/fixed_design_v3/results/selected_designs.csv')

    subsets=load('revisions/fixed_design_v3/results/design_subsets.csv');subsets=subsets[subsets.selected];seen=set()
    for i,row in enumerate(tables['tab:subsets']):
        context='subset row'+str(i)
        value=lookup(subsets,seen,context,held_season=int(row[0]),bank=BANK[row[1]],family=FAMILY[row[2]],depth=int(row[3]))
        centers(row[4],value.centers_nm,context)
        number(row[5],value.rmsep,context+' design RMSEP')
    coverage('tab:subsets',tables['tab:subsets'],seen,subsets,'revisions/fixed_design_v3/results/design_subsets.csv (selected only)')

    fixed=v3[v3.objective=='fixed_length'];seen=set()
    for i,row in enumerate(tables['tab:v3fixed']):
        context='v3 fixed row'+str(i)
        for depth,token in zip(range(2,9),row[4:]):
            value=lookup(fixed,seen,context,held_season=int(row[0]),bank=BANK[row[1]],family=FAMILY[row[2]],
                         variant=VARIANT[row[3]],operating_point='depth_'+str(depth))
            number(token,value.rmsep,context+' depth'+str(depth))
    coverage('tab:v3fixed',tables['tab:v3fixed'],seen,fixed,'revisions/fixed_design_v3/results/metrics.csv (fixed only)')

    stability=load('revisions/fixed_design_v3/results/selection_stability.csv');seen=set()
    for i,row in enumerate(tables['tab:stability']):
        context='stability row'+str(i)
        for token,pair in zip(row[4:],((1,2),(1,3),(2,3))):
            value=lookup(stability,seen,context,bank=BANK[row[0]],family=FAMILY[row[1]],variant=VARIANT[row[2]],
                         depth=int(row[3]),held_a=pair[0],held_b=pair[1])
            number(token,value.jaccard,context+' pair'+str(pair))
    coverage('tab:stability',tables['tab:stability'],seen,stability,'revisions/fixed_design_v3/results/selection_stability.csv')

    candidate=load('revisions/candidate_v4/results/selection_scores.csv');seen=set()
    for i,row in enumerate(tables['tab:candidateselection']):
        context='candidate tuning row'+str(i)
        value=lookup(candidate,seen,context,index=int(row[0]))
        centers(row[1],value.centers_nm,context)
        number(row[2],value.mse,context+' tuning MSE')
        number(row[3],value.rmsep,context+' tuning RMSEP')
        boolean(row[4],value.selected,context+' selected flag')
    coverage('tab:candidateselection',tables['tab:candidateselection'],seen,candidate,'revisions/candidate_v4/results/selection_scores.csv (tuning only)')
    require('development LOPO tuning results only' in metadata['tab:candidateselection']['caption'],'V4 caption labels tuning only')
    require('not independent validation accuracy' in metadata['tab:candidateselection']['caption'],'V4 caption excludes independent accuracy')
    require("V3's performance cannot be assigned to this final artifact" in document,'V4 narrative excludes inherited V3 accuracy')
    require('not an independently evaluated fourth study' in document,'V4 narrative excludes independent study')

    counts={'original_operating_points':len(original),'original_delta_rows':len(delta),
            'v2_held_predictor_cells':len(predictor),'v2_adaptive_points':len(v2[v2.objective!='fixed_length']),
            'v2_paired_contrasts':TABLE_SUMMARIES['tab:v2paired']['source_rows_checked'],
            'v3_fixed_points':len(fixed),'v3_adaptive_points':len(v3[v3.objective!='fixed_length']),
            'v3_paired_contrasts':TABLE_SUMMARIES['tab:v3paired']['source_rows_checked'],
            'v3_selected_subsets':len(subsets),'v4_tuning_scores':len(candidate)}
    require(counts==review['source_stage_counts'],'all source-stage counts reconstructed')
    require(set(TABLE_SUMMARIES)==set(tables),'every supplementary table numerically audited')
    for relative,wanted in review['source_files'].items():
        require(sha256(ROOT/relative)==wanted,'source remained unchanged '+relative)
    require(sha256(review_path)==review_hash,'review remained unchanged during audit')
    require(sha256(manuscript)==manuscript_hash,'supplement remained unchanged during audit')
    output={'status':'PASS','verification_kind':'independent source-to-LaTeX numeric reconciliation',
            'supplement_sha256':manuscript_hash,'supplement_review_sha256':review_hash,
            'verifier_sha256':sha256(__file__),'verifier_source_sha256':sha256(__file__),
            'source_sha256':review['source_files'],
            'table_count':len(tables),'displayed_table_rows':sum(map(len,tables.values())),
            'tables':TABLE_SUMMARIES,'checks':len(CHECKS),'numeric_values_checked':len(NUMERIC),
            'source_stage_counts':counts,'numeric_cells':NUMERIC,
            'tolerance':'half the last displayed decimal place plus 1e-10; exact integer/identifier/flag/coverage checks',
            'raw_data_loaded':False,'model_fitting_performed':False,'prior_artifacts_modified':False,
            'v4_status':'All 15 scores explicitly verified as development tuning evidence, not independent accuracy.',
            'limits':'Verifies transcription and complete table coverage against preserved results; earlier numerical audits establish prediction-level calculations. Does not re-estimate models or claim new biological validation.'}
    REPORT.write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print('Supplement PASS: %d tables, %d rows, %d checks, %d numeric values.'%
          (len(tables),sum(map(len,tables.values())),len(CHECKS),len(NUMERIC)))


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        REPORT.write_text(json.dumps({'status':'FAIL','error':repr(error),'checks_completed':len(CHECKS),
                                      'numeric_values_checked':len(NUMERIC)},indent=2)+'\n')
        raise
