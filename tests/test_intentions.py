from dataclasses import replace
import unittest
from begin_network.intentions import Store as BaseStore, InvalidIntention

class Store(BaseStore):
    def create(self, *args, **kwargs):
        kwargs.setdefault('perspectives', {k: ['explicit synthetic test view'] for k in ('mirror','window','social')})
        return super().create(*args, **kwargs)


class IntentionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.store.create('rima-window', 'integrated', facts=['I run a company'], aspirations=['Learn guitar'],
                          inferences=['Possibly interested in folk music'], consent=True,
                          disclosure=['aspirations'], role='seek', available_from=10,
                          available_until=100, expires_at=120)
        self.store.create('teacher-window', 'integrated', facts=['I teach guitar'], consent=True,
                          disclosure=['facts'], role='offer', available_from=20,
                          available_until=90, expires_at=120)

    def vectors(self):
        return [self.store.vector(id, [3,4], 'manual-fixture-v1', 'synthetic-v1')
                for id in ('rima-window', 'teacher-window')]

    def test_nan_time_and_boolean_vector_contracts_rejected(self):
        vectors=self.vectors()
        with self.assertRaises(InvalidIntention):self.store.compare(*vectors,now=float('nan'))
        with self.assertRaises(InvalidIntention):self.store.compare(replace(vectors[0],dimension=True,values=(True,)),vectors[1],now=30)
        with self.assertRaises(InvalidIntention):self.store.compare(replace(vectors[0],values=(True,False)),vectors[1],now=30)
        with self.assertRaises(InvalidIntention):self.store.create('invalid',[],available_from=0,available_until=1,expires_at=1)

    def test_synthetic_goal_relevance_and_disclosure(self):
        self.assertAlmostEqual(self.store.compare(*self.vectors(), now=30), 1)
        self.assertEqual(self.store.disclose('rima-window',30), {'aspirations': ('Learn guitar',)})
        v=self.vectors()[0]
        self.assertEqual((v.dimension,v.normalization,v.language),(2,'l2','en'))

    def test_edit_invalidates_old_vector_and_keeps_categories(self):
        old=self.vectors()
        updated=self.store.edit('rima-window',1,inferences=[],aspirations=['Learn piano'])
        self.assertEqual(updated.facts,('I run a company',))
        self.assertEqual(updated.inferences,())
        with self.assertRaisesRegex(InvalidIntention,'stale representation'):
            self.store.compare(*old,now=30)
        with self.assertRaisesRegex(InvalidIntention,'stale revision'):
            self.store.edit('rima-window',1,consent=False)

    def test_consent_withdrawal_retirement_expiry(self):
        vectors=self.vectors()
        self.store.edit('rima-window',1,consent=False)
        with self.assertRaises(InvalidIntention): self.store.disclose('rima-window',30)
        with self.assertRaises(InvalidIntention): self.store.compare(*vectors,now=30)
        self.store.retire('teacher-window',1)
        with self.assertRaises(InvalidIntention): self.store.edit('teacher-window',2,consent=True)
        with self.assertRaises(InvalidIntention): self.store.disclose('teacher-window',30)
        fresh=Store();fresh.create('a','integrated',consent=True,available_until=10,expires_at=10)
        with self.assertRaises(InvalidIntention): fresh.disclose('a',10)

    def test_multiple_integrated_intentions_are_independent(self):
        self.store.create('rima-mirror','integrated',facts=['Learning music'],consent=True,
                          available_until=100,expires_at=120)
        self.store.create('rima-social','integrated',aspirations=['Meet local musicians'],consent=True,
                          available_until=100,expires_at=120)
        self.store.edit('rima-window',1,aspirations=['Learn piano'])
        self.assertEqual(self.store.get('rima-social').revision,1)
        self.assertEqual(self.store.get('rima-mirror').facts,('Learning music',))

    def test_incompatible_metadata_and_tampered_vectors(self):
        a,b=self.vectors()
        for bad in (replace(b,model='other'),replace(b,language='fr'),replace(b,method='other'),
                    replace(b,dimension=3),replace(b,values=(2.,2.))):
            with self.assertRaises(InvalidIntention):self.store.compare(a,bad,now=30)
        for values in ([],[0,0],[float('nan')],[True]):
            with self.assertRaises(InvalidIntention):self.store.vector('rima-window',values,'m','v')

    def test_timing_and_task_roles(self):
        a,b=self.vectors()
        with self.assertRaises(InvalidIntention):self.store.compare(a,b,now=90)
        with self.assertRaises(InvalidIntention):self.store.compare(a,b,now=30,roles=('peer','peer'))
        self.store.edit('teacher-window',1,available_from=100,available_until=110)
        with self.assertRaises(InvalidIntention):self.store.compare(*self.vectors(),now=30)

    def test_lifecycle_validation(self):
        with self.assertRaises(InvalidIntention):self.store.create('bad','integrated',available_until=0)
        with self.assertRaises(InvalidIntention):self.store.edit('rima-window',1,purpose='integrated')
        with self.assertRaises(InvalidIntention):self.store.edit('rima-window',1,disclosure=['private-key'])
        with self.assertRaises(InvalidIntention):self.store.create('rima-window','integrated')
        with self.assertRaises(InvalidIntention):self.store.edit('rima-window',1,facts='accidental string')


if __name__=='__main__':unittest.main()
