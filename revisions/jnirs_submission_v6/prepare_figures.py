#!/usr/bin/env python3
"""Restyle an existing frozen result figure; no fitting or evaluation occurs."""
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
