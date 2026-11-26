"""Reporting-only consolidation of already frozen mango prediction exports.

No estimator, acquisition policy, subset, or operating point is fitted/selected.
The original held-season analysis and exploratory development revisions retain
their separate identities. This script never loads raw spectra or assays.
"""

from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'results'
MAN = HERE / 'manuscript'
FIG = HERE / 'figures'
SOURCES = {}
CELLS = []
CHECKS = []
P1 = 'results/'
P2 = 'revisions/methodology_v2/results/'
P3 = 'revisions/fixed_design_v3/results/'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1 << 20), b''):
            h.update(part)
    return h.hexdigest()


def source(relative):
    path = ROOT / relative
    if not path.is_file() or any(part in ('sealed', 'candidate_v4') for part in path.parts):
        raise ValueError('Unregistered evidence source: ' + relative)
    SOURCES[relative] = digest(path)
    return path


def csv(relative, **kwargs):
    return pd.read_csv(source(relative), **kwargs)


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(name, value):
    if not name.startswith('evidence'):
        raise ValueError(name)
    (OUT / name).write_text(json.dumps(clean(value), indent=2, sort_keys=True, allow_nan=False) + '\n')


def table_csv(name, rows):
    if not name.startswith('tables'):
        raise ValueError(name)
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / name, index=False, float_format='%.12g')
    return frame


def choose(frame, **filters):
    mask = np.ones(len(frame), dtype=bool)
    for name, value in filters.items():
        mask &= frame[name].to_numpy() == value
    result = frame.loc[mask].copy()
    if result.empty:
        raise AssertionError('Empty evidence selector: ' + repr(filters))
    return result


def check(name, actual, expected, tolerance=2e-8):
    actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if actual.shape != expected.shape or not np.allclose(actual, expected, rtol=0, atol=tolerance, equal_nan=True):
        raise AssertionError('%s: %r != %r' % (name, actual, expected))
    finite = np.isfinite(actual) & np.isfinite(expected)
    CHECKS.append({'name': name, 'n_values': int(actual.size),
                   'max_absolute_difference': float(np.max(np.abs(actual[finite] - expected[finite]))) if finite.any() else 0.,
                   'absolute_tolerance': tolerance})


def metrics(frame):
    if frame.row_id.duplicated().any():
        raise AssertionError('Duplicate prediction rows')
    residual = frame.prediction.to_numpy(float) - frame.y.to_numpy(float)
    bank = frame.bank_prediction.to_numpy(float) - frame.y.to_numpy(float)
    return {'n': len(frame), 'n_groups': frame.group.nunique(),
            'rmsep': float(np.sqrt(np.mean(residual ** 2))),
            'mae': float(np.mean(np.abs(residual))), 'bias': float(np.mean(residual)),
            'mean_pulses': float(frame.pulses.mean()),
            'bank_rmsep': float(np.sqrt(np.mean(bank ** 2))),
            'large_absolute_error_rate': float(np.mean(np.abs(residual) > 2))}


def cell(stage, prediction_source, metric_source, predictions, saved_metrics, filters):
    rows = choose(predictions, **filters)
    saved = choose(saved_metrics, **filters)
    if len(saved) != 1:
        raise AssertionError('Metric selector is not unique')
    actual = metrics(rows)
    for name, value in actual.items():
        if name in saved.columns:
            check(stage + ':' + repr(filters) + ':' + name, value, saved.iloc[0][name])
    CELLS.append({'stage': stage, 'prediction_source': prediction_source,
                  'metric_source': metric_source, 'filters': filters, 'recomputed': actual})
    return rows, actual


def aligned(a, b):
    a, b = a.set_index('row_id').sort_index(), b.set_index('row_id').sort_index()
    if not a.index.equals(b.index) or not np.array_equal(a.group, b.group):
        raise AssertionError('Paired rows/populations differ')
    check('paired assays', a.y.to_numpy(), b.y.to_numpy(), 1e-10)
    return a, b


def contrast(a, b):
    a, b = aligned(a, b)
    y = a.y.to_numpy(float)
    pa, pb = a.prediction.to_numpy(float), b.prediction.to_numpy(float)
    pulses = a.pulses.to_numpy(float) - b.pulses.to_numpy(float)
    groups = a.group.to_numpy()
    unique = np.unique(groups)
    result = {'n_groups': len(unique),
              'delta_rmsep': float(np.sqrt(np.mean((pa-y)**2)) - np.sqrt(np.mean((pb-y)**2))),
              'delta_pulses': float(np.mean(pulses))}
    result['budget_comparable'] = abs(result['delta_pulses']) <= .25
    result.update(rmsep_ci_low=None, rmsep_ci_high=None, pulses_ci_low=None, pulses_ci_high=None)
    if len(unique) >= 5:
        # Independent reconstruction expands sampled populations into paired rows.
        indices = [np.flatnonzero(groups == group) for group in unique]
        rng = np.random.RandomState(42)
        boot = []
        for _ in range(1000):
            ids = np.concatenate([indices[i] for i in rng.randint(len(unique), size=len(unique))])
            boot.append([np.sqrt(np.mean((pa[ids]-y[ids])**2)) - np.sqrt(np.mean((pb[ids]-y[ids])**2)),
                         np.mean(pulses[ids])])
        lower, upper = np.percentile(boot, [2.5, 97.5], axis=0)
        result.update(rmsep_ci_low=float(lower[0]), rmsep_ci_high=float(upper[0]),
                      pulses_ci_low=float(lower[1]), pulses_ci_high=float(upper[1]))
    return result


def verify_contrast(actual, saved, name):
    for field in ('delta_rmsep', 'delta_pulses', 'rmsep_ci_low', 'rmsep_ci_high', 'pulses_ci_low', 'pulses_ci_high'):
        if actual[field] is not None and field in saved:
            check(name + ':' + field, actual[field], saved[field])


def tex(name, specification, header, rows):
    if not name.startswith('generated_'):
        raise ValueError(name)
    text = ['% Generated from independently reconstructed frozen prediction exports.',
            '\\begin{tabular}{' + specification + '}', '\\toprule',
            ' & '.join(header) + ' \\\\', '\\midrule']
    text += [' & '.join(row) + ' \\\\' for row in rows]
    text += ['\\bottomrule', '\\end{tabular}', '']
    (MAN / name).write_text('\n'.join(text))


def estimate(value, low, high):
    return '%.3f [%.3f, %.3f]' % (value, low, high)


def main():
    for folder in (OUT, MAN, FIG):
        folder.mkdir(parents=True, exist_ok=True)
    p1 = csv(P1 + 'external_predictions.csv')
    m1 = csv(P1 + 'external_metrics.csv')
    u1 = json.loads(source(P1 + 'external_uncertainty.json').read_text())
    p2 = csv(P2 + 'policy_predictions.csv.gz')
    m2 = csv(P2 + 'policy_metrics.csv')
    e2 = csv(P2 + 'endpoint_summary.csv')
    c2 = csv(P2 + 'paired_comparisons.csv')
    p3 = csv(P3 + 'predictions.csv.gz')
    m3 = csv(P3 + 'metrics.csv')
    c3 = csv(P3 + 'comparisons.csv')
    primary, diagnostics, fixed, stopping, comparisons, sensitivity, curve_rows = [], [], [], [], [], [], []

    methods = [
        ('Two-reference, scientific', 'nominal', 'proposed', 'scientific'),
        ('Single-reference, scientific', 'nominal', 'single', 'scientific'),
        ('Two-reference, engineering', 'nominal', 'proposed', 'engineering'),
        ('Complete-bank PLS', 'nominal', 'full_bank', 'reference'),
        ('Full-spectrum PLS', 'nominal', 'rich_pls', 'reference'),
        ('Full-spectrum CNN', 'nominal', 'rich_cnn', 'reference'),
        ('Uncertainty stopping', 'nominal', 'uncertainty', 'scientific'),
        ('Random acquisition order', 'nominal', 'random_order', 'scientific'),
        ('Two-step lookahead', 'nominal', 'lookahead', 'scientific'),
        ('Fixed four, masked MLP', 'nominal', 'fixed_length', 'scientific'),
        ('Fixed four, PLS', 'static', 'physical_plsr_4', 'reference'),
        ('Fixed four, sparse SVR', 'static', 'physical_sparse_svr_4', 'reference'),
        ('Adapted full-spectrum CNN', 'static', 'walsh_adapted', 'reference')]
    primary_tex = []
    for label, scenario, method, point in methods:
        display = [label]
        for season in (4, 5):
            filters = dict(season=season, rule='swap_mid', seed=42, scenario=scenario,
                           method=method, operating_point=point)
            rows, values = cell('original_held_season', P1+'external_predictions.csv',
                                P1+'external_metrics.csv', p1, m1, filters)
            primary.append(dict(label=label, **filters, **values))
            count = '--' if method in ('rich_pls', 'rich_cnn', 'walsh_adapted') else '%.3f' % values['mean_pulses']
            display += ['%.3f' % values['rmsep'], count]
        primary_tex.append(display)
    tex('generated_primary.tex', 'lrrrr', ['Method', 'S4 RMSEP', 'S4 readings', 'S5 RMSEP', 'S5 readings'], primary_tex)
    for season in (4, 5):
        base = dict(season=season, rule='swap_mid', seed=42, scenario='nominal', operating_point='scientific')
        actual = contrast(choose(p1, method='proposed', **base), choose(p1, method='single', **base))
        saved = u1['%d|swap_mid|42' % season]
        check('original contrast point S%d' % season, [actual['delta_rmsep'],actual['delta_pulses']], saved['point'][:2])
        if saved['intervals']:
            check('original contrast CI S%d' % season,
                  [actual['rmsep_ci_low'],actual['rmsep_ci_high'],actual['pulses_ci_low'],actual['pulses_ci_high']],
                  saved['intervals'][0] + saved['intervals'][1])
        comparisons.append(dict(stage='original', season=season, bank='swap_mid', family='mlp_hybrid',
                                comparison='two_minus_single', operating_point='scientific', **actual))

    diagnostic_tex = []
    for bank in ('swap_mid', 'uniform'):
        for season in (1, 2, 3):
            base = dict(held_season=season, bank=bank, seed=42, objective='fixed_length')
            frames = []
            for family, depth in (('mlp_hybrid',7), ('pls',7), ('pls',8)):
                rows, _ = cell('exploratory_v2', P2+'policy_predictions.csv.gz', P2+'policy_metrics.csv',
                               p2,m2,dict(base,family=family,operating_point='depth_%d'%depth))
                frames.append(rows.set_index('row_id').sort_index())
            a,b,c = frames
            if not a.index.equals(b.index) or not a.index.equals(c.index):
                raise AssertionError('Endpoint rows differ')
            ea,eb,ec = [np.abs(a.y.to_numpy(float)-frame.prediction.to_numpy(float)) for frame in frames]
            values = dict(total=ea-ec,estimator=ea-eb,measurement=eb-ec)
            check('endpoint additive identity', values['total'], values['estimator']+values['measurement'],1e-12)
            groups=a.group.to_numpy();unique=np.unique(groups)
            ids=[np.flatnonzero(groups==g) for g in unique]
            rng=np.random.RandomState(42);boot=[]
            for _ in range(1000):
                draw=np.concatenate([ids[i] for i in rng.randint(len(unique),size=len(unique))])
                boot.append([values[k][draw].mean() for k in ('total','estimator','measurement')])
            lower,upper=np.percentile(boot,[2.5,97.5],axis=0)
            result=dict(held_season=season,bank=bank,seed=42,n=len(a),n_groups=len(unique))
            saved=choose(e2,held_season=season,bank=bank,seed=42).iloc[0]
            display=['Primary' if bank=='swap_mid' else 'Uniform',str(season)]
            for j,key in enumerate(('total','estimator','measurement')):
                for suffix,value in (('mean',values[key].mean()),('ci_low',lower[j]),('ci_high',upper[j])):
                    result[key+'_'+suffix]=float(value)
                    check('endpoint %s S%d %s%s'%(bank,season,key,suffix),value,saved[key+'_'+suffix])
                display.append(estimate(result[key+'_mean'],lower[j],upper[j]))
            diagnostics.append(result);diagnostic_tex.append(display)
    tex('generated_diagnostics.tex','llrrr',['Bank','Season','Total','Estimator switch','Additional reading'],diagnostic_tex)
    for season in (1,2,3):
        for family in ('mlp_hybrid','pls','ridge'):
            base=dict(held_season=season,bank='swap_mid',seed=42,family=family,operating_point='scientific')
            a=choose(p2,objective='two_reference',**base);b=choose(p2,objective='single_reference',**base)
            actual=contrast(a,b)
            saved=choose(c2,comparison='two_minus_single',**base).iloc[0]
            verify_contrast(actual,saved,'v2 stopping %s S%d'%(family,season))
            comparisons.append(dict(stage='v2',season=season,bank='swap_mid',family=family,
                                    comparison='two_minus_single',operating_point='scientific',**actual))

    fixed_tex=[];stopping_tex=[]
    for season in (1,2,3):
        base=dict(held_season=season,bank='swap_mid',family='pls')
        chosen={}
        for label,variant,depth in [('catalog4','catalog',4),('designed4','designed',4),
                                    ('selected4','selected_subset',4),('selected6','selected_subset',6),
                                    ('full8','catalog',8)]:
            filters=dict(base,variant=variant,objective='fixed_length',operating_point='depth_%d'%depth)
            rows,values=cell('exploratory_v3',P3+'predictions.csv.gz',P3+'metrics.csv',p3,m3,filters)
            chosen[label]=(rows,values)
        result=dict(held_season=season,bank='swap_mid',family='pls')
        for label,(_,values) in chosen.items():
            result.update({label+'_'+key:value for key,value in values.items()})
        for label,comparison,a,b,depth in [
                ('designed4','designed_fixed_minus_catalog','designed4','catalog4',4),
                ('selected4','selected_subset_minus_catalog','selected4','catalog4',4)]:
            actual=contrast(chosen[a][0],chosen[b][0])
            saved=choose(c3,comparison=comparison,operating_point='depth_%d'%depth,**base).iloc[0]
            verify_contrast(actual,saved,'v3 '+label+' S%d'%season)
            comparisons.append(dict(stage='v3',season=season,bank='swap_mid',family='pls',
                                    comparison=comparison,operating_point='depth_%d'%depth,**actual))
            if label=='designed4':
                result.update({'contrast_'+key:value for key,value in actual.items()})
        result['selected6_relative_screen_pass']=bool(result['selected6_rmsep'] <= result['full8_rmsep']+.25)
        fixed.append(result)
        fixed_tex.append([str(season)]+['%.3f'%result[label+'_rmsep'] for label in ('catalog4','designed4','selected6','full8')]+
                         [estimate(result['contrast_delta_rmsep'],result['contrast_rmsep_ci_low'],result['contrast_rmsep_ci_high'])])
        two,mtwo=cell('exploratory_v3',P3+'predictions.csv.gz',P3+'metrics.csv',p3,m3,
                     dict(base,variant='designed',objective='two_reference',operating_point='scientific'))
        single,msingle=cell('exploratory_v3',P3+'predictions.csv.gz',P3+'metrics.csv',p3,m3,
                           dict(base,variant='designed',objective='single_reference',operating_point='scientific'))
        actual=contrast(two,single)
        saved=choose(c3,comparison='two_minus_single',operating_point='scientific',**base).iloc[0]
        verify_contrast(actual,saved,'v3 stopping S%d'%season)
        row=dict(base,**{'two_'+k:v for k,v in mtwo.items()},**{'single_'+k:v for k,v in msingle.items()},**actual)
        stopping.append(row)
        comparisons.append(dict(stage='v3',season=season,bank='swap_mid',family='pls',
                                comparison='two_minus_single',operating_point='scientific',**actual))
        stopping_tex.append([str(season),'%.3f / %.3f'%(mtwo['rmsep'],mtwo['mean_pulses']),
                             '%.3f / %.3f'%(msingle['rmsep'],msingle['mean_pulses']),
                             estimate(actual['delta_rmsep'],actual['rmsep_ci_low'],actual['rmsep_ci_high']),
                             '%.3f'%actual['delta_pulses']])
        for variant in ('catalog','designed','selected_subset'):
            for depth in range(2,9):
                _,value=cell('exploratory_v3',P3+'predictions.csv.gz',P3+'metrics.csv',p3,m3,
                             dict(base,variant=variant,objective='fixed_length',operating_point='depth_%d'%depth))
                curve_rows.append(dict(held_season=season,variant=variant,depth=depth,**value))
    tex('generated_fixed.tex','lrrrrr',['Season','Catalog 4','Designed 4','Selected 6','Full 8','Designed 4 minus catalog 4'],fixed_tex)
    tex('generated_stopping.tex','lrrrr',['Season','Two: RMSEP / readings','Single: RMSEP / readings','RMSEP difference [95\\% CI]','Reading difference'],stopping_tex)
    for bank in ('swap_mid','uniform'):
        for family in ('pls','ridge'):
            for season in (1,2,3):
                for variant,depth in [('catalog',4),('designed',4),('selected_subset',4),('selected_subset',6),('catalog',8)]:
                    filters=dict(held_season=season,bank=bank,family=family,variant=variant,
                                 objective='fixed_length',operating_point='depth_%d'%depth)
                    _,values=cell('exploratory_v3',P3+'predictions.csv.gz',P3+'metrics.csv',p3,m3,filters)
                    sensitivity.append(dict(**filters,**values))

    tables={name:table_csv('tables_'+name+'.csv',rows) for name,rows in
            [('primary',primary),('diagnostics',diagnostics),('fixed',fixed),('stopping',stopping),
             ('comparisons',comparisons),('sensitivity',sensitivity),('fixed_curves',curve_rows)]}
    plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':200})
    fig,axes=plt.subplots(1,3,figsize=(7.3,2.75),sharey=True)
    styles=[('catalog','Catalog order','#0072B2','o','-'),
            ('designed','Designed order','#D55E00','s','-'),
            ('selected_subset','Selected subsets (not nested)','#009E73','^','--')]
    curves=tables['fixed_curves']
    for season,ax in zip((1,2,3),axes):
        for variant,label,color,marker,style in styles:
            part=choose(curves,held_season=season,variant=variant).sort_values('depth')
            ax.plot(part.depth,part.rmsep,label=label,color=color,marker=marker,linestyle=style,markersize=3,linewidth=1.1)
        ax.set(title='Development season %d'%season,xlabel='Fixed reading count',xticks=range(2,9))
        ax.grid(alpha=.18)
    axes[0].set_ylabel('RMSEP (dry-matter pp)')
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,-.01))
    fig.tight_layout(rect=[0,.10,1,1])
    save_figure(fig,'fixed_budget_results')

    comp=tables['comparisons']
    comp=comp[(comp.comparison=='two_minus_single')&((comp.stage=='original')|(comp.family=='pls'))].copy()
    labels=[('Original held S%d'%r.season if r.stage=='original' else
             '%s development S%d'%('Matched PLS' if r.stage=='v2' else 'Designed PLS',r.season)) for r in comp.itertuples()]
    fig,axes=plt.subplots(1,2,figsize=(7.3,3.6),sharey=True,gridspec_kw={'width_ratios':[1,1]})
    positions=np.arange(len(comp))
    colors={'original':'#0072B2','v2':'#CC79A7','v3':'#D55E00'}
    for j,row in enumerate(comp.itertuples()):
        for ax,prefix in zip(axes,('rmsep','pulses')):
            point=getattr(row,'delta_'+prefix);low=getattr(row,prefix+'_ci_low');high=getattr(row,prefix+'_ci_high')
            if pd.notna(low):
                ax.errorbar(point,j,xerr=[[point-low],[high-point]],fmt='o',color=colors[row.stage],capsize=2,markersize=4)
            else:
                ax.plot(point,j,'D',color=colors[row.stage],markersize=4)
    axes[0].set_yticks(positions,labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel('Two minus single RMSEP (pp)')
    axes[1].set_xlabel('Two minus single mean readings')
    axes[1].axvspan(-.25,.25,color='grey',alpha=.15,label='Registered comparability margin')
    for ax in axes:
        ax.axvline(0,color='.35',lw=.7,ls='--');ax.grid(axis='x',alpha=.18)
    fig.legend(*axes[1].get_legend_handles_labels(),loc='lower center',
               bbox_to_anchor=(.73,-.01),fontsize=6,frameon=False)
    fig.tight_layout(rect=[0,.05,1,1])
    save_figure(fig,'controlled_contrasts')

    for relative,before in SOURCES.items():
        if digest(ROOT/relative)!=before:
            raise AssertionError('Prior evidence changed: '+relative)
    write_json('evidence_cells.json',{'cells':CELLS,'checks':CHECKS})
    artifacts=sorted([*OUT.glob('tables*.csv'),*MAN.glob('generated_*.tex'),*FIG.glob('*.pdf'),*FIG.glob('*.png'),OUT/'evidence_cells.json'])
    write_json('evidence_manifest.json',{
        'status':'PASS','analysis_kind':'reporting-only reuse of frozen prediction exports',
        'raw_data_loaded':False,'fitting_performed':False,'candidate_v4_scores_used':False,
        'source_sha256':SOURCES,'build_code_sha256':digest(__file__),
        'artifact_sha256':{str(path.relative_to(HERE)):digest(path) for path in artifacts},
        'recomputed_policy_cells':len(CELLS),'check_count':len(CHECKS),
        'checked_numeric_values':sum(record['n_values'] for record in CHECKS),
        'tables':{name:{'rows':len(frame),'columns':list(frame.columns)} for name,frame in tables.items()},
        'interval_method':'1000 paired population bootstrap draws, seed42; actual row expansion; suppressed for two-population season5',
        'interpretation_limits':['Original frozen held seasons4/5 belong to the same public dataset.',
                                 'Revisions2/3 are exploratory reuse of development seasons1–3.',
                                 'Subset minima do not constitute fresh validation.',
                                 'Full-spectrum references are not charged as LED readings in the manuscript table.',
                                 'Simulated acquisition counts are not physical energy or hardware timings.']})
    print('Evidence PASS: %d policy cells, %d checks, %d scalar values; no fitting.'%
          (len(CELLS),len(CHECKS),sum(record['n_values'] for record in CHECKS)))


def save_figure(fig,name):
    fig.savefig(FIG/(name+'.png'),bbox_inches='tight')
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    plt.close(fig)


if __name__=='__main__':
    main()
