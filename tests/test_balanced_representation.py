"""The three perspectives form one editable representation, never disjoint types."""
import math
import tempfile
import unittest
from begin_network.encoders import SyntheticEncoder
from begin_network.intentions import Store, InvalidIntention
from begin_network.local_discovery import evaluate, validate_query
from begin_network.envelope import Rejected
from begin_network.runtime_bridge import Participant


class BalancedRepresentationTests(unittest.TestCase):
    def item(self, **changes):
        options = dict(perspectives={'mirror': ['synthetic guitar'], 'window': ['synthetic piano'],
                                    'social': ['synthetic guitar']},
                       balance={'mirror': .2, 'window': .5, 'social': .3}, consent=True,
                       available_until=100, expires_at=100)
        options.update(changes)
        return Store().create('one', 'integrated', **options)

    def test_one_vector_contains_all_three_weighted_views(self):
        vector = SyntheticEncoder().encode(self.item())
        self.assertAlmostEqual(vector[0], math.sqrt(.5))
        self.assertAlmostEqual(vector[1], math.sqrt(.5))
        for name in ('mirror', 'window', 'social'):
            item = self.item()
            item.perspectives[name] = ['synthetic piano' if name != 'window' else 'synthetic guitar']
            self.assertNotEqual(SyntheticEncoder().encode(item), vector)

    def test_balance_changes_relevance_without_changing_type(self):
        a = SyntheticEncoder().encode(self.item())
        b = SyntheticEncoder().encode(self.item(balance={'mirror': .1, 'window': .8, 'social': .1}))
        self.assertGreater(b[1], a[1])
        self.assertLess(b[0], a[0])

    def test_missing_views_zero_nonfinite_and_invalid_balances_rejected(self):
        for perspectives in (None, {}, {'mirror': ['only']}, {'mirror': ['x'], 'window': [], 'social': ['y']}):
            with self.assertRaises(InvalidIntention): self.item(perspectives=perspectives)
        for balance in ({}, {'mirror': 0, 'window': .5, 'social': .5},
                        {'mirror': True, 'window': .5, 'social': .5},
                        {'mirror': float('nan'), 'window': .5, 'social': .5},
                        {'mirror': .5, 'window': .5, 'social': .5}):
            with self.assertRaises(InvalidIntention): self.item(balance=balance)

    def test_legacy_records_require_explicit_recreation(self):
        for name in ('mirror','window','social'):
            with self.assertRaises(InvalidIntention): Store().create('old', name)
            with self.assertRaises(Rejected): validate_query({'method':'old', 'model':'old', 'purpose':name,
                'role':'peer','available_from':0,'available_until':100,'values':[1.,0.]})

    def test_edits_invalidate_vectors_and_input_mutation_cannot_change_store(self):
        store = Store()
        item = self.item()
        created = store.create('one','integrated',perspectives=item.perspectives,balance=item.balance,
                               consent=True,available_until=100,expires_at=100)
        created.perspectives['social'] = ['mutated externally']
        self.assertEqual(store.get('one').perspectives['social'], ['synthetic guitar'])
        previous = store.vector('one', SyntheticEncoder().encode(store.get('one')), 'balanced-v2', 'fixture')
        updated = store.edit('one',1,balance={'mirror':.1,'window':.8,'social':.1})
        self.assertEqual(updated.revision,2)
        other = store.create('other','integrated',perspectives=item.perspectives,consent=True,available_until=100,expires_at=100)
        right = store.vector('other',SyntheticEncoder().encode(other),'balanced-v2','fixture')
        with self.assertRaisesRegex(InvalidIntention,'stale'): store.compare(previous,right,now=1,roles=('peer','peer'))

    def test_runner_balance_edit_revokes_old_introduction(self):
        with tempfile.TemporaryDirectory() as root:
            p = Participant(root, encoder=SyntheticEncoder(), clock=lambda: 10)
            try:
                item = self.item()
                options = dict(purpose='integrated',facts=[],aspirations=[],inferences=[],role='peer',
                               available_from=0,available_until=100,expires_at=100,consent=True,disclosure=[],
                               perspectives=item.perspectives,balance=item.balance)
                p.set_intention('one',**options)
                pool = 'a'*64
                p.configure_discovery_pools([pool])
                invitation = p.offer_discovery('one',pool)
                p.set_intention('one',**dict(options,balance={'mirror':.1,'window':.8,'social':.1}),expected_revision=1)
                with self.assertRaises(Rejected): p._live_invitation(invitation['invitation_id'])
            finally:
                p.close()
