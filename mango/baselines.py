"""Training-only fixed-budget physical and ideal-grid baseline models."""
import warnings
import numpy as np
from sklearn.linear_model import LassoLars
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .models import PLSReference, FixedSVR


LASSO_SOLVER = {'max_iter':2000,'precompute':True,'fit_intercept':True,
                'eps':float(np.finfo(float).eps)}


def _lasso_optimality(model,x,y,alpha):
    residual=y-model.predict(x)
    gradient=x.T@residual/len(y)
    active=np.abs(model.coef_)>1e-8
    active_gap=np.max(np.abs(gradient[active]-alpha*np.sign(model.coef_[active]))) if active.any() else 0.
    inactive_gap=np.max(np.maximum(np.abs(gradient[~active])-alpha,0.)) if (~active).any() else 0.
    primal=.5*np.mean(residual**2)+alpha*np.abs(model.coef_).sum()
    dual_variable=residual/max(1.,np.max(np.abs(gradient))/alpha)
    dual=np.mean((y-y.mean())*dual_variable-.5*dual_variable**2)
    return float(max(active_gap,inactive_gap)),float(max(primal-dual,0.))


def sparse_order(x,y,groups,return_diagnostics=False,solver_options=None):
    x,y,groups=np.asarray(x),np.asarray(y),np.asarray(groups)
    cv=list(GroupKFold(n_splits=3).split(x,y,groups))
    alphas=np.logspace(-4,-.3,14)[::-1]
    losses=np.empty((len(alphas),len(cv)),dtype=float)
    warning_counts=np.zeros((len(alphas),len(cv)),dtype=int)
    iterations=np.zeros((len(alphas),len(cv)),dtype=int)
    dual_gaps=np.zeros((len(alphas),len(cv)),dtype=float)
    kkt=np.zeros((len(alphas),len(cv)),dtype=float)
    fold_records=[]
    solver=dict(LASSO_SOLVER)
    if solver_options:
        solver.update(solver_options)
    for fold,(fit,valid) in enumerate(cv):
        scaler=StandardScaler().fit(x[fit])
        train=scaler.transform(x[fit])
        held=scaler.transform(x[valid])
        fold_records.append({'fold':fold,'fit_groups':np.unique(groups[fit]).astype(str).tolist(),
                             'validation_groups':np.unique(groups[valid]).astype(str).tolist(),
                             'fit_rows':int(len(fit)),'validation_rows':int(len(valid))})
        candidate=LassoLars(**solver)
        for i,alpha in enumerate(alphas):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                candidate.set_params(alpha=float(alpha)).fit(train,y[fit])
            losses[i,fold]=np.mean((candidate.predict(held)-y[valid])**2)
            warning_counts[i,fold]=len(caught)
            iterations[i,fold]=candidate.n_iter_
            kkt[i,fold],dual_gaps[i,fold]=_lasso_optimality(candidate,train,y[fit],float(alpha))
    chosen=int(np.argmin(losses.mean(axis=1)))
    scaled=StandardScaler().fit_transform(x)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model=LassoLars(alpha=float(alphas[chosen]),**solver).fit(scaled,y)
    refit_kkt,refit_dual_gap=_lasso_optimality(model,scaled,y,float(alphas[chosen]))
    corr=np.abs(np.nan_to_num(np.corrcoef(scaled.T,y)[-1,:-1]))
    order=sorted(range(x.shape[1]),key=lambda j:(-abs(model.coef_[j]),-corr[j],j))
    diagnostics={'chosen_alpha':float(alphas[chosen]),'alphas':alphas.tolist(),
                 'fold_mse':losses.tolist(),'mean_fold_mse':losses.mean(axis=1).tolist(),
                 'cv_warning_counts':warning_counts.tolist(),'refit_warning_count':len(caught),
                 'cv_iterations':iterations.tolist(),'refit_iterations':int(model.n_iter_),
                 'cv_dual_gaps':dual_gaps.tolist(),'refit_dual_gap':refit_dual_gap,
                 'cv_kkt_violation':kkt.tolist(),'refit_kkt_violation':refit_kkt,
                 'optimality_assessment_tolerance':1e-7,
                 'folds':fold_records,'scaling':'StandardScaler fitted separately inside each grouped inner fold; final scaler refitted on all fitting rows',
                 'selection':'minimum mean grouped-fold MSE; alpha grid descending resolves exact ties toward stronger regularization',
                 'max_iter':solver['max_iter'],'solver':solver,'solver_name':'LassoLars',
                 'normalization':'Locked sklearn1.3.2 default performs no LassoLars normalization; fold-local StandardScaler is explicit.'}
    return (order,diagnostics) if return_diagnostics else order


def fit_static(channels, full, y, groups, bank_indices, seed=42):
    out={}
    physical=channels[:,bank_indices]
    physical_order,physical_diagnostics=sparse_order(physical,y,groups,return_diagnostics=True)
    full_order,full_diagnostics=sparse_order(full,y,groups,return_diagnostics=True)
    for family,x,order,budgets in [('physical',physical,physical_order,[4,8]),('ideal',full,full_order,[4,8,16])]:
        for budget in budgets:
            indices=sorted(order[:min(budget,x.shape[1])])
            z=x[:,indices]
            models={'plsr':PLSReference(min(len(indices),6)).fit(z,y),
                    'sparse_svr':FixedSVR().fit(z,y)}
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                models['mlp']=make_pipeline(StandardScaler(),MLPRegressor(hidden_layer_sizes=(64,32),max_iter=160,
                                         random_state=seed,early_stopping=False,batch_size=256,alpha=.01)).fit(z,y)
            for name,model in models.items():
                out['%s_%s_%d'%(family,name,budget)]={'model':model,'indices':indices,'family':family,
                                                     'pulses':budget,'bank_indices':list(bank_indices),
                                                     'selection_diagnostics':physical_diagnostics if family=='physical' else full_diagnostics}
    return out


def predict_static(models,channels,full):
    out={}
    for name,obj in models.items():
        x=full if obj['family']=='ideal' else channels[:,obj['bank_indices']]
        out[name]=obj['model'].predict(x[:,obj['indices']]).ravel()
    return out
