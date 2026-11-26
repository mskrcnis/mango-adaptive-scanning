"""Group-separated adaptation of Walsh et al.'s published CNN architecture.

This uses raw 103-channel inputs and local seasonal partitions, not the authors'
preprocessing combinations or data split. See docs/walsh_reference.md.
"""
from __future__ import annotations

import time

import numpy as np
import torch
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from torch import nn


class WalshArchitecture(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(1, 1, 21, padding=10), nn.ELU(), nn.Flatten(),
            nn.Linear(width, 36), nn.ELU(), nn.Linear(36, 18), nn.ELU(),
            nn.Linear(18, 12), nn.ELU(), nn.Linear(12, 1))
        for layer in self.layers:
            if isinstance(layer, (nn.Linear, nn.Conv1d)):
                nn.init.kaiming_normal_(layer.weight, mode='fan_in', nonlinearity='relu')
                nn.init.zeros_(layer.bias)

    def forward(self, x):
        return self.layers(x[:, None, :]).squeeze(-1)

    def regularization(self):
        return 0.0055 * sum(layer.weight.square().sum() for layer in self.layers
                            if isinstance(layer, (nn.Linear, nn.Conv1d)))


class WalshReference:
    def __init__(self, scaler, network, fit_info):
        self.scaler = scaler
        self.network = network.cpu().eval()
        self.fit_info = fit_info

    def predict(self, X):
        X = np.atleast_2d(np.asarray(X, dtype=np.float64))
        if not np.isfinite(X).all():
            raise ValueError('Walsh input must contain finite spectra.')
        transformed = self.scaler.transform(X).astype(np.float32)
        result = []
        with torch.no_grad():
            for start in range(0, len(X), 4096):
                result.append(self.network(torch.from_numpy(transformed[start:start + 4096])).numpy())
        return np.concatenate(result) if result else np.empty(0, dtype=float)


def fit_walsh(X, y, groups, seed=42, max_epochs=750):
    """Return a serializable fitted model with ``predict`` and ``fit_info``.

    The supplied arrays must contain only outer fitting groups. A separate 20%
    group subset controls scheduling/early stopping; no controller calibration
    or held-out season is accepted by this function. ``max_epochs`` is exposed
    for smoke verification; the registered baseline uses the default 750.
    """
    started = time.monotonic()
    X, y, groups = np.asarray(X, dtype=np.float64), np.asarray(y, dtype=np.float32), np.asarray(groups)
    if X.ndim != 2 or y.shape != (len(X),) or groups.shape != (len(X),):
        raise ValueError('Expected aligned spectra, scalar targets and group labels.')
    if not np.isfinite(X).all() or not np.isfinite(y).all() or len(np.unique(groups)) < 2:
        raise ValueError('Finite observations and at least two fitting groups are required.')
    if not 1 <= max_epochs <= 750:
        raise ValueError('max_epochs must be between 1 and 750.')
    fit, validation = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(X, y, groups))
    assert not set(groups[fit]).intersection(groups[validation])
    scaler = StandardScaler().fit(X[fit])
    xfit = scaler.transform(X[fit]).astype(np.float32)
    xval = scaler.transform(X[validation]).astype(np.float32)
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    network = WalshArchitecture(X.shape[1]).to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=0.005, eps=1e-7)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=25, threshold=1e-4,
        threshold_mode='abs', min_lr=1e-6)
    tx = torch.as_tensor(xfit, device=device)
    ty = torch.as_tensor(y[fit], device=device)
    vx = torch.as_tensor(xval, device=device)
    vy = torch.as_tensor(y[validation], device=device)
    best, best_epoch, waiting = float('inf'), 0, 0
    history, best_state = [], None
    for epoch in range(1, max_epochs + 1):
        network.train()
        order = torch.randperm(len(fit), device=device)
        training_total = 0.0
        for start in range(0, len(fit), 128):
            index = order[start:start + 128]
            optimizer.zero_grad()
            loss = (network(tx[index]) - ty[index]).square().mean() + network.regularization()
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite Walsh training loss at epoch %d.' % epoch)
            loss.backward()
            optimizer.step()
            training_total += float(loss.detach().cpu()) * len(index)
        network.eval()
        with torch.no_grad():
            validation_mse = float((network(vx) - vy).square().mean().cpu())
            validation_loss = validation_mse + float(network.regularization().cpu())
        if not np.isfinite(validation_loss):
            raise FloatingPointError('Nonfinite Walsh validation loss at epoch %d.' % epoch)
        history.append({'epoch': epoch, 'train_loss': training_total / len(fit),
                        'validation_loss': validation_loss, 'validation_mse': validation_mse,
                        'learning_rate': optimizer.param_groups[0]['lr']})
        if validation_loss < best - 1e-5:
            best, best_epoch, waiting = validation_loss, epoch, 0
            best_state = {key: value.detach().cpu().clone() for key, value in network.state_dict().items()}
        else:
            waiting += 1
        scheduler.step(validation_loss)
        if waiting >= 50:
            break
    network.load_state_dict(best_state)
    information = {
        'method': 'walsh_adapted', 'seed': int(seed), 'epochs': epoch, 'max_epochs': int(max_epochs),
        'best_epoch': best_epoch, 'best_validation_loss': best, 'history': history,
        'fit_indices': fit.tolist(), 'early_stop_indices': validation.tolist(),
        'fit_groups': sorted(map(str, np.unique(groups[fit]))),
        'early_stop_groups': sorted(map(str, np.unique(groups[validation]))),
        'n_features': int(X.shape[1]), 'n_fit': len(fit), 'n_early_stop': len(validation),
        'device': str(device), 'elapsed_seconds': time.monotonic() - started,
        'preprocessing': 'raw absorbance; training-subset column standardization; unscaled y',
        'architecture': 'Conv1D(1,21,same)-ELU-Flatten-Dense(36)-ELU-Dense(18)-ELU-Dense(12)-ELU-Dense(1)',
        'adaptation': 'PyTorch He normal instead of Keras truncated He normal; local raw-103 inputs and group split',
        'kernel_l2_coefficient': 0.0055, 'batch_size': 128, 'initial_learning_rate': 0.005,
        'source_commit': '0d939025cf30df1cfaf6afdc35c7de34de0b03b1',
        'source_code_sha256': 'f1ae16dcd04440f22e74f293f8af7a3d592c7672e5b1ae37194beb2fad3f753c'}
    return WalshReference(scaler, network, information)
