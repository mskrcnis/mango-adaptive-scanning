# Data underlying the main figures

These CSVs contain the plotted values. They are extracts or deterministic representations of previously verified outputs, not new model evaluations.

- Figure 1: existing response_weights calculation on the 103-channel grid, peak-normalized per emitter to reproduce the original plot. Profiles at 720, 760, 780, 800, 820, 890, 910 and 940 nm form the primary bank; 740 and 850 nm are catalog alternatives.
- Figure 2: original frozen threshold curves (nominal, swap_mid, seed 42, five policies, two seasons) and the four frozen scientific operating points. Only line/marker presentation changed for monochrome readability.
- Figure 3: v5 tables_fixed_curves.csv, copied unchanged.
- Figure 4: v5 tables_comparisons.csv filtered to two_minus_single and original or PLS rows, exactly as the original figure builder. Season 5 intervals remain absent.

The PDFs for Figures 1, 3 and 4 retain the verified v5 bytes. `prepare_figures.py` rebuilds the restyled Figure 2 using only these included CSVs.
