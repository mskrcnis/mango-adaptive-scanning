"""Reporting-only generation from locked, saved external predictions."""
import json
import shutil
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .state import ROOT,atomic_json,canonical_hash,digest,event

COLORS={'proposed':'#126E75','single':'#BF553E','uncertainty':'#7656A0','fixed_order':'#586F3E',
        'random_order':'#88919B','lookahead':'#C69526','single_cnn_reference':'#784B63'}
LABELS={'proposed':'Two-reference','single':'Single rich-reference','full_bank':'All installed LEDs',
        'rich_pls':'Full-spectrum PLSR','rich_cnn':'Compact full-spectrum CNN', 'walsh_adapted':'Walsh-architecture CNN',
        'uncertainty':'Residual uncertainty','fixed_order':'Fixed order + stopping','random_order':'Random order + stopping',
        'lookahead':'Two-step look-ahead','fixed_length':'Fixed-length scan','single_cnn_reference':'Single CNN-reference'}


def tex(value):
    return str(value).replace('\\',r'\textbackslash{}').replace('_',r'\_').replace('%',r'\%').replace('&',r'\&').replace('#',r'\#')


def num(value,digits=3):
    if value is None or pd.isna(value):return 'undefined'
    return ('%.'+str(digits)+'f')%value


def savefig(fig,name):
    fig.savefig(ROOT/'figures'/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(ROOT/'figures'/(name+'.png'),bbox_inches='tight',dpi=240)
    plt.close(fig)


def subset(frame,rule,method,season,point='scientific',seed=42):
    found=frame[(frame.rule==rule)&(frame.method==method)&(frame.season==season)&
                (frame.seed==seed)&(frame.operating_point==point)]
    if len(found)!=1:raise ValueError('Expected one row: '+str((rule,method,season,point,seed,len(found))))
    return found.iloc[0]


def main_rows(metrics,selection):
    rule=selection['primary_rule']
    return [(season,subset(metrics,rule,'proposed',season),subset(metrics,rule,'single',season)) for season in [4,5]]


def figures(metrics,predictions,selection):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'font.family':'DejaVu Sans'})
    rule=selection['primary_rule']
    fig,ax=plt.subplots(figsize=(9,4.4));ax.axis('off')
    boxes=[(.02,.53,.26,.40,'DEVELOPMENT\nSeasons 1-3\n10,243 scans\n94 harvest populations'),
           (.37,.53,.26,.40,'GROUPED LEARNING\nOOF gain targets\nDisjoint calibration\n6 banks; 3 season folds'),
           (.72,.53,.26,.40,'ARTIFACT LOCK\nBank and fitted models\nCalibration mappings\nGrid + operating points'),
           (.37,.02,.26,.36,'OBSERVED-ONLY REPLAY\n2 initial LEDs; up to 8\nNo assay available\nto the controller'),
           (.72,.02,.26,.36,'EXTERNAL EVALUATION\nSeason 4: 1,448 scans\n18 harvest populations\nSeason 5: 320 / 2 groups')]
    from matplotlib.patches import FancyBboxPatch
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.01',facecolor='#EEF4F4',edgecolor='#126E75'))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=10)
    for start,end in [((.29,.73),(.36,.73)),((.64,.73),(.71,.73)),((.85,.52),(.50,.39)),((.64,.2),(.71,.2))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#37464A','lw':1.7})
    savefig(fig,'study_design')
    from .optics import get_catalog,response_weights
    catalog=get_catalog();wave=np.arange(684,991,3)
    bank=joblib.load(ROOT/'results/frozen'/(rule+'_seed42.joblib'))['bank_indices']
    weights=response_weights(wave,catalog)
    fig,ax=plt.subplots(figsize=(8,3.8))
    for i,c in enumerate(catalog):
        ax.plot(wave,weights[:,i]/weights[:,i].max(),label=str(c['center_nm'])+' nm'+(' *' if i in bank else ''),
                lw=1.8 if i in bank else .8,alpha=1 if i in bank else .5,linestyle='-' if i in bank else '--')
    ax.set(xlabel='Wavelength (nm)',ylabel='Normalized typical emission',title='Digitized component profiles; * installed in primary bank')
    ax.legend(ncol=5,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.18));savefig(fig,'led_profiles')
    curves=pd.read_csv(ROOT/'results/frozen_curves.csv')
    curves=curves[curves.scenario=='nominal']
    fig,axes=plt.subplots(1,2,figsize=(9,4),sharey=False)
    for ax,season in zip(axes,[4,5]):
        for method in ['proposed','single','uncertainty','fixed_order','lookahead']:
            g=curves[(curves.season==season)&(curves.rule==rule)&(curves.seed==42)&(curves.method==method)].sort_values('mean_pulses')
            if len(g):ax.plot(g.mean_pulses,g.rmsep,'o-',ms=3,lw=1.3,label=LABELS[method],color=COLORS[method])
        for method in ['proposed','single']:
            g=subset(metrics,rule,method,season)
            ax.scatter([g.mean_pulses],[g.rmsep],s=85,marker='*',color=COLORS[method],zorder=10,edgecolor='black',linewidth=.5)
        ax.set(title='Season %d'%season,xlabel='Mean simulated LED readings',ylabel='RMSEP (dry-matter pp)',xlim=(1.8,8.2))
        ax.grid(alpha=.15)
    axes[1].legend(fontsize=8,loc='best');savefig(fig,'error_pulses')
    fig,axes=plt.subplots(1,2,figsize=(9,3.6))
    for ax,season in zip(axes,[4,5]):
        rows=[subset(metrics,rule,m,season) for m in ['proposed','single']]
        labels=['Two-reference','Single-reference','Full-bank loss']
        rates=[r.missed_rate for r in rows]+[rows[0].bank_loss_rate]
        counts=[str(int(r.missed_n))+'/'+str(int(r.early_n)) for r in rows]+[str(int(rows[0].bank_loss_n))+'/'+str(int(rows[0]['n']))]
        ax.bar(labels,np.asarray(rates)*100,color=[COLORS['proposed'],COLORS['single'],'#62747B'])
        for i,(rate,count) in enumerate(zip(rates,counts)):
            if np.isfinite(rate):ax.text(i,rate*100+1,count,ha='center',fontsize=9)
        ax.axhline(10,ls='--',c='black',lw=.8)
        finite_rates=[x for x in rates if np.isfinite(x)]
        for i,rate in enumerate(rates):
            if not np.isfinite(rate):ax.text(i,2,'undefined\n0 early stops',ha='center',fontsize=8)
        ax.set(ylabel='Material-error event rate (%)',title='Season %d; delta = 0.50 pp'%season,ylim=(0,max(25,max(finite_rates or [0])*115)))
        ax.tick_params(axis='x',labelsize=8)
    savefig(fig,'missed_and_bank_losses')
    # Reliability data can be list- or dictionary-valued; the exporter records keys explicitly.
    cal=json.loads((ROOT/'results/calibration.json').read_text())
    entries=cal if isinstance(cal,list) else list(cal.values())
    fig,axes=plt.subplots(1,2,figsize=(9,3.7))
    for ax,season in zip(axes,[4,5]):
        ax.plot([0,1],[0,1],'--',color='#88919B',lw=1)
        for item in entries:
            if item.get('season')!=season or item.get('rule')!=rule or item.get('seed')!=42 or item.get('method') not in ['proposed','single'] or item.get('scenario')!='nominal' or item.get('operating_point')!='scientific':continue
            bins=item.get('bins',item.get('diagnostic',{}).get('bins',[]))
            b=[v for v in bins if v['n']>0]
            if b:ax.plot([v['predicted'] for v in b],[v['observed'] for v in b],'o-',label=LABELS[item['method']],color=COLORS[item['method']])
        ax.set(title='Season %d: visited partial states'%season,xlabel='Predicted probability',ylabel='Observed material gain frequency',xlim=(0,1),ylim=(0,1))
        if ax.lines.__len__()>1:ax.legend(fontsize=8)
    savefig(fig,'calibration')
    # Example uses only the non-outcome development fixture used by the CLI/app.
    trace=json.loads((ROOT/'results/demo_trace.json').read_text())
    states=trace if isinstance(trace,list) else trace.get('trace',trace.get('states',[]))
    if states:
        states=[x for x in states if x.get('prediction') is not None]
        fig,ax=plt.subplots(figsize=(7.5,3.6))
        x=[s.get('pulses',s.get('pulse_count')) for s in states]
        ax.plot(x,[s['prediction'] for s in states],'o-',c=COLORS['proposed'])
        ax.set(xlabel='Simulated LED readings',ylabel='Predicted dry matter (%)',title='Real development example: sequential prediction')
        ax.set_xticks(x)
        for xi,s in zip(x,states):ax.annotate('stop' if s.get('stop') else 'continue',(xi,s['prediction']),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
        savefig(fig,'example_trace')
    g=predictions[(predictions.rule==rule)&(predictions.method=='proposed')&(predictions.seed==42)&(predictions.operating_point=='scientific')]
    fig,axes=plt.subplots(1,2,figsize=(9,3.5))
    for ax,season in zip(axes,[4,5]):
        s=g[g.season==season]
        stop=np.abs(s.y-s.prediction)-np.abs(s.y-s.bank_prediction)
        bankgain=np.abs(s.y-s.bank_prediction)-np.abs(s.y-s.rich_prediction)
        ax.hist(stop,bins=35,density=True,histtype='step',color=COLORS['proposed'],label='Stop gain')
        ax.hist(bankgain,bins=35,density=True,histtype='step',color=COLORS['single'],label='Bank loss')
        ax.axvline(.5,c='black',ls='--',lw=.8);ax.axvline(0,c='grey',lw=.7)
        ax.set(xlabel='Signed absolute-error difference (pp)',ylabel='Density',title='Season %d'%season);ax.legend(fontsize=8)
    savefig(fig,'signed_gains')


def conclusions(metrics,selection):
    rows=[]
    for season,a,b in main_rows(metrics,selection):
        gap=float(a.mean_pulses-b.mean_pulses);diff=float(a.rmsep-b.rmsep)
        accuracy=float(a.rmsep-a.bank_rmsep) if 'bank_rmsep' in a else None
        if accuracy is None:
            bankrow=subset(metrics,selection['primary_rule'],'full_bank',season,'reference')
            accuracy=float(a.rmsep-bankrow.rmsep)
        pulses=bool(a.mean_pulses<=6)
        acc=bool(accuracy<=.25)
        comparable=bool(abs(gap)<=.25)
        interpretation=('descriptive lower RMSEP' if diff<0 else 'no descriptive RMSEP improvement') if comparable else 'inconclusive: external budgets differ by more than 0.25 pulse'
        rows.append({'season':season,'n':int(a['n']),'proposed_rmsep':float(a.rmsep),'single_rmsep':float(b.rmsep),
                     'rmsep_difference':diff,'proposed_mean_pulses':float(a.mean_pulses),'single_mean_pulses':float(b.mean_pulses),
                     'pulse_difference':gap,'budget_comparable':comparable,'rmsep_increase_vs_bank':accuracy,
                     'prototype_accuracy_pass':acc,'prototype_pulses_pass':pulses,'prototype_both_pass':acc and pulses,
                     'objective_conclusion':interpretation,'missed_n':int(a.missed_n),'early_n':int(a.early_n),
                     'bank_loss_rate':float(a.bank_loss_rate)})
    return rows


def decision_report(metrics,selection,rows):
    lines=['# Decision report','',
           'These are scan-level, simulated-acquisition results on reused public harvest-season benchmarks. Error units are dry-matter percentage points (pp). The first table uses the separately frozen scientific operating points.',
           '', '| Season | Scans | Two-ref RMSEP | Single-ref RMSEP | Difference | Mean readings two / single | Within 0.25 pulse? | RMSEP increase vs bank | >=25% fewer readings? | <=0.25 pp increase? |',
           '|---|---:|---:|---:|---:|---:|---|---:|---|---|']
    for r in rows:
        lines.append('| {season} | {n} | {proposed_rmsep:.3f} | {single_rmsep:.3f} | {rmsep_difference:+.3f} | {proposed_mean_pulses:.3f} / {single_mean_pulses:.3f} | {budget_comparable} | {rmsep_increase_vs_bank:+.3f} | {prototype_pulses_pass} | {prototype_accuracy_pass} |'.format(**r))
    lines+=['','## Did the objective help?', '']
    for r in rows:lines.append('- Season %d: %s. Material missed corrections: %d/%d early stops.'%(r['season'],r['objective_conclusion'],r['missed_n'],r['early_n']))
    uncertainty=json.loads((ROOT/'results/external_uncertainty.json').read_text())
    lines+=['', '| Season | RMSEP difference, 95% cluster interval (pp) | Reading difference, 95% cluster interval | Conditional missed-rate difference, 95% interval |',
            '|---|---|---|---|']
    for season in [4,5]:
        u=uncertainty[str(season)+'|'+selection['primary_rule']+'|42']
        values=[]
        for j in range(3):
            interval=u.get('intervals')
            ci='['+num(interval[j][0])+', '+num(interval[j][1])+']' if interval and interval[j] else 'not estimated'
            values.append(num(u['point'][j])+'; '+ci)
        lines.append('| '+str(season)+' | '+' | '.join(values)+' |')
    group_metrics=pd.read_csv(ROOT/'results/external_group_metrics.csv')
    strata=group_metrics[(group_metrics.season==5)&(group_metrics.rule==selection['primary_rule'])&
                        (group_metrics.seed==42)&(group_metrics.scenario=='nominal')&
                        (group_metrics.operating_point=='scientific')&group_metrics.method.isin(['proposed','single'])]
    lines+=['', 'Season-5 harvest-population strata (no population-level interval):', '',
            '| Population | Method | Scans | RMSEP (pp) | Mean readings | Missed / early stops |',
            '|---|---|---:|---:|---:|---:|']
    for _,r in strata.sort_values(['group','method']).iterrows():
        lines.append('| %s | %s | %d | %.3f | %.3f | %d / %d |'%(r['group'],r.method,r['n'],r.rmsep,r.mean_pulses,r.missed_n,r.early_n))
    lines+=['','Use `results/external_uncertainty.json` for paired harvest-population bootstrap intervals. Season 5 has only two populations, so no population-level confidence interval is reported. Three seeds describe training variability separately. A point-estimate advantage alone is not a robust generalization claim.',
            '', '## Do these trade-offs justify a prototype?', '']
    both=all(r['prototype_both_pass'] for r in rows)
    lines.append('The two illustrative external engineering criteria '+('pass in both seasons.' if both else 'do not pass in both seasons.')+' Development screening '+('passed.' if selection['development_engineering_feasible'] else 'failed; the primary bank is the registered descriptive fallback.'))
    lines.append('The complete bank and rich-spectrum errors must also be considered: passing a relative bank criterion would not establish adequate absolute packhouse accuracy. No grower tolerance was independently established.')
    lines+=['', 'The separate frozen engineering operating point gives:', '',
            '| Season | RMSEP (pp) | Increase vs full bank (pp) | Mean readings | Reading reduction | Accuracy criterion | Reading criterion |',
            '|---|---:|---:|---:|---:|---|---|']
    for season in [4,5]:
        r=subset(metrics,selection['primary_rule'],'proposed',season,'engineering')
        increase=float(r.rmsep-r.bank_rmsep);reduction=1-float(r.mean_pulses)/8
        lines.append('| %d | %.3f | %+.3f | %.3f | %.2f%% | %s | %s |'%(season,r.rmsep,increase,r.mean_pulses,100*reduction,increase<=.25,reduction>=.25))
    lines+=['', 'Neither frozen operating point achieves both prototype criteria in both seasons. The scientific point saves readings but loses too much accuracy; the engineering point largely reads the complete bank.',
            '', '## Simpler controls and failure mechanism', '']
    for season in [4,5]:
        proposed=subset(metrics,selection['primary_rule'],'proposed',season)
        fixed=subset(metrics,selection['primary_rule'],'fixed_order',season)
        plsr=subset(metrics,selection['primary_rule'],'physical_plsr_4',season,'reference')
        svr=subset(metrics,selection['primary_rule'],'physical_sparse_svr_4',season,'reference')
        lines.append('- Season %d: fixed ordering gives %.3f pp at %.3f readings (versus %.3f pp at %.3f for learned ordering). Fixed four-LED PLSR gives %.3f pp and sparse SVR %.3f pp.'%(season,fixed.rmsep,fixed.mean_pulses,proposed.rmsep,proposed.mean_pulses,plsr.rmsep,svr.rmsep))
    lines.append('The ordering differences are descriptively small, and fixed-budget regressors expose substantial partial-prediction error. These results do not establish value for the extra adaptive controller complexity. Prioritize simpler fixed acquisition and improved prediction/calibration in a new development study; do not revise these frozen models using the external assays.')
    lines+=['','## Limits and next experiment','',
            '- No verified fruit identifiers: harvest populations are the grouping unit; repeated scans cannot establish unique fruit counts. Season 5 represents only two populations.',
            '- Prior local experiments scored the same seasons. This is a locked new analysis of reused benchmarks, not fresh independent replication.',
            '- The emulator uses digitized typical emitter plots and a flat detector/reference response. The F750 manual gives Log(1/Reflectance) without explicitly identifying the base; base 10 is the documented conventional assumption. Actual LED hardware measurements are required.',
            '- Bank-loss gains combine optical information limitations and differences in model fitting. Generic CNN and separately adapted Walsh CNN are distinct references; no published score is presented as a matched local result.',
            '- Two-step look-ahead is a conditional-Gaussian approximation, not the published ACO implementation. Hyperparameter search is deliberately bounded; full frontiers and unsuccessful models are retained.',
            '- Six journal leads have verified metadata but unavailable full methods. Literature overlap with early-exit loss gaps, dynamic feature selection and adaptive spectroscopy prevents a claim of absolute originality or patentability.',
            '', 'A physical follow-up should acquire adaptive and fixed scans on the same newly collected mangoes, obtain oven-dry reference measurements, measure photodiode/detector response, emission profiles, optical SNR, pulse energy, total time and placement repeatability, and evaluate a genuinely later harvest season. Favor fixed ordering if its frozen trade-off is comparable. If bank error dominates, improve optical coverage or transfer calibration before optimizing stopping.',
            '', '## Prior-art boundary','',
            'Jazbec et al. already formulate supervised early-versus-full loss gaps; Covert et al. learn conditional acquisition, Valancius et al. address non-greedy acquisition, and BAARC studies adaptive spectral acquisition. The contribution tested here is an empirical separation of bank-correctable error from richer-spectrum limitation. This is not a legal patent opinion; a specific implementation claim requires a jurisdiction-specific prior-art and claim analysis.',
            '', '## Evidence','',
            '`results/external_predictions.csv`, `results/external_metrics.csv`, `results/frozen_curves.csv`, `results/external_uncertainty.json`, `results/selection.json`, `results/frozen/manifest.json`, and `docs/literature_audit.md`.']
    (ROOT/'decision_report.md').write_text('\n'.join(lines)+'\n')


def table_latex(headers,rows,align=None):
    align=align or 'l'+'r'*(len(headers)-1)
    return '\n'.join([r'\begin{tabular}{'+align+'}',r'\toprule',' & '.join(map(tex,headers))+r' \\',r'\midrule']+
                     [' & '.join(map(tex,row))+r' \\' for row in rows]+[r'\bottomrule',r'\end{tabular}'])


def manuscript(metrics,selection,rows):
    folder=ROOT/'manuscript'
    folder.mkdir(exist_ok=True)
    cells=[]
    summary=[]
    for season,a,b in main_rows(metrics,selection):
        for method in ['proposed','single','full_bank','rich_pls','rich_cnn','walsh_adapted']:
            point='scientific' if method in ['proposed','single'] else 'reference'
            r=subset(metrics,selection['primary_rule'],method,season,point)
            summary.append([season,LABELS[method],num(r.rmsep),num(r.mae),num(r.bias),num(r.mean_pulses,2)])
            cells.append({'season':season,'rule':selection['primary_rule'],'seed':42,'method':method,'operating_point':point,'scenario':str(r.scenario),
                          'rmsep':float(r.rmsep),'mae':float(r.mae),'bias':float(r.bias),'mean_pulses':float(r.mean_pulses)})
    atomic_json(ROOT/'results/manuscript_cells.json',cells)
    (folder/'primary_table.tex').write_text(table_latex(['Season','Method','RMSEP','MAE','Bias','Readings'],summary,'llrrrr'))
    mechanism=[]
    for season,a,b in main_rows(metrics,selection):
        for label,r in [('Two-reference',a),('Single-reference',b)]:
            mechanism.append([season,label,str(int(r.missed_n))+'/'+str(int(r.early_n)),num(r.missed_rate,3),
                              num(r.early_fraction,3),str(int(r.bank_loss_n))+'/'+str(int(r['n']))])
    (folder/'mechanism_table.tex').write_text(table_latex(['Season','Method','Missed / early','Rate','Early fraction','Bank loss / scans'],mechanism,'llrrrr'))
    uncertainty=json.loads((ROOT/'results/external_uncertainty.json').read_text())
    uncertainty_rows=[]
    for season in [4,5]:
        u=uncertainty[str(season)+'|'+selection['primary_rule']+'|42']
        interval=u.get('intervals')
        for j,label in enumerate(['RMSEP difference (pp)','Mean reading difference','Conditional missed-rate difference']):
            missing_reason='Not estimated: %d populations'%u['n_groups'] if u['n_groups']<5 else 'Undefined conditional denominator'
            uncertainty_rows.append([season,label,num(u['point'][j]),
                '['+num(interval[j][0])+', '+num(interval[j][1])+']' if interval and interval[j] else missing_reason])
    (folder/'uncertainty_table.tex').write_text(table_latex(['Season','Paired estimand','Estimate','95% population-bootstrap interval'],uncertainty_rows,'llrl'))
    narrative=' '.join('In season %d, the two-reference and single-reference controllers had RMSEP %.3f and %.3f pp, with %.3f and %.3f mean readings, respectively.'%(r['season'],r['proposed_rmsep'],r['single_rmsep'],r['proposed_mean_pulses'],r['single_mean_pulses']) for r in rows)
    conclusion='Both illustrative prototype criteria held in both seasons.' if all(r['prototype_both_pass'] for r in rows) else 'The illustrative prototype criteria did not hold in both seasons.'
    objective=' '.join('Season %d was %s.'%(r['season'],r['objective_conclusion']) for r in rows)
    template=(ROOT/'manuscript/main_template.tex').read_text()
    template=template.replace('@@RESULTS@@',tex(narrative)).replace('@@CONCLUSION@@',tex(conclusion)).replace('@@OBJECTIVE@@',tex(objective))
    template=template.replace('@@BANKRULE@@',tex(selection['primary_rule'])).replace('@@DEVSCREEN@@','passed' if selection['development_engineering_feasible'] else 'failed')
    controls=[]
    controls_text=[]
    for season in [4,5]:
        for method,point in [('uncertainty','scientific'),('fixed_order','scientific'),('fixed_length','scientific'),
                             ('random_order','scientific'),('lookahead','scientific'),
                             ('physical_plsr_4','reference'),('physical_plsr_8','reference'),
                             ('physical_sparse_svr_4','reference'),('physical_sparse_svr_8','reference')]:
            r=subset(metrics,selection['primary_rule'],method,season,point)
            controls.append([season,LABELS.get(method,method.replace('_',' ')),num(r.rmsep),num(r.mean_pulses,2),num(r.early_fraction,3)])
            cells.append({'season':season,'rule':selection['primary_rule'],'seed':42,'method':method,'operating_point':point,'scenario':str(r.scenario),
                          'rmsep':float(r.rmsep),'mae':float(r.mae),'bias':float(r.bias),'mean_pulses':float(r.mean_pulses)})
        fixed=subset(metrics,selection['primary_rule'],'fixed_order',season)
        look=subset(metrics,selection['primary_rule'],'lookahead',season)
        controls_text.append('In season %d, fixed ordering with adaptive stopping achieved %.3f pp at %.3f readings, and the two-step look-ahead approximation achieved %.3f pp at %.3f readings.'%(season,fixed.rmsep,fixed.mean_pulses,look.rmsep,look.mean_pulses))
    (folder/'controls_table.tex').write_text(table_latex(['Season','Control/reference','RMSEP','Readings','Early fraction'],controls,'llrrr'))
    atomic_json(ROOT/'results/manuscript_cells.json',cells)
    template=template.replace('@@CONTROLS@@',tex(' '.join(controls_text)))
    calibration=json.loads((ROOT/'results/calibration.json').read_text())
    diagnostic_text=[]
    for season in [4,5]:
        briers={v['method']:v['brier'] for v in calibration.values() if v['season']==season and v['rule']==selection['primary_rule'] and v['seed']==42 and v['scenario']=='nominal' and v['operating_point']=='scientific' and v['method'] in ['proposed','single']}
        engineering=subset(metrics,selection['primary_rule'],'proposed',season,'engineering')
        plsr=subset(metrics,selection['primary_rule'],'physical_plsr_4',season,'reference')
        svr=subset(metrics,selection['primary_rule'],'physical_sparse_svr_4',season,'reference')
        diagnostic_text.append('Season %d visited-state Brier scores were %.3f and %.3f for the two-reference and single-reference targets. The engineering point used %.3f readings with RMSEP %.3f pp. Fixed four-LED PLSR and sparse SVR achieved %.3f and %.3f pp.'%(season,briers['proposed'],briers['single'],engineering.mean_pulses,engineering.rmsep,plsr.rmsep,svr.rmsep))
    template=template.replace('@@DIAGNOSTICS@@',tex(' '.join(diagnostic_text)))
    (folder/'main.tex').write_text(template)
    supplement(metrics,selection)
    commands=[]
    for stem in ['main','supplement']:
        for step in [['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'],
                     ['bibtex',stem],['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex'],
                     ['pdflatex','-interaction=nonstopmode','-halt-on-error',stem+'.tex']]:
            if step[0]=='bibtex' and stem=='supplement':continue
            result=subprocess.run(step,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            commands.append({'command':' '.join(step),'returncode':result.returncode})
            (folder/(stem+'_compile_'+step[0]+'.log')).write_text(result.stdout)
            if result.returncode:raise RuntimeError('TeX compilation failed: '+str(step)+'; inspect manuscript logs.')
    atomic_json(ROOT/'results/pdf_compilation.json',{'commands':commands,'status':'passed'})


def supplement(metrics,selection):
    rows=[]
    keep=metrics[(metrics.seed==42)&metrics.scenario.isin(['nominal','static'])&metrics.operating_point.isin(['scientific','reference','engineering'])]
    for _,r in keep.sort_values(['season','rule','operating_point','method']).iterrows():
        rows.append([int(r.season),r.rule,r.method,r.operating_point,num(r.rmsep),num(r.mean_pulses,2),num(r.missed_rate,3)])
    table=table_latex(['Season','Bank','Method','Point','RMSEP','Readings','Missed rate'],rows,'llllrrr').replace('tabular','longtable')
    seed_rows=[]
    seeds=metrics[(metrics.scenario=='nominal')&metrics.method.isin(['proposed','single'])&
                  (metrics.operating_point=='scientific')]
    for _,r in seeds.sort_values(['season','rule','seed','method']).iterrows():
        seed_rows.append([int(r.season),r.rule,int(r.seed),r.method,num(r.rmsep),num(r.mean_pulses,2),num(r.missed_rate,3)])
    seed_table=table_latex(['Season','Bank','Seed','Method','RMSEP','Readings','Missed rate'],seed_rows,'llrlrrr').replace('tabular','longtable')
    sensitivity_rows=[]
    sensitivities=metrics[~metrics.scenario.isin(['nominal','static'])]
    for _,r in sensitivities.sort_values(['season','scenario','method']).iterrows():
        sensitivity_rows.append([int(r.season),r.scenario,r.method,num(r.rmsep),num(r.mean_pulses,2),num(r.missed_rate,3)])
    sensitivity_table=table_latex(['Season','Scenario','Method','RMSEP','Readings','Missed rate'],sensitivity_rows,'lllrrr').replace('tabular','longtable')
    text=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=18mm]{geometry}\usepackage{booktabs,longtable,graphicx,hyperref,pdflscape}
\setlength{\belowcaptionskip}{5pt}
\begin{document}
\title{Supplement: adaptive mango spectral scanning}\author{Author review copy}\date{}\maketitle
\section{Complete registered comparisons}
All RMSEP values are dry-matter percentage points. Readings are simulated acquisition counts.
The scientific operating points target four mean development readings; engineering points use the registered constraints.
These settings were frozen before external scoring. Values are generated directly from the saved metrics table.
\begin{landscape}\scriptsize
@@TABLE@@
\normalsize\end{landscape}
\section{Training seeds and optical sensitivities}
All seeds use the same frozen development-selected operating indices. No seed is selected using external outcomes.
The response-shift rows apply the frozen physical predictor without retraining; ideal-point rows have their own development-fitted models and operating points.
Rich-reference reading counts denote grid features, not physical LED costs. Missing rates have a zero early-stop denominator.
\begin{landscape}\scriptsize
@@SEEDS@@
\clearpage
@@SENSITIVITIES@@
\normalsize\end{landscape}
\section{Detailed learning and optical methods}
The masked predictor has hidden layers 64 and 32 with ReLU activations. Inputs are standardized acquired values and a binary mask.
Unobserved standardized placeholders are zero; an acquired zero remains distinguishable through the mask.
Training uses 80 epochs and AdamW at 0.002. All 64 masks reachable from the two initial channels are enumerated for target generation;
63 nonterminal masks train each controller. Each scan receives equal weight across masks.
Three group-disjoint inner folds produce the assay-relative targets. No reference prediction for an acquired state was trained on that state's harvest population.
Controllers have a shared 64/32 encoder with binary stop, signed action-gain, and residual-error heads, trained for 25 epochs.
BCE and scaled action MSE have weight one; the auxiliary scaled residual MSE has weight 0.25.
The full bank uses autoscaled PLS with six components. The rich PLS reference uses row SNV, an 11-point quadratic second derivative and 12 components.
Full-spectrum preprocessing is used exclusively by the offline rich reference, never the sparse runtime controller.
A compact two-convolution CNN is the second target reference; a separate Walsh-architecture adaptation uses the checked author architecture.
Bank-design populations (15 percent of the non-calibration pool) are disjoint from fitting and calibration populations; isotonic mappings use complete sequential calibration paths, followed by outer-season evaluation.
The conditional-Gaussian two-step acquisition baseline uses training covariance and three synthetic draws per continuation; it never uses a replay fruit's hidden readings for an action.
The complete configuration, fold assignments, model settings and software versions accompany the frozen manifest.

Digitized LED profiles are typical manufacturer plots, not individual device measurements. Integration uses relative intensity and wavelength-bin widths.
The detector and reference response are flat assumptions. Base-10 absorbance is a conventional interpretation of the manufacturer's Log(1/Reflectance), not a verified firmware calibration.
Center shifts of three nm and width factors 0.9 and 1.1 are illustrative perturbations, not validated tolerances. Declared manufacturer center ranges are retained separately in the catalog.
Profile coverage is enforced at 95 percent; unsupported perturbations are explicitly excluded in the sensitivity records.

\section{Unsuccessful comparisons and uncertainty}
No outcome-driven threshold relaxation was allowed. All candidate bank scores and the full threshold frontier are retained in development\_scores.csv and development\_frontier.csv.
Three seeds (7,42,99) for the primary and independent-bank objective comparisons are reported in the external metrics file.
Their variability is distinct from paired harvest-population bootstrap uncertainty. Season 5 has only two harvest populations, so no population-level confidence interval is justified.
No development refinement was used solely to obtain favorable external outcomes. The pipeline retains a deliberately interrupted attempt to verify recovery and every failed attempt in its ledger.
The final manuscript cells are independently recomputed from the paired prediction file. Reporting-only generation never calls fitting code.

\section{Audit and source access}
The version-3 source contains 12,011 spectra, not 12,011 verified fruits. Its 103-channel comparison grid is exactly 684--990 nm in 3-nm increments.
Metadata include cultivar and temperature categories, but no fruit identifier or per-record instrument serial identifier. No exact common-grid duplicate spectra were found.
Earlier local work used the same external-season benchmarks, which is disclosed. No prior numerical results were used for the new model design.
Six journal records had bibliographic/abstract verification but inaccessible full methods: Gutierrez 2019, Anderson 2020, Mishra 2023, Yang 2025, Yang 2026 and Ma 2026.
The complete literature audit records which sources were read in full; inaccessible methods cannot establish absence of prior art.

\section{Software handoff and physical validation}
The application accepts one requested LED reading at a time. Its replay source is a real development example, with assay omitted from the distributed fixture.
The adapter read\_channel(led\_id) can be replaced with a real emitter/photodiode driver. No full spectrum or assay is required by the controller.
A future physical validation must compare adaptive and fixed acquisition on the same newly collected fruits with oven-dry reference values,
measured optical response, energy, acquisition time, placement repeatability and later-season transfer. Software replay cannot establish these quantities.
\end{document}
'''.replace('@@TABLE@@',table).replace('@@SEEDS@@',seed_table).replace('@@SENSITIVITIES@@',sensitivity_table)
    (ROOT/'manuscript/supplement.tex').write_text(text)


def generate_reports(force=False):
    completion=ROOT/'results/external_completion.json'
    if not completion.exists():raise RuntimeError('External scoring is incomplete; do not create manuscript result claims.')
    dependency_files=['results/external_completion.json','results/frozen/manifest.json',
                      'results/development_scores.csv','mango/reporting.py','mango/reporting_diagnostics.py',
                      'manuscript/main_template.tex','manuscript/references.bib']
    completion_record=json.loads(completion.read_text())
    for relative,expected in completion_record['outputs'].items():
        if digest(ROOT/relative)!=expected:raise RuntimeError('Changed scored reporting input: '+relative)
    key=canonical_hash({'files':{p:digest(ROOT/p) for p in dependency_files},
                        'trace':json.loads((ROOT/'results/demo_trace.json').read_text())['trace']})
    cache=ROOT/'results/report_generation.json'
    if cache.exists() and not force:
        previous=json.loads(cache.read_text())
        if previous.get('dependency')==key and previous.get('outputs') and all((ROOT/p).is_file() and digest(ROOT/p)==h for p,h in previous['outputs'].items()):
            event('Reporting artifacts unchanged and checksummed; reused verified PDFs without regeneration.')
            return
    metrics=pd.read_csv(ROOT/'results/external_metrics.csv')
    predictions=pd.read_csv(ROOT/'results/external_predictions.csv')
    selection=json.loads((ROOT/'results/frozen/selection.json').read_text())
    from .reporting_diagnostics import generate_diagnostics
    generate_diagnostics(ROOT)
    rows=conclusions(metrics,selection)
    atomic_json(ROOT/'results/decision_summary.json',rows)
    examples(predictions,selection)
    figures(metrics,predictions,selection)
    decision_report(metrics,selection,rows)
    manuscript(metrics,selection,rows)
    outputs=[ROOT/'decision_report.md']
    outputs+=list((ROOT/'figures').glob('*.pdf'))+list((ROOT/'figures').glob('*.png'))
    outputs+=[ROOT/'manuscript'/name for name in ['main.tex','main.pdf','supplement.tex','supplement.pdf',
              'primary_table.tex','mechanism_table.tex','uncertainty_table.tex','controls_table.tex']]
    from .reporting_diagnostics import ARTIFACTS
    outputs+=[ROOT/'results'/name for name in ARTIFACTS+['manuscript_cells.json','decision_summary.json',
              'illustrative_examples.json','bank_stability.json','pdf_compilation.json']]
    atomic_json(cache,{'status':'complete','dependency':key,'outputs':{str(p.relative_to(ROOT)):digest(p) for p in outputs}})
    event('Reporting-only generation complete: figures, decision report, manuscript and supplement; no models refitted.')


def examples(predictions,selection):
    rule=selection['primary_rule']
    primary=predictions[(predictions.rule==rule)&(predictions.method=='proposed')&(predictions.seed==42)&(predictions.operating_point=='scientific')]
    single=predictions[(predictions.rule==rule)&(predictions.method=='single')&(predictions.seed==42)&(predictions.operating_point=='scientific')]
    diagnostic=pd.read_csv(ROOT/'results/external_one_step_diagnostics.csv')
    records=[]
    for season in [4,5]:
        g=primary[primary.season==season].copy()
        for category,values,condition in [
            ('premature_stop',g.g_stop,(g.pulses<8)&(g.g_stop>.5)),
            ('full_bank_limitation',g.g_bank,g.g_bank>.5)]:
            candidates=g[condition].copy()
            if len(candidates):
                median=float(values[condition].median())
                column='g_stop' if category=='premature_stop' else 'g_bank'
                row=candidates.assign(distance=abs(candidates[column]-median)).sort_values(['distance','row_id']).iloc[0]
                other=single[(single.season==season)&(single.row_id==row.row_id)].iloc[0]
                records.append({'season':season,'category':category,'row_id':str(row.row_id),'group':str(row['group']),
                    'rule':'event nearest within-season median gain; stable row ID tie-break',
                    'assay':float(row.y),'proposed_prediction':float(row.prediction),'single_prediction':float(other.prediction),
                    'bank_prediction':float(row.bank_prediction),'rich_prediction':float(row.rich_prediction),
                    'proposed_pulses':int(row.pulses),'single_pulses':int(other.pulses),'g_stop':float(row.g_stop),'g_bank':float(row.g_bank)})
            else:records.append({'season':season,'category':category,'status':'no qualifying event'})
        c=diagnostic[(diagnostic.season==season)&(diagnostic.method=='proposed')&diagnostic.actually_continued&(diagnostic.actual_selected_gain>.5)].copy()
        if len(c):
            c['distance']=abs(c.actual_selected_gain-c.actual_selected_gain.median())
            selected=c.sort_values(['distance','row_id','pulses_before']).iloc[0]
            records.append({'season':season,'category':'useful_continuation','row_id':str(selected.row_id),
                            'pulses_before':int(selected.pulses_before),'actual_one_step_gain':float(selected.actual_selected_gain),
                            'rule':'continued material improvement nearest within-season median; row ID/depth tie-break'})
        else:records.append({'season':season,'category':'useful_continuation','status':'no qualifying event'})
    atomic_json(ROOT/'results/illustrative_examples.json',records)
    development=pd.read_csv(ROOT/'results/development_scores.csv')
    membership=development[(development.rule==rule)&(development.seed==42)][['fold','bank_indices']].drop_duplicates()
    catalog=json.loads((ROOT/'results/frozen/catalog.json').read_text())
    counts={c['id']:0 for c in catalog}
    for indices in membership.bank_indices:
        for i in map(int,indices.split(',')):counts[catalog[i]['id']]+=1
    atomic_json(ROOT/'results/bank_stability.json',{'selected_rule':rule,'fold_memberships':membership.to_dict('records'),'membership_count_out_of_3_folds':counts})
