#!/usr/bin/env python3
"""Format frozen result figures; no fitting or evaluation occurs."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
curves = pd.read_csv(HERE / 'figure_data/Figure_2_curves.csv')
points = pd.read_csv(HERE / 'figure_data/Figure_2_operating_points.csv')
styles = {
    'proposed': ('Bank-reference', '#126E75', 'o', '-'),
    'single': ('Rich-reference', '#BF553E', 's', '--'),
    'uncertainty': ('Residual uncertainty', '#7656A0', '^', ':'),
    'fixed_order': ('Fixed order + stopping', '#586F3E', 'v', '-.'),
    'lookahead': ('Two-step look-ahead', '#A07820', 'D', (0, (5, 2, 1, 2))),
}
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False,
                     'axes.spines.right': False, 'font.family': 'DejaVu Sans',
                     'pdf.fonttype': 42, 'ps.fonttype': 42})
fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.8))
for ax, season in zip(axes, [4, 5]):
    for method, (label, color, marker, linestyle) in styles.items():
        part = curves[(curves.season == season) & (curves.method == method)].sort_values('mean_pulses')
        assert len(part) == 21
        ax.plot(part.mean_pulses, part.rmsep, label=label, color=color,
                marker=marker, linestyle=linestyle, markersize=3,
                markerfacecolor='white', markeredgewidth=.7, linewidth=1.2)
    for method in ['proposed', 'single']:
        point = points[(points.season == season) & (points.method == method)]
        assert len(point) == 1
        ax.scatter(point.mean_pulses, point.rmsep, s=90, marker='*',
                   color=styles[method][1], zorder=10, edgecolor='black', linewidth=.5)
    ax.set(title=f'Season {season}', xlabel='Mean simulated LED readings',
           ylabel='RMSEP (dry-matter pp)', xlim=(1.8, 8.2))
    ax.grid(alpha=.15)
fig.legend(*axes[1].get_legend_handles_labels(), loc='lower center',
           ncol=3, frameon=False, fontsize=8)
fig.tight_layout(rect=[0, .15, 1, 1])
fig.savefig(HERE / 'figures/Figure_2.pdf', bbox_inches='tight',
            metadata={'CreationDate': None, 'ModDate': None})
plt.close(fig)
print('Rebuilt Figure_2.pdf from the frozen plotted values.')

# Retain the frozen contrast values, row order and styling. Source stage keys
# are provenance identifiers only; the reader-facing labels name the analysis.
contrasts = pd.read_csv(HERE / 'figure_data/Figure_4_contrasts.csv')
assert len(contrasts) == 8
assert contrasts.comparison.eq('two_minus_single').all()
assert list(zip(contrasts.stage, contrasts.season)) == [
    ('original', 4), ('original', 5),
    ('v2', 1), ('v2', 2), ('v2', 3),
    ('v3', 1), ('v3', 2), ('v3', 3),
]
labels = [
    ('Benchmark season %d' % row.season if row.stage == 'original' else
     '%s development S%d' % (
         'Matched PLS' if row.stage == 'v2' else 'Designed PLS', row.season))
    for row in contrasts.itertuples()
]
with plt.rc_context({'font.size': 8, 'savefig.dpi': 200}):
    fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.6), sharey=True,
                             gridspec_kw={'width_ratios': [1, 1]})
    colors = {'original': '#0072B2', 'v2': '#CC79A7', 'v3': '#D55E00'}
    for position, row in enumerate(contrasts.itertuples()):
        for ax, prefix in zip(axes, ('rmsep', 'pulses')):
            point = getattr(row, 'delta_' + prefix)
            low = getattr(row, prefix + '_ci_low')
            high = getattr(row, prefix + '_ci_high')
            if pd.notna(low):
                ax.errorbar(point, position,
                            xerr=[[point - low], [high - point]], fmt='o',
                            color=colors[row.stage], capsize=2, markersize=4)
            else:
                ax.plot(point, position, 'D', color=colors[row.stage], markersize=4)
    axes[0].set_yticks(range(len(contrasts)), labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel('Two minus single RMSEP (pp)')
    axes[1].set_xlabel('Two minus single mean readings')
    axes[1].axvspan(-.25, .25, color='grey', alpha=.15,
                   label='Registered comparability margin')
    for ax in axes:
        ax.axvline(0, color='.35', lw=.7, ls='--')
        ax.grid(axis='x', alpha=.18)
    fig.legend(*axes[1].get_legend_handles_labels(), loc='lower center',
               bbox_to_anchor=(.73, -.01), fontsize=6, frameon=False)
    fig.tight_layout(rect=[0, .05, 1, 1])
    fig.savefig(HERE / 'figures/Figure_4.pdf', bbox_inches='tight',
                metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)
print('Rebuilt Figure_4.pdf from the frozen plotted values with analysis labels.')
