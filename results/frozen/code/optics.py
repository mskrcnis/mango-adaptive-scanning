"""Reference-normalized finite-band apparent-absorbance emulator."""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = (684.0, 990.0)
COVERAGE_CUTOFF = 0.95


def get_catalog(eligible_only=True, profile_type=None):
    """Return verified part records, defaulting to eligible digitized curves.

    ``profile_type='gaussian_approximation'`` retains the same physical parts but
    replaces plotted shapes with Gaussians from documented nominal center/FWHM.
    It is a separately labeled sensitivity, not a measured emission profile.
    """
    rows = json.loads((ROOT / 'data/catalog/catalog.json').read_text())
    rows = deepcopy(rows)
    if profile_type == 'gaussian_approximation':
        for row in rows:
            row['profile_type'] = profile_type
            row['support_fraction'] = support_fraction(row, *SUPPORT)
            row['eligible'] = row['support_fraction'] >= COVERAGE_CUTOFF
    elif profile_type not in (None, 'digitized_datasheet_curve'):
        raise ValueError('Unknown profile type')
    return [r for r in rows if r['eligible'] or not eligible_only]


def _profile_values(wavelengths, channel, center_shift_nm=0.0, width_scale=1.0):
    wave = np.asarray(wavelengths, dtype=np.float64)
    if width_scale <= 0:
        raise ValueError('width_scale must be positive')
    center = float(channel.get('center_nm', channel.get('center')))
    kind = channel.get('profile_type', 'gaussian_approximation')
    adjusted = center + (wave - center - center_shift_nm) / width_scale
    if kind == 'digitized_datasheet_curve':
        curve = np.loadtxt(ROOT / channel['profile_path'], delimiter=',', skiprows=1)
        return np.interp(adjusted, curve[:, 0], curve[:, 1], left=0., right=0.)
    if kind == 'gaussian_approximation':
        width = float(channel.get('fwhm_nm', channel.get('fwhm')))
        if width <= 0:
            raise ValueError('Gaussian FWHM must be positive')
        return np.exp(-4 * np.log(2) * ((adjusted-center) / width)**2)
    raise ValueError(f'Unsupported profile type: {kind}')


def support_fraction(channel, lower=684., upper=990., center_shift_nm=0., width_scale=1.):
    if lower >= upper or width_scale <= 0:
        raise ValueError('Invalid support or bandwidth scale')
    center = float(channel.get('center_nm', channel.get('center')))
    if channel.get('profile_type') == 'digitized_datasheet_curve':
        curve = np.loadtxt(ROOT / channel['profile_path'], delimiter=',', skiprows=1)
        x = center + (curve[:, 0] - center) * width_scale + center_shift_nm
        v = curve[:, 1]
        inside = np.unique(np.r_[lower, x[(x > lower) & (x < upper)], upper])
        mass = np.trapezoid(v, x) if hasattr(np, 'trapezoid') else np.trapz(v, x)
        yin = np.interp(inside, x, v, left=0., right=0.)
        partial = np.trapezoid(yin, inside) if hasattr(np, 'trapezoid') else np.trapz(yin, inside)
        return float(np.clip(partial / mass, 0., 1.))
    sigma = float(channel.get('fwhm_nm', channel.get('fwhm'))) * width_scale / (2 * math.sqrt(2*math.log(2)))
    center += center_shift_nm
    return .5 * (math.erf((upper-center)/(math.sqrt(2)*sigma)) - math.erf((lower-center)/(math.sqrt(2)*sigma)))


def response_weights(wavelengths, catalog=None, *, detector=None, reference=None,
                     center_shift_nm=0.0, width_scale=1.0, coverage_cutoff=COVERAGE_CUTOFF):
    """Return normalized weights with shape (wavelengths, channels).

    Trapezoidal bin widths integrate only measured support. Flat detector and
    reference responses are an explicit simulation assumption. Supplied response
    arrays must have one nonnegative entry per wavelength. Coverage screening is
    based on the emitter model, before an optional in-window detector multiplier.
    """
    wave = np.asarray(wavelengths, dtype=np.float64)
    if wave.ndim != 1 or len(wave) < 2 or not np.isfinite(wave).all() or np.any(np.diff(wave) <= 0):
        raise ValueError('Wavelengths must be a finite strictly increasing vector')
    catalog = get_catalog() if catalog is None else catalog
    if not catalog:
        raise ValueError('An empty catalog has no measurable channels')
    delta = np.diff(wave)
    bins = np.r_[delta[0]/2, (delta[:-1]+delta[1:])/2, delta[-1]/2]
    total = bins.copy()
    for label, arr in [('detector', detector), ('reference', reference)]:
        if arr is not None:
            arr = np.asarray(arr, dtype=np.float64)
            if arr.shape != wave.shape or np.any(arr < 0) or not np.isfinite(arr).all():
                raise ValueError(f'{label} response is invalid')
            total *= arr
    cols = []
    for channel in catalog:
        fraction = support_fraction(channel, float(wave[0]), float(wave[-1]), center_shift_nm, width_scale)
        if fraction + 1e-12 < coverage_cutoff:
            raise ValueError(f"Unsupported emitter {channel['id']}: response mass {fraction:.6f} < {coverage_cutoff}")
        weight = _profile_values(wave, channel, center_shift_nm, width_scale) * total
        if not np.isfinite(weight).all() or weight.sum() <= 0:
            raise ValueError(f"Emitter {channel['id']} has no usable response")
        cols.append(weight / weight.sum())
    return np.column_stack(cols)


def channel_matrix(X, wavelengths, catalog=None, **kwargs):
    """Compute z=-log10(sum(w*10**(-A))) from base-10 apparent absorbance.

    Offline only: full spectral rows are used to construct individual channel
    readings. Runtime acquisition receives only requested scalar readings.
    """
    absorbance = np.asarray(X, dtype=np.float64)
    was_1d = absorbance.ndim == 1
    if was_1d:
        absorbance = absorbance[None, :]
    if absorbance.ndim != 2 or absorbance.shape[1] != len(wavelengths) or not np.isfinite(absorbance).all():
        raise ValueError('Absorbance shape or values are invalid')
    weights = response_weights(wavelengths, catalog, **kwargs)
    # Row shifting keeps exponentials finite without changing weighted ratios.
    shift = absorbance.min(axis=1, keepdims=True)
    ratio = np.power(10., -(absorbance-shift)) @ weights
    if np.any(ratio <= 0):
        raise ValueError('Channel intensity underflow; inspect absorbance units')
    result = -np.log10(ratio) + shift
    return result[0] if was_1d else result
