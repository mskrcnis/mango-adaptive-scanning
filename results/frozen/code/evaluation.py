"""Observed-information trajectories and threshold-independent policy evaluation."""
import numpy as np
from sklearn.isotonic import IsotonicRegression

from .models import predict_bank, predict_rich
from .training import simulate


METHODS = ['proposed', 'single', 'uncertainty', 'fixed_order', 'random_order', 'lookahead', 'single_cnn_reference']


def trajectory(bundle, readings, method):
    raw = simulate(bundle, readings, method=method, threshold=-1e30)
    states = raw['traces']
    return {key: np.asarray([[s[field] for s in row] for row in states], dtype=dtype)
            for key, field, dtype in [('prediction','prediction',float), ('probability','p_stopgain',float),
                                     ('risk','predicted_error',float), ('mask','mask',bool)]}


def choose_on_path(path, threshold, method='proposed', max_pulses=None):
    n, depth = path['prediction'].shape
    scores = path['risk'] if method == 'uncertainty' else path['probability']
    stop = scores <= threshold
    stop[:, -1] = True
    if method == 'fixed_length':
        index = np.full(n, int(max_pulses) - int(path['mask'][0, 0].sum()), dtype=int)
    else:
        index = stop.argmax(1)
    rows = np.arange(n)
    return {'predictions': path['prediction'][rows,index], 'pulses': path['mask'][rows,index].sum(1),
            'probabilities':path['probability'][rows,index], 'masks':path['mask'][rows,index],
            'index':index}


def calibrate(bundle, readings, xfull, y):
    bundle['calibrators'] = {}
    bank = predict_bank(bundle, readings)
    references = {'two_reference':bank, 'single_reference':predict_rich(bundle,xfull)}
    if 'single_cnn_reference' in bundle['controllers']:
        references['single_cnn_reference'] = predict_rich(bundle,xfull,'cnn')
    records = {}
    for objective, reference in references.items():
        method = {'two_reference':'proposed', 'single_reference':'single'}.get(objective,objective)
        path = trajectory(bundle, readings, method)
        p = path['probability'][:,:-1].ravel()
        label = ((np.abs(y[:,None]-path['prediction'][:,:-1]) - np.abs(y-reference)[:,None]) > .5).ravel().astype(int)
        mapping = IsotonicRegression(y_min=0,y_max=1,out_of_bounds='clip').fit(p,label)
        bundle['calibrators'][objective] = mapping
        records[objective] = {'n_scans':len(y), 'n_states':len(label), 'positive_fraction':float(label.mean()),
                              'raw_brier':float(np.mean((p-label)**2)),
                              'fitted_brier':float(np.mean((mapping.predict(p)-label)**2)),
                              'mapping_x':mapping.X_thresholds_.tolist(), 'mapping_y':mapping.y_thresholds_.tolist(),
                              'interpretation':'training-calibration fit diagnostics, not held-out calibration evidence'}
    risk_path = trajectory(bundle, readings, 'uncertainty')
    bundle['uncertainty_thresholds'] = np.quantile(risk_path['risk'][:,:-1],np.linspace(0,1,21)).tolist()
    bundle['calibration_records'] = records
    return bundle


def visited_calibration(y, reference, path, selection, delta=.5):
    rows, depths = [], []
    for i, end in enumerate(selection['index']):
        for d in range(min(int(end)+1, path['prediction'].shape[1]-1)):
            rows.append(i)
            depths.append(d)
    rows, depths = np.asarray(rows,dtype=int), np.asarray(depths,dtype=int)
    p = path['probability'][rows,depths]
    label = (np.abs(y[rows]-path['prediction'][rows,depths])-np.abs(y[rows]-reference[rows])) > delta
    bins=[]
    edges=np.linspace(0.,1.,11)
    for index,(low,high) in enumerate(zip(edges[:-1],edges[1:])):
        take = (p>=low)&((p<=high) if index==len(edges)-2 else (p<high))
        bins.append({'low':float(low),'n':int(take.sum()),'predicted':float(p[take].mean()) if take.any() else None,
                     'observed':float(label[take].mean()) if take.any() else None})
    return {'n_states':len(p), 'brier':float(np.mean((p-label)**2)) if len(p) else None, 'bins':bins,
            'scope':'visited non-terminal states, repeated scan states; descriptive calibration only'}
