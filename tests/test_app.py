import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from mango.app import ScannerSession, ReplaySource, _http_test, replay
from mango.training import fit_bundle, simulate


class AppContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.RandomState(18)
        x = rng.normal(size=(36, 4))
        y = 17 + x[:, 0] + x[:, 3]
        model = fit_bundle(x, rng.normal(size=(36, 103)), y, np.repeat(np.arange(12), 3), list(range(4)),
                           config={'predictor_epochs': 2, 'controller_epochs': 2, 'cnn_epochs': 2,
                                   'inner_folds': 2, 'device': 'cpu', 'batch_size': 64,
                                   'bank_components': 2, 'rich_components': 2})
        cls.runtime = {'bundle': model, 'parts': [{'id': 'LED%d' % j, 'center_nm': 720 + j * 40} for j in range(4)],
                       'threshold': -1., 'example': {'row_id': 'software-fixture', 'readings': x[0].tolist()},
                       'rule': 'software_test', 'operating_point': 'software test only', 'manifest_sha256': 'fixture'}

    def test_http_interaction(self):
        result = _http_test(self.runtime)
        self.assertEqual(result['status'], 'passed')
        self.assertTrue(all(result['checks'].values()))

    def test_reject_wrong_led_and_duplicate(self):
        session = ScannerSession(self.runtime)
        with self.assertRaises(ValueError):
            session.add_reading('LED1', 0.)
        session.add_reading('LED0', 0.)
        with self.assertRaises(ValueError):
            session.add_reading('LED0', 0.)
        self.assertEqual(int(session.mask.sum()), 1)

    def test_manual_cli_exports_same_trace(self):
        def answer(prompt):
            for j in range(4):
                if 'LED%d:' % j in prompt:
                    return str(self.runtime['example']['readings'][j])
            raise AssertionError(prompt)
        with tempfile.TemporaryDirectory() as temp:
            destination = str(Path(temp) / 'trace.json')
            with patch('mango.app.load_runtime', return_value=self.runtime), patch('builtins.input', side_effect=answer), patch('builtins.print'):
                result = replay(manual=True, trace_output=destination)
            expected = simulate(self.runtime['bundle'], self.runtime['example']['readings'], threshold=-1.)['traces'][0]
            self.assertEqual(result['trace'], expected)
            self.assertEqual(json.loads(Path(destination).read_text())['trace'], expected)


if __name__ == '__main__':
    unittest.main()
