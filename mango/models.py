"""Small prediction models for channel-restricted, offline scanner replay."""
from dataclasses import dataclass
import warnings

import numpy as np
import torch
from sklearn.cross_decomposition import PLSRegression
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from scipy.signal import savgol_filter
from torch import nn


class MaskedMLP(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2 * width, 64), nn.ReLU(),
                                 nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


class GainController(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(2 * width, 64), nn.ReLU(),
                                     nn.Linear(64, 32), nn.ReLU())
        self.stop = nn.Linear(32, 1)
        self.action = nn.Linear(32, width)
        self.error = nn.Linear(32, 1)

    def forward(self, x):
        hidden = self.encoder(x)
        return self.stop(hidden).squeeze(-1), self.action(hidden), self.error(hidden).squeeze(-1)


class SpectralCNN(nn.Module):
    """Compact Walsh-inspired convolutional reference; not the authors' code."""
    def __init__(self, width):
        super().__init__()
        self.net = nn.Sequential(nn.Conv1d(1, 8, 7, padding=3), nn.ReLU(),
                                 nn.Conv1d(8, 16, 5, padding=2), nn.ReLU(),
                                 nn.AvgPool1d(2), nn.Flatten(),
                                 nn.Linear(16 * (width // 2), 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):
        return self.net(x[:, None, :]).squeeze(-1)


def snv(x):
    x = np.asarray(x, dtype=np.float64)
    return (x - x.mean(1, keepdims=True)) / np.maximum(x.std(1, keepdims=True), 1e-8)


class PLSReference:
    def __init__(self, n_components=10, use_snv=False, derivative=False):
        self.n_components = int(n_components)
        self.use_snv = bool(use_snv)
        self.derivative = bool(derivative)

    def transform(self, x):
        z = snv(x) if self.use_snv else np.asarray(x, dtype=np.float64)
        if self.derivative:
            z = savgol_filter(z, window_length=11, polyorder=2, deriv=2, delta=3.0, axis=1)
        return z

    def fit(self, x, y):
        z = self.transform(x)
        count = max(1, min(self.n_components, z.shape[1], z.shape[0] - 1))
        self.model = PLSRegression(n_components=count, scale=True, max_iter=500)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.model.fit(z, np.asarray(y))
        return self

    def predict(self, x):
        z = self.transform(x)
        return self.model.predict(z).ravel()


class FixedSVR:
    def fit(self, x, y):
        self.scaler = StandardScaler().fit(x)
        self.model = SVR(C=10.0, epsilon=0.1, gamma='scale').fit(self.scaler.transform(x), y)
        return self

    def predict(self, x):
        return self.model.predict(self.scaler.transform(x))


def observed_input(scaler, values, mask):
    values = np.asarray(values, dtype=np.float32)
    mask = np.asarray(mask, dtype=bool)
    if values.ndim == 1:
        values, mask = values[None, :], mask[None, :]
    if values.shape != mask.shape or values.shape[1] != len(scaler.mean_):
        raise ValueError('Readings and mask must have matching N by installed-channel shape')
    if not np.isfinite(values[mask]).all():
        raise ValueError('Acquired readings must be finite')
    safe = np.where(mask, values, scaler.mean_[None, :])
    scaled = scaler.transform(safe).astype(np.float32)
    return np.concatenate([np.where(mask, scaled, 0.0), mask.astype(np.float32)], axis=1)


def torch_predict(model, inputs, batch_size=16384):
    model.eval()
    outputs = []
    with torch.no_grad():
        for start in range(0, len(inputs), batch_size):
            t = torch.as_tensor(inputs[start:start + batch_size], dtype=torch.float32)
            out = model(t)
            if isinstance(out, tuple):
                outputs.append(tuple(item.cpu().numpy() for item in out))
            else:
                outputs.append(out.cpu().numpy())
    if not outputs:
        return np.empty(0)
    if isinstance(outputs[0], tuple):
        return tuple(np.concatenate([out[j] for out in outputs]) for j in range(len(outputs[0])))
    return np.concatenate(outputs)


def partial_predict(bundle, acquired_values, mask):
    mask = np.asarray(mask, dtype=bool)
    values = np.asarray(acquired_values, dtype=np.float32)
    if mask.ndim == 1:
        mask, values = mask[None, :], values[None, :]
    inputs = observed_input(bundle['scaler'], values, mask)
    pred = np.asarray(torch_predict(bundle['masked_predictor'], inputs), dtype=np.float64) * bundle['y_scale'] + bundle['y_mean']
    complete = mask.all(1)
    if np.any(complete):
        pred[complete] = predict_bank(bundle, values[complete])
    return np.asarray(pred, dtype=float)


def predict_bank(bundle, xbank):
    return bundle['bank_predictor'].predict(np.atleast_2d(np.asarray(xbank, dtype=np.float32)))


def predict_rich(bundle, xfull, reference='pls'):
    if reference == 'pls':
        return bundle['rich_predictor'].predict(np.atleast_2d(xfull))
    if reference != 'cnn':
        raise ValueError(reference)
    inputs = bundle['rich_scaler'].transform(np.atleast_2d(xfull)).astype(np.float32)
    return torch_predict(bundle['rich_cnn'], inputs) * bundle['y_scale'] + bundle['y_mean']


def controller_outputs(bundle, acquired_values, mask, objective='two_reference', raw=False):
    inputs = observed_input(bundle['scaler'], acquired_values, mask)
    logits, actions, error = torch_predict(bundle['controllers'][objective], inputs)
    probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -50, 50)))
    calibrator = bundle.get('calibrators', {}).get(objective)
    if calibrator is not None and not raw:
        probabilities = np.asarray(calibrator.predict(probabilities), dtype=float)
    actions = actions * bundle['gain_scale']
    actions[np.asarray(mask, dtype=bool).reshape(actions.shape)] = -np.inf
    return probabilities, actions


def predicted_error(bundle, acquired_values, mask):
    inputs = observed_input(bundle['scaler'], acquired_values, mask)
    _, _, error = torch_predict(bundle['controllers']['two_reference'], inputs)
    result = np.maximum(error * bundle['error_scale'], 0.0)
    complete = np.asarray(mask, dtype=bool).reshape((-1, len(bundle['bank_indices']))).all(1)
    if complete.any() and 'bank_error_model' in bundle:
        values = np.asarray(acquired_values, dtype=float).reshape((-1, len(bundle['bank_indices'])))
        result[complete] = np.maximum(bundle['bank_error_model'].predict(bundle['scaler'].transform(values[complete])), 0.0)
    return result


def gain_labels(y, partial, bank, rich, continued, delta=0.50):
    y = np.asarray(y)
    error = np.abs(y - partial)
    stop = error - np.abs(y - bank)
    bank_gain = np.abs(y - bank) - np.abs(y - rich)
    actions = error[..., None] - np.abs(y[..., None] - continued)
    return {'g_stop': stop, 'g_bank': bank_gain, 'g_actions': actions,
            'stop_label': stop > delta,
            'single_label': error - np.abs(y - rich) > delta}
