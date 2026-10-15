"""Published experimental evidence must identify the source it actually ran."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SharedIndexEvidenceTests(unittest.TestCase):
    def test_reports_are_bound_to_current_sources_and_separate_nodes(self):
        for name in ('results.json', 'model-results.json'):
            report = json.loads((ROOT / 'experiments/shared_index' / name).read_text())
            self.assertTrue(report['synthetic_only'])
            for filename, expected in report['source_hashes'].items():
                directory = 'experiments/shared_index' if filename in ('party.py', 'support.py') else 'src/begin_network'
                self.assertEqual(hashlib.sha256((ROOT / directory / filename).read_bytes()).hexdigest(), expected, filename)
            groups = [report['parties']] if 'parties' in report else [m['parties'] for m in report['measurements']]
            for parties in groups:
                self.assertEqual(len({p['pid'] for p in parties}), 3)
                self.assertEqual({p['party'] for p in parties}, {0, 1, 2})
                self.assertTrue(all(p['tls'] and p['bytes_sent'] > 0 for p in parties))

    def test_model_predicate_evidence_does_not_claim_semantic_quality(self):
        report = json.loads((ROOT / 'experiments/shared_index/model-results.json').read_text())
        self.assertEqual(report['dimensions'], 384)
        self.assertEqual(report['actual_predicates'], report['expected_predicates'])
        self.assertEqual(report['actual_predicates'], [True, False])
        self.assertFalse(report['semantic_quality_evaluated'])
        suite = json.loads((ROOT / 'experiments/shared_index/results.json').read_text())
        self.assertTrue(suite['successful'])
        self.assertEqual(suite['tests_run'], len(suite['tests']))
        self.assertIn('not malicious security', suite['trust'])


if __name__ == '__main__':
    unittest.main()
