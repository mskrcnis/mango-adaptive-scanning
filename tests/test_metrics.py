import numpy as np
from mango.metrics import safe_rate
from mango.evaluation import visited_calibration


def test_zero_denominator_is_undefined():
    assert safe_rate(0,0) is None


def test_reliability_bins_include_all_exact_boundaries():
    probabilities=np.array([0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.])
    path={'prediction':np.zeros((11,2)), 'probability':np.column_stack([probabilities,np.zeros(11)])}
    result=visited_calibration(np.zeros(11),np.zeros(11),path,{'index':np.zeros(11,dtype=int)})
    assert result['n_states']==11
    assert sum(b['n'] for b in result['bins'])==11
    assert result['bins'][-1]['n']==2
