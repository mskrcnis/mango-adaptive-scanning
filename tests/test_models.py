"""Contract tests for the observation boundary and OOF target construction."""
import unittest

import numpy as np

from mango.models import observed_input, partial_predict, predict_bank, gain_labels, controller_outputs
from mango.training import fit_bundle, simulate, lookahead_action


class ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.RandomState(4)
        cls.x = rng.normal(size=(48, 5))
        full = rng.normal(size=(48, 103))
        y = 16 + cls.x[:, 0] + .7 * cls.x[:, 4]
        groups = np.repeat(np.arange(12), 4)
        cls.bundle = fit_bundle(cls.x, full, y, groups, list(range(5)), config={
            'predictor_epochs': 2, 'controller_epochs': 2, 'cnn_epochs': 2,
            'inner_folds': 2, 'device': 'cpu', 'batch_size': 64,
            'bank_components': 3, 'rich_components': 3})

    def test_gain_signs(self):
        result = gain_labels(np.array([10.]), np.array([13.]), np.array([11.]),
                             np.array([10.5]), np.array([[12., 14.]]))
        np.testing.assert_array_equal(result['g_stop'], [2.])
        np.testing.assert_array_equal(result['g_bank'], [.5])
        np.testing.assert_array_equal(result['g_actions'], [[1., -1.]])
        self.assertTrue(result['stop_label'][0])

    def test_hidden_values_do_not_change_decision(self):
        a = self.x[:3].copy()
        mask = np.zeros_like(a, dtype=bool)
        mask[:, [0, 4]] = True
        b = a.copy()
        b[~mask] = 1e20
        np.testing.assert_array_equal(partial_predict(self.bundle, a, mask), partial_predict(self.bundle, b, mask))
        p1, g1 = controller_outputs(self.bundle, a, mask)
        p2, g2 = controller_outputs(self.bundle, b, mask)
        np.testing.assert_array_equal(p1, p2)
        np.testing.assert_array_equal(g1, g2)
        self.assertEqual(lookahead_action(self.bundle, a[0], mask[0]), lookahead_action(self.bundle, b[0], mask[0]))

    def test_zero_and_unread_differ(self):
        values = np.zeros((1, 5))
        observed = np.zeros((1, 5), dtype=bool)
        missing = observed.copy()
        observed[0, 2] = True
        a = observed_input(self.bundle['scaler'], values, observed)
        b = observed_input(self.bundle['scaler'], values, missing)
        self.assertEqual(a[0, 7], 1)
        self.assertEqual(b[0, 7], 0)
        self.assertFalse(np.array_equal(a, b))

    def test_frozen_bank_endpoint(self):
        x = self.x[:5]
        np.testing.assert_array_equal(partial_predict(self.bundle, x, np.ones_like(x, dtype=bool)),
                                      predict_bank(self.bundle, x))
        oof = self.bundle['oof']
        np.testing.assert_array_equal(oof['partial_predictions'][:, -1], oof['bank_predictions'])

    def test_target_group_separation(self):
        oof = self.bundle['oof']
        for fold in oof['folds']:
            self.assertFalse(set(fold['fit_groups']) & set(fold['target_groups']))
        for group in np.unique(oof['groups']):
            self.assertEqual(len(np.unique(oof['fold_ids'][oof['groups'] == group])), 1)

    def test_termination_without_repeated_pulse(self):
        for method in ['proposed', 'single', 'single_cnn_reference', 'uncertainty', 'fixed_order',
                       'random_order', 'fixed_length', 'lookahead', 'full_bank']:
            result = simulate(self.bundle, self.x[:2], method, threshold=-1.)
            self.assertTrue(np.all(result['pulses'] <= 5))
            for trace in result['traces']:
                requests = [state['next_channel'] for state in trace if state['next_channel'] is not None]
                self.assertEqual(len(requests), len(set(requests)))
                self.assertTrue(trace[-1]['stop'])

    def test_runtime_has_no_assay_or_metadata_argument(self):
        import inspect
        for function in [partial_predict, controller_outputs, simulate, lookahead_action]:
            parameters = inspect.signature(function).parameters
            self.assertFalse(set(parameters) & {'y', 'assay', 'season', 'metadata', 'reference_predictions'})


if __name__ == '__main__':
    unittest.main()
