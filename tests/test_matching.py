import json
from dataclasses import replace
from pathlib import Path
import unittest

from begin_network.matching import Intention, represent, compare, evaluate


class MatchingTests(unittest.TestCase):
    def pair(self, purpose='window', **candidate):
        role = 'offer' if purpose == 'window' else 'peer'
        q = represent(Intention('q', purpose, 'python', role='seek' if purpose == 'window' else 'peer'))
        c = represent(Intention('c', purpose, candidate.pop('text', 'python'), role=role, **candidate))
        return q, c

    def test_three_purposes(self):
        for purpose in ('window', 'mirror', 'social'):
            self.assertEqual(compare(*self.pair(purpose)).status, 'match')

    def test_task_roles_are_independent_of_representation_purpose(self):
        for purpose in ('mirror', 'window', 'social'):
            for left, right in (('seek', 'offer'), ('offer', 'seek'), ('peer', 'peer')):
                q = represent(Intention('q', purpose, 'python', role=left))
                c = represent(Intention('c', purpose, 'python', role=right))
                self.assertEqual(compare(q, c).status, 'match')
            q = represent(Intention('q', purpose, 'python', role='seek'))
            c = represent(Intention('c', purpose, 'python', role='seek'))
            self.assertEqual(compare(q, c).reason, 'role mismatch')

    def test_provenance_and_determinism(self):
        q, _ = self.pair()
        self.assertEqual(q, represent(q.intention))
        self.assertEqual(len(q.source_sha256), 64)
        self.assertNotEqual(q.source_sha256, represent(replace(q.intention, text='code')).source_sha256)

    def test_incompatible_model_and_method(self):
        q, c = self.pair()
        for changed in (replace(c, model='future'), replace(c, method='lexical-v1')):
            self.assertEqual(compare(q, changed).status, 'incompatible')

    def test_constraints_survive_exploration(self):
        for args in ({'consent': False}, {'language': 'fr'}, {'location': 'moon'},
                     {'required_tags': ('verified',)}):
            q, c = self.pair(**args)
            self.assertIn(compare(q, c, explore=True).status, ('declined', 'ineligible'))

    def test_explicit_exploration(self):
        q, c = self.pair(text='python astronomy ocean birds')
        self.assertEqual(compare(q, c, threshold=.8).status, 'no-match')
        self.assertEqual(compare(q, c, threshold=.8, explore=True).status, 'exploration')
        q, c = self.pair(text='gardening')
        self.assertEqual(compare(q, c, explore=True).status, 'no-match')

    def test_fixed_corpus_exposes_failures(self):
        cases = json.loads((Path(__file__).parents[1] / 'examples/matching_cases.json').read_text())
        lexical = evaluate(cases, 'lexical-v1')
        concept = evaluate(cases, 'concept-v1')
        self.assertEqual(lexical['counts'], dict(tp=1, fp=2, tn=7, fn=3))
        self.assertEqual(concept['counts'], dict(tp=4, fp=2, tn=7, fn=0))
        self.assertEqual([d['case'] for d in concept['decisions']
                          if d['status'] == 'match' and not d['expected_match']],
                         ['negation adversary', 'topic stuffing adversary'])

    def test_unsupported_inputs(self):
        for intention in (Intention('q', 'unknown', 'a'), Intention('q', 'mirror', 'a', role='admin')):
            with self.assertRaises(ValueError):
                represent(intention)
        with self.assertRaises(ValueError):
            represent(Intention('q', 'mirror', 'a'), model='downloaded')


if __name__ == '__main__':
    unittest.main()
