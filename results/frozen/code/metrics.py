"""Assay errors, sequential mechanism metrics and paired grouped uncertainty."""
import numpy as np


def safe_rate(count, denominator):
    return float(count / denominator) if denominator else None


def regression(y, prediction):
    y, prediction = np.asarray(y), np.asarray(prediction)
    residual = prediction - y
    denom = np.sum((y - np.mean(y)) ** 2)
    return {'n': len(y), 'rmsep': float(np.sqrt(np.mean(residual ** 2))),
            'mae': float(np.mean(np.abs(residual))), 'bias': float(np.mean(residual)),
            'r2': float(1 - np.sum(residual ** 2) / denom) if denom > 0 else None}


def policy_metrics(y, prediction, pulses, bank_prediction, rich_prediction, capacity, delta=.5):
    out = regression(y, prediction)
    e, eb, ef = [np.abs(y - p) for p in (prediction, bank_prediction, rich_prediction)]
    early = np.asarray(pulses) < capacity
    missed = early & ((e - eb) > delta)
    out.update(mean_pulses=float(np.mean(pulses)), median_pulses=float(np.median(pulses)),
               p95_pulses=float(np.percentile(pulses, 95)), early_n=int(early.sum()),
               early_fraction=float(early.mean()), missed_n=int(missed.sum()),
               missed_rate=safe_rate(missed.sum(), early.sum()), missed_unconditional=float(missed.mean()),
               bank_loss_n=int(((eb - ef) > delta).sum()), bank_loss_rate=float(np.mean((eb - ef) > delta)),
               large_absolute_error_n=int((e > 2).sum()), large_absolute_error_rate=float(np.mean(e > 2)))
    return out


def paired_cluster_uncertainty(y, pa, pb, pulse_a, pulse_b, groups, bank, capacity, seed=42, n_boot=1000):
    y, pa, pb, pulse_a, pulse_b, groups, bank = [np.asarray(x) for x in (y, pa, pb, pulse_a, pulse_b, groups, bank)]
    unique = np.unique(groups)
    def values(idx):
        ea, eb, ebank = np.abs(y[idx]-pa[idx]), np.abs(y[idx]-pb[idx]), np.abs(y[idx]-bank[idx])
        early_a, early_b = pulse_a[idx] < capacity, pulse_b[idx] < capacity
        ma = safe_rate(np.sum(early_a & ((ea-ebank)>.5)), np.sum(early_a))
        mb = safe_rate(np.sum(early_b & ((eb-ebank)>.5)), np.sum(early_b))
        return [float(np.sqrt(np.mean(ea**2))-np.sqrt(np.mean(eb**2))),
                float(np.mean(pulse_a[idx]-pulse_b[idx])),
                None if ma is None or mb is None else ma-mb,
                float(np.mean(early_a & ((ea-ebank)>.5))-np.mean(early_b & ((eb-ebank)>.5)))]
    point = values(np.arange(len(y)))
    out = {'estimands': ['rmsep_difference', 'pulse_difference', 'conditional_missed_difference', 'unconditional_missed_difference'],
           'point': point, 'n_groups':len(unique), 'n_boot':n_boot,
           'scope':'harvest-population cluster resampling within this sampled season', 'intervals':None}
    if len(unique) < 5:
        out['scope'] = 'Only %d harvest populations: population-level confidence intervals suppressed; group-specific estimates supplied.' % len(unique)
        out['group_estimates'] = {str(g): values(np.flatnonzero(groups == g)) for g in unique}
        return out
    rng = np.random.RandomState(seed)
    indices = {g:np.flatnonzero(groups == g) for g in unique}
    samples=[]
    for _ in range(n_boot):
        idx = np.concatenate([indices[g] for g in rng.choice(unique, len(unique), replace=True)])
        samples.append(values(idx))
    out['intervals'] = []
    for k in range(4):
        s = [v[k] for v in samples if v[k] is not None]
        out['intervals'].append(np.percentile(s,[2.5,97.5]).tolist() if len(s) else None)
    return out
