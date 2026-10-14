"""Expose outcome leakage rather than equating ciphertext with private discovery."""
import importlib.util
from pathlib import Path
import unittest

class ProbingEvidenceTests(unittest.TestCase):
    def test_signed_encrypted_distinct_queries_recover_synthetic_direction(self):
        source = Path(__file__).parents[1] / 'experiments/probing/run.py'
        spec = importlib.util.spec_from_file_location('begin_probing_experiment', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run(12)
        self.assertEqual(result['accepted_queries'], 12)
        self.assertFalse(result['grant_is_cumulative'])
        low, high = result['recovered_interval']
        self.assertLessEqual(low, result['synthetic_truth_angle'])
        self.assertGreaterEqual(high, result['synthetic_truth_angle'])
        self.assertLess(result['interval_width'], 0.0004)
        self.assertLess(result['absolute_angle_error'], 0.0002)
        self.assertTrue(any(row['matched'] for row in result['transcript']))
        self.assertTrue(any(not row['matched'] for row in result['transcript']))
