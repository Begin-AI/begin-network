"""Audit frozen benchmark artifacts without downloading model weights in core CI."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/'experiments'/'embeddings'

class EvidenceTests(unittest.TestCase):
    def test_report_binds_corpus_and_pinned_model(self):
        report=json.loads((ROOT/'results.json').read_text())
        self.assertEqual(report['corpus_sha256'],hashlib.sha256((ROOT/'corpus.json').read_bytes()).hexdigest())
        self.assertEqual(report['revision'],(ROOT/'model-revision.txt').read_text().strip())
        self.assertEqual(report['dimension'],384)
        self.assertEqual(len(report['model_files_sha256']['model.safetensors']),64)

    def test_report_counts_and_known_semantic_failures_are_visible(self):
        report=json.loads((ROOT/'results.json').read_text())
        corpus=json.loads((ROOT/'corpus.json').read_text())
        gold={case['id']:case['expected_match'] for case in corpus['cases']}
        for method,data in report['results'].items():
            counts=dict(tp=0,fp=0,tn=0,fn=0)
            self.assertEqual({case['id'] for case in data['cases']},set(gold))
            for case in data['cases']:
                expected=gold[case['id']]
                self.assertEqual(case['expected_match'],expected)
                prediction=case['predicted_match']
                counts[('t' if prediction==expected else 'f')+('p' if prediction else 'n')]+=1
            self.assertEqual(counts,data['counts'])
        learned={case['id']:case for case in report['results']['all-MiniLM-L6-v2']['cases']}
        for id in ('negated-skill','negated-willingness','past-vs-future','aspiration-not-capability'):
            self.assertTrue(learned[id]['predicted_match'])
            self.assertFalse(learned[id]['expected_match'])

if __name__=='__main__':unittest.main()
