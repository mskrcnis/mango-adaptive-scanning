"""Partition and supervised-selection boundaries, including repeated scans."""
import copy
from itertools import combinations
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from mango.baselines import sparse_order
from mango.workflow import split_indices, design_indices, get_bundle, bank_rules


class FixtureData(SimpleNamespace):
    def __len__(self):
        return len(self.y)


class PartitionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.RandomState(324)
        seasons=np.repeat([1,2,3],36)
        groups=np.repeat(['s%d_pop%d'%(s,g) for s in [1,2,3] for g in range(12)],3)
        cls.data=FixtureData(X=rng.normal(size=(108,103)),y=rng.normal(size=108),
                                 groups=groups,seasons=seasons,
                                 row_ids=np.asarray(['row_%03d'%j for j in range(108)]))
        cls.channels=rng.normal(size=(108,10))

    def test_design_fit_calibration_validation_isolation(self):
        data=self.data
        for season in [1,2,3,None]:
            fit,cal,valid=split_indices(data,season)
            design=design_indices(data,season)
            partitions=[fit,cal,valid,design]
            for left,right in combinations(partitions,2):
                self.assertFalse(set(left)&set(right))
                self.assertFalse(set(data.row_ids[left])&set(data.row_ids[right]))
                self.assertFalse(set(data.groups[left])&set(data.groups[right]))
            self.assertEqual(set(np.concatenate(partitions)),set(range(len(data.y))))
            self.assertTrue(len(design)>0)
            for group in np.unique(data.groups):
                locations=[number for number,indices in enumerate(partitions) if group in data.groups[indices]]
                self.assertEqual(len(locations),1)
            if season is not None:
                self.assertTrue(np.all(data.seasons[valid]==season))
                self.assertFalse(np.any(data.seasons[np.concatenate([fit,cal,design])]==season))

    def test_bank_candidates_ignore_core_outcomes_and_channels(self):
        for season in [1,2,3,None]:
            fit,cal,valid=split_indices(self.data,season)
            design=design_indices(self.data,season)
            changed=copy.deepcopy(self.data)
            changed.y[np.concatenate([fit,cal,valid])]=np.arange(len(fit)+len(cal)+len(valid))*1e6
            changed_channels=self.channels.copy()
            changed_channels[np.concatenate([fit,cal,valid])]=1e8
            expected=bank_rules(self.channels[design],self.data.y[design])
            def fake_fit(data,channels,actual_fit,actual_cal,indices,seed,settings):
                np.testing.assert_array_equal(actual_fit,fit)
                np.testing.assert_array_equal(actual_cal,cal)
                self.assertFalse(set(data.groups[actual_fit])&set(data.groups[design]))
                return {'bank_indices':indices}
            with patch('mango.workflow.checkpoint',side_effect=lambda key,fingerprint,action:action()), patch('mango.workflow.fit_calibrated',side_effect=fake_fit):
                for rule in expected:
                    original,fp,actual_valid=get_bundle(self.data,self.channels,season,rule,42,'fixture')
                    altered,fp_changed,_=get_bundle(changed,changed_channels,season,rule,42,'fixture')
                    self.assertEqual(original['bank_indices'],expected[rule])
                    self.assertEqual(altered['bank_indices'],expected[rule])
                    np.testing.assert_array_equal(actual_valid,valid)


class SparseSelectionContractTests(unittest.TestCase):
    def test_scaling_fits_only_inner_training_rows(self):
        rng=np.random.RandomState(12)
        x=rng.normal(size=(72,10))
        x[:,0]=np.arange(len(x))
        y=2*x[:,1]+rng.normal(scale=.1,size=len(x))
        groups=np.repeat(np.arange(12),6)
        fitted_rows=[]
        class TrackingScaler(StandardScaler):
            def fit(self,values,y=None,sample_weight=None):
                fitted_rows.append(np.asarray(values)[:,0].astype(int).tolist())
                return super().fit(values,y,sample_weight=sample_weight)
        with patch('mango.baselines.StandardScaler',TrackingScaler):
            order,diagnostics=sparse_order(x,y,groups,return_diagnostics=True)
        folds=list(GroupKFold(n_splits=3).split(x,y,groups))
        self.assertEqual(len(fitted_rows),4)
        for fitted,(train,valid) in zip(fitted_rows,folds):
            self.assertEqual(set(fitted),set(train))
            self.assertFalse(set(groups[fitted])&set(groups[valid]))
        self.assertEqual(set(fitted_rows[-1]),set(range(len(x))))
        self.assertEqual(sorted(order),list(range(x.shape[1])))
        self.assertEqual(len(diagnostics['alphas']),14)
        self.assertEqual(np.asarray(diagnostics['fold_mse']).shape,(14,3))
        self.assertEqual(diagnostics['max_iter'],2000)
        self.assertEqual(diagnostics['solver_name'],'LassoLars')
        self.assertLess(max(map(max,diagnostics['cv_kkt_violation'])),1e-7)
        self.assertLess(diagnostics['refit_kkt_violation'],1e-7)
        again=sparse_order(x,y,groups)
        self.assertEqual(order,again)


if __name__=='__main__':
    unittest.main()
