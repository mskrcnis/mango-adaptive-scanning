"""Group-disjoint target generation and bounded sequential learning.

Every target-producing predictor is fitted without the target group's rows.
No fitting function accepts a season label or external evaluation outcomes.
"""
import copy
import time
from itertools import combinations

import numpy as np
import torch
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from torch import nn

from .models import (MaskedMLP, GainController, SpectralCNN, PLSReference,
                     observed_input, partial_predict, predict_bank, predict_rich,
                     controller_outputs, predicted_error)


DEFAULT_CONFIG = {
    'inner_folds': 3, 'predictor_epochs': 80, 'controller_epochs': 25,
    'cnn_epochs': 55, 'batch_size': 2048, 'learning_rate': 0.002,
    'threads': 2, 'device': 'cuda', 'delta': 0.50, 'bank_components': 6,
    'rich_components': 12, 'group_equal_weight': True, 'include_cnn': True,
    'initial_indices': None, 'lookahead_draws': 3,
}


def reachable_masks(width, initial_indices):
    initial = tuple(sorted(initial_indices))
    remaining = [j for j in range(width) if j not in initial]
    masks = []
    for count in range(len(remaining) + 1):
        for subset in combinations(remaining, count):
            mask = np.zeros(width, dtype=bool)
            mask[list(initial) + list(subset)] = True
            masks.append(mask)
    return np.stack(masks)


def _weights(groups, equal=True):
    if not equal:
        return np.ones(len(groups), dtype=np.float32)
    _, inv, counts = np.unique(groups, return_inverse=True, return_counts=True)
    result = 1.0 / counts[inv]
    return (result / result.mean()).astype(np.float32)


def _device(config):
    requested = config['device']
    return torch.device(requested if requested != 'cuda' or torch.cuda.is_available() else 'cpu')


def _fit_predictors(xbank, xfull, y, groups, seed, config):
    phase_started = time.perf_counter()
    phase_timings = {}
    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)
    width = xbank.shape[1]
    initial = config['initial_indices'] or [0, width - 1]
    masks = reachable_masks(width, initial)
    scaler = StandardScaler().fit(xbank)
    rich_scaler = StandardScaler().fit(xfull)
    ys = float(max(np.std(y), 1e-6))
    ym = float(np.mean(y))
    device = _device(config)
    xt = torch.as_tensor(scaler.transform(xbank), dtype=torch.float32, device=device)
    yt = torch.as_tensor((y - ym) / ys, dtype=torch.float32, device=device)
    wt = torch.as_tensor(_weights(groups, config['group_equal_weight']), device=device)
    mt = torch.as_tensor(masks[:-1], dtype=torch.float32, device=device)
    model = MaskedMLP(width).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=1e-4)
    batch_size = config['batch_size']
    for epoch in range(config['predictor_epochs']):
        order = rng.permutation(len(y))
        selected_masks = rng.randint(0, len(mt), len(y))
        for start in range(0, len(y), batch_size):
            ids = torch.as_tensor(order[start:start + batch_size], device=device)
            mask_ids = torch.as_tensor(selected_masks[start:start + batch_size], device=device)
            mask = mt[mask_ids]
            features = torch.cat([xt[ids] * mask, mask], dim=1)
            pred = model(features)
            loss = (((pred - yt[ids]) ** 2) * wt[ids]).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    phase_timings['masked_mlp_seconds'] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    bundle = {'scaler': scaler, 'y_mean': ym, 'y_scale': ys,
              'masked_predictor': model.cpu().eval(),
              'bank_predictor': PLSReference(config['bank_components']).fit(xbank, y),
              'rich_predictor': PLSReference(config['rich_components'], use_snv=True, derivative=True).fit(xfull, y),
              'rich_scaler': rich_scaler, 'initial_indices': initial, 'masks': masks}
    phase_timings['pls_references_seconds'] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    if config['include_cnn']:
        torch.manual_seed(seed + 19)
        model_cnn = SpectralCNN(xfull.shape[1]).to(device)
        xf = torch.as_tensor(rich_scaler.transform(xfull), dtype=torch.float32, device=device)
        optimizer = torch.optim.AdamW(model_cnn.parameters(), lr=config['learning_rate'], weight_decay=1e-3)
        for epoch in range(config['cnn_epochs']):
            order = rng.permutation(len(y))
            for start in range(0, len(y), batch_size):
                ids = torch.as_tensor(order[start:start + batch_size], device=device)
                pred = model_cnn(xf[ids])
                loss = (((pred - yt[ids]) ** 2) * wt[ids]).mean()
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        bundle['rich_cnn'] = model_cnn.cpu().eval()
    phase_timings['cnn_seconds'] = time.perf_counter() - phase_started
    bundle['phase_timings'] = phase_timings
    return bundle


def _all_mask_predictions(bundle, xbank):
    predictions = []
    for mask in bundle['masks']:
        repeated = np.broadcast_to(mask, xbank.shape)
        predictions.append(partial_predict(bundle, xbank, repeated))
    return np.stack(predictions, axis=1)


def fit_bundle(Xchannels, Xfull, y, groups, bank_indices, seed=42, config=None):
    started = time.perf_counter()
    settings = dict(DEFAULT_CONFIG)
    if config:
        settings.update(config)
    torch.set_num_threads(int(settings['threads']))
    torch.use_deterministic_algorithms(True, warn_only=True)
    xbank = np.asarray(Xchannels, dtype=np.float32)[:, bank_indices]
    xfull = np.asarray(Xfull, dtype=np.float32)
    y = np.asarray(y, dtype=np.float32)
    groups = np.asarray(groups).astype(str)
    if not (np.isfinite(xbank).all() and np.isfinite(xfull).all() and np.isfinite(y).all()):
        raise ValueError('Training inputs and assays must be finite')
    if len(np.unique(groups)) < 2:
        raise ValueError('At least two verified training groups are needed for OOF labels')
    width = xbank.shape[1]
    settings['initial_indices'] = settings['initial_indices'] or [0, width - 1]
    masks = reachable_masks(width, settings['initial_indices'])
    nstates = len(masks)
    partial = np.empty((len(y), nstates), dtype=np.float32)
    bank = np.empty(len(y), dtype=np.float32)
    rich = np.empty(len(y), dtype=np.float32)
    cnn = np.empty(len(y), dtype=np.float32)
    fold_ids = np.full(len(y), -1, dtype=int)
    folds = []
    split = GroupKFold(n_splits=min(settings['inner_folds'], len(np.unique(groups))))
    for fold, (train, valid) in enumerate(split.split(xbank, y, groups)):
        fold_started = time.perf_counter()
        train_groups, valid_groups = set(groups[train]), set(groups[valid])
        if train_groups & valid_groups:
            raise AssertionError('A group leaked across a controller-label cross-fit')
        fold_bundle = _fit_predictors(xbank[train], xfull[train], y[train], groups[train],
                                      seed + fold * 101, settings)
        partial[valid] = _all_mask_predictions(fold_bundle, xbank[valid])
        bank[valid] = predict_bank(fold_bundle, xbank[valid])
        rich[valid] = predict_rich(fold_bundle, xfull[valid])
        if settings['include_cnn']:
            cnn[valid] = predict_rich(fold_bundle, xfull[valid], 'cnn')
        else:
            cnn[valid] = rich[valid]
        fold_ids[valid] = fold
        folds.append({'fold': fold, 'fit_groups': sorted(train_groups), 'target_groups': sorted(valid_groups),
                      'n_fit': len(train), 'n_target': len(valid),
                      'seconds': time.perf_counter() - fold_started,
                      'phase_timings': fold_bundle['phase_timings']})
    bundle = _fit_predictors(xbank, xfull, y, groups, seed + 1009, settings)
    errors = np.abs(y[:, None] - partial)
    e_bank, e_rich, e_cnn = np.abs(y - bank), np.abs(y - rich), np.abs(y - cnn)
    gain = np.zeros((len(y), nstates - 1, width), dtype=np.float32)
    mapping = {tuple(mask): i for i, mask in enumerate(masks)}
    for m, mask in enumerate(masks[:-1]):
        for j in np.flatnonzero(~mask):
            continuation = mask.copy()
            continuation[j] = True
            gain[:, m, j] = errors[:, m] - errors[:, mapping[tuple(continuation)]]
    gain_stop = errors[:, :-1] - e_bank[:, None]
    labels = {'two_reference': gain_stop > settings['delta'],
              'single_reference': errors[:, :-1] - e_rich[:, None] > settings['delta']}
    if settings['include_cnn']:
        labels['single_cnn_reference'] = errors[:, :-1] - e_cnn[:, None] > settings['delta']
    repeated_values = np.repeat(xbank, nstates - 1, axis=0)
    repeated_masks = np.tile(masks[:-1], (len(y), 1))
    features = observed_input(bundle['scaler'], repeated_values, repeated_masks)
    available = ~repeated_masks
    flattened_gain = gain.reshape(-1, width)
    gain_scale = float(max(np.std(flattened_gain[available]), 0.1))
    error_scale = float(max(np.std(errors[:, :-1]), 0.1))
    weights = np.repeat(_weights(groups, settings['group_equal_weight']), nstates - 1)
    device = _device(settings)
    xt = torch.as_tensor(features, device=device)
    at = torch.as_tensor(available, dtype=torch.float32, device=device)
    gt = torch.as_tensor(flattened_gain / gain_scale, device=device)
    et = torch.as_tensor(errors[:, :-1].ravel() / error_scale, device=device)
    wt = torch.as_tensor(weights, device=device)
    controllers = {}
    training_log = {}
    for name, label in labels.items():
        controller_started = time.perf_counter()
        torch.manual_seed(seed + 701)
        rng = np.random.RandomState(seed + 701)
        model = GainController(width).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=settings['learning_rate'], weight_decay=1e-4)
        lt = torch.as_tensor(label.ravel(), dtype=torch.float32, device=device)
        final_loss = 0.0
        for epoch in range(settings['controller_epochs']):
            order = rng.permutation(len(features))
            for start in range(0, len(features), settings['batch_size']):
                ids = torch.as_tensor(order[start:start + settings['batch_size']], device=device)
                stop, actions, error = model(xt[ids])
                bce = nn.functional.binary_cross_entropy_with_logits(stop, lt[ids], reduction='none')
                action_loss = (((actions - gt[ids]) ** 2) * at[ids]).sum(1) / at[ids].sum(1).clamp_min(1)
                residual_loss = (error - et[ids]) ** 2
                loss = ((bce + action_loss + 0.25 * residual_loss) * wt[ids]).mean()
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                final_loss = float(loss.detach().cpu())
        controllers[name] = model.cpu().eval()
        training_log[name] = {'last_batch_loss': final_loss, 'epochs': settings['controller_epochs'],
                              'positive_fraction': float(label.mean()), 'target_states': int(label.size),
                              'seconds': time.perf_counter() - controller_started}
    scaled = bundle['scaler'].transform(xbank)
    bank_error_model = Ridge(alpha=10.0).fit(scaled, e_bank,
                                           sample_weight=_weights(groups, settings['group_equal_weight']))
    covariance = np.cov(scaled, rowvar=False)
    covariance += np.eye(width) * 1e-5
    initial_mask = masks[0]
    fixed_scores = np.mean(gain[:, 0, :], axis=0)
    fixed_order = list(settings['initial_indices']) + sorted(np.flatnonzero(~initial_mask).tolist(),
                                                            key=lambda j: (-fixed_scores[j], j))
    bundle.update({'controllers': controllers, 'gain_scale': gain_scale, 'error_scale': error_scale,
                   'bank_indices': list(map(int, bank_indices)), 'config': settings, 'seed': int(seed),
                   'fixed_order': fixed_order, 'conditional_mean': scaled.mean(0),
                   'bank_error_model': bank_error_model,
                   'conditional_cov': covariance,
                   'training_seconds': time.perf_counter() - started,
                   'training_log': training_log,
                   'oof': {'partial_predictions': partial, 'bank_predictions': bank,
                           'rich_predictions': rich, 'cnn_predictions': cnn, 'fold_ids': fold_ids,
                           'folds': folds, 'masks': masks, 'g_stop': gain_stop,
                           'g_bank': e_bank - e_rich, 'g_bank_cnn': e_bank - e_cnn,
                           'g_actions': gain, 'groups': groups, 'y': y,
                           'target_positive_fractions': {k: float(v.mean()) for k, v in labels.items()}}})
    return bundle


def _conditional_values(bundle, values, mask, draw_seed):
    return _conditional_batch(bundle, np.asarray(values)[None, :], mask, draw_seed)[0]


def _conditional_batch(bundle, values, mask, draw_seed):
    observed, missing = np.flatnonzero(mask), np.flatnonzero(~mask)
    standardized = bundle['scaler'].transform(np.where(mask, values, bundle['scaler'].mean_))
    mean, cov = bundle['conditional_mean'], bundle['conditional_cov']
    c_oo = cov[np.ix_(observed, observed)]
    c_mo = cov[np.ix_(missing, observed)]
    correction = np.linalg.solve(c_oo, (standardized[:, observed] - mean[observed]).T).T
    conditional_mean = mean[missing] + correction @ c_mo.T
    conditional_cov = cov[np.ix_(missing, missing)] - c_mo @ np.linalg.solve(c_oo, c_mo.T)
    eigval, eigvec = np.linalg.eigh((conditional_cov + conditional_cov.T) / 2)
    root = eigvec @ np.diag(np.sqrt(np.maximum(eigval, 1e-8)))
    draws = bundle['config']['lookahead_draws']
    rng = np.random.RandomState(draw_seed)
    z = np.repeat(standardized[:, None, :], draws, axis=1)
    z[:, :, missing] = conditional_mean[:, None, :] + rng.normal(size=(draws, len(missing))) @ root.T
    return bundle['scaler'].inverse_transform(z.reshape(-1, len(mask))).reshape(z.shape).astype(np.float32)


def lookahead_action(bundle, values, mask):
    """Two-step conditional-Gaussian residual-risk approximation.

    Every synthetic future value is drawn from a covariance fitted on training
    groups. The second action may depend on the first simulated observation.
    Assays and the replay example's hidden channels never enter this routine.
    """
    return int(lookahead_actions(bundle, np.asarray(values)[None, :], np.asarray(mask)[None, :])[0])


def lookahead_actions(bundle, values, masks):
    """Batch identical observation masks without exposing hidden readings."""
    values, masks = np.asarray(values), np.asarray(masks, dtype=bool)
    result = np.empty(len(values), dtype=int)
    unique_masks, membership = np.unique(masks, axis=0, return_inverse=True)
    for number, mask in enumerate(unique_masks):
        all_ids = np.flatnonzero(membership == number)
        missing = np.flatnonzero(~mask)
        if len(missing) == 0:
            raise ValueError('No unobserved channel is available')
        if len(missing) == 1:
            result[all_ids] = missing[0]
            continue
        for start in range(0, len(all_ids), 256):
            ids = all_ids[start:start + 256]
            current = values[ids]
            first_draws = _conditional_batch(bundle, current, mask,
                                             bundle['seed'] + 771 + int(mask.sum()))
            action_risks = []
            for j in missing:
                draw_risks = []
                for draw in range(first_draws.shape[1]):
                    after_first = current.copy()
                    after_first[:, j] = first_draws[:, draw, j]
                    first_mask = mask.copy()
                    first_mask[j] = True
                    second_draws = _conditional_batch(bundle, after_first, first_mask,
                                                       bundle['seed'] + 991 + 31 * int(j) + draw)
                    candidate_risks = []
                    for k in np.flatnonzero(~first_mask):
                        second_mask = first_mask.copy()
                        second_mask[k] = True
                        after_second = np.repeat(after_first[:, None, :], second_draws.shape[1], axis=1)
                        after_second[:, :, k] = second_draws[:, :, k]
                        flattened = after_second.reshape(-1, len(mask))
                        errors = predicted_error(bundle, flattened,
                                                 np.broadcast_to(second_mask, flattened.shape))
                        candidate_risks.append(errors.reshape(len(ids), -1).mean(1))
                    draw_risks.append(np.min(np.stack(candidate_risks), axis=0))
                action_risks.append(np.mean(np.stack(draw_risks), axis=0))
            result[ids] = missing[np.argmin(np.stack(action_risks), axis=0)]
    return result


def simulate(bundle, readings, method='proposed', threshold=0.5, max_pulses=None, return_states=True):
    """Replay a vector or batch; all decisions see only accumulated readings."""
    readings = np.asarray(readings, dtype=np.float32)
    if readings.ndim == 1:
        readings = readings[None, :]
    n, width = readings.shape
    if width != len(bundle['bank_indices']):
        raise ValueError('Replay readings must use installed-bank order')
    allowed = {'proposed', 'two_reference', 'single', 'single_reference', 'single_cnn_reference',
               'uncertainty', 'fixed_order', 'random_order', 'fixed_length', 'lookahead', 'full_bank'}
    if method not in allowed:
        raise ValueError('Unknown acquisition method: ' + method)
    objective = {'single': 'single_reference'}.get(method, method)
    if objective not in bundle['controllers']:
        objective = 'two_reference'
    values = np.zeros_like(readings)
    mask = np.zeros((n, width), dtype=bool)
    initial = bundle['initial_indices']
    values[:, initial] = readings[:, initial]
    mask[:, initial] = True
    maximum = width if max_pulses is None else int(max_pulses)
    if maximum < len(initial) or maximum > width:
        raise ValueError('Pulse cap must include the initial readings and not exceed bank width')
    if method == 'full_bank':
        maximum = width
    alive = np.ones(n, dtype=bool)
    traces = [[] for _ in range(n)]
    predictions = np.empty(n)
    final_prob = np.full(n, np.nan)
    rng = np.random.RandomState(bundle['seed'] + 401)
    random_orders = [list(initial) + rng.permutation([j for j in range(width) if j not in initial]).tolist()
                     for _ in range(n)]
    while alive.any():
        ids = np.flatnonzero(alive)
        preds = partial_predict(bundle, values[ids], mask[ids])
        prob, gains = controller_outputs(bundle, values[ids], mask[ids], objective)
        risk = predicted_error(bundle, values[ids], mask[ids]) if method == 'uncertainty' else None
        lookahead_next = {}
        if method == 'lookahead':
            continuing = (mask[ids].sum(1) < maximum) & (prob > threshold)
            continued_ids = ids[continuing]
            if len(continued_ids):
                selected = lookahead_actions(bundle, values[continued_ids], mask[continued_ids])
                lookahead_next = dict(zip(continued_ids.tolist(), selected.tolist()))
        for t, i in enumerate(ids):
            pulses = int(mask[i].sum())
            stop = pulses >= maximum
            if method not in {'fixed_length', 'full_bank'}:
                stop = stop or (float(risk[t]) <= threshold if method == 'uncertainty' else float(prob[t]) <= threshold)
            next_channel = None
            if not stop:
                if method in {'fixed_order', 'fixed_length'}:
                    next_channel = next(j for j in bundle['fixed_order'] if not mask[i, j])
                elif method == 'random_order':
                    next_channel = next(j for j in random_orders[i] if not mask[i, j])
                elif method == 'lookahead':
                    next_channel = lookahead_next[int(i)]
                else:
                    next_channel = int(np.argmax(gains[t]))
                if mask[i, next_channel]:
                    raise AssertionError('A channel was requested twice')
            if return_states:
                traces[i].append({'pulses': pulses, 'mask': mask[i].astype(int).tolist(),
                                  'readings': [float(values[i, j]) if mask[i, j] else None for j in range(width)],
                                  'prediction': float(preds[t]), 'p_stopgain': float(prob[t]),
                                  'predicted_error': float(risk[t]) if risk is not None else None,
                                  'next_channel': next_channel, 'stop': bool(stop)})
            if stop:
                alive[i] = False
                predictions[i] = preds[t]
                final_prob[i] = prob[t]
            else:
                values[i, next_channel] = readings[i, next_channel]
                mask[i, next_channel] = True
    return {'predictions': predictions, 'pulses': mask.sum(1), 'masks': mask,
            'stop_probabilities': final_prob, 'traces': traces}
