import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from begin_network.envelope import generate_key, decode, sign, Rejected, VERSION
from begin_network.permissions import PermissionLedger, GRANT_PROFILE

class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.manager, self.worker = [generate_key() for _ in range(3)]
        self.keys = {k['kid']:decode(k['public']) for k in (self.root,self.manager,self.worker)}
        self.path = self.tmp.name + '/owner.sqlite'
        self.ledger = self.open_ledger()
        self.root_grant = self.grant(self.root,self.manager,'root-grant',None,depth=1,budget=3)
        self.leaf = self.grant(self.manager,self.worker,'worker-grant','root-grant',depth=0,budget=3)
        self.refresh()

    def tearDown(self):
        self.ledger.close(); self.tmp.cleanup()

    def open_ledger(self):
        return PermissionLedger(self.path,audience='resource-owner',authority=self.root['kid'],trusted_keys=self.keys,freshness=30)

    def envelope(self,key,kind,id,body,proofs=None,issued=100,expires=200):
        return {'version':VERSION,'type':kind,'sender':key['kid'],'id':id,'audience':'resource-owner',
                'issued_at':issued,'expires_at':expires,'body':body,'proofs':proofs or []}

    def grant(self,issuer,subject,id,parent,depth,budget,**changes):
        body={'profile':GRANT_PROFILE,'subject':subject['kid'],'purpose':'synthetic-goal','actions':['answer'],
              'resource':'synthetic-fixture','max_units':budget,'depth':depth,'parent':parent}
        body.update(changes)
        return self.envelope(issuer,'grant',id,body,[parent] if parent else [])

    def token(self,key,payload): return sign(payload,decode(key['private']))

    def chain(self,leaf=None):
        return [self.token(self.root,self.root_grant),self.token(self.manager,leaf or self.leaf)]

    def request(self,id='task',units=1,**changes):
        body={'purpose':'synthetic-goal','action':'answer','resource':'synthetic-fixture','units':units}
        body.update(changes)
        return self.token(self.worker,self.envelope(self.worker,'request',id,body,['worker-grant']))

    def refresh(self,issued=100,revoked=None):
        token=self.token(self.root,self.envelope(self.root,'revocation','snapshot-'+str(issued),
                         {'profile':GRANT_PROFILE,'revoked':revoked or []},issued=issued))
        self.ledger.apply_revocations(token,issued)

    def test_delegated_request_and_idempotency(self):
        token=self.request()
        self.assertEqual(self.ledger.reserve(token,self.chain(),110),'accepted')
        self.assertEqual(self.ledger.reserve(token,self.chain(),110),'duplicate')
        self.ledger.close();self.ledger=self.open_ledger()
        self.assertEqual(self.ledger.reserve(token,self.chain(),110),'duplicate')
        self.assertEqual(self.ledger.db.execute('SELECT spent FROM grants ORDER BY id').fetchall(),[(1,),(1,)])

    def test_scope_expansion_fails(self):
        for changes in ({'purpose':'other'},{'actions':['answer','spend']},{'resource':'private'},
                        {'max_units':4},{'depth':1},{'depth':False},{'parent':'other'}):
            leaf=copy.deepcopy(self.leaf);leaf['body'].update(changes)
            with self.subTest(changes=changes),self.assertRaises(Rejected):self.ledger.reserve(self.request(),self.chain(leaf),110)
        for changes in ({'action':'spend'},{'purpose':'other'},{'resource':'private'},{'units':True},{'units':10**100}):
            with self.subTest(changes=changes),self.assertRaises(Rejected):self.ledger.reserve(self.request(**changes),self.chain(),110)

    def test_cumulative_budget_not_per_request(self):
        self.ledger.reserve(self.request('first',2),self.chain(),110)
        with self.assertRaises(Rejected):self.ledger.reserve(self.request('second',2),self.chain(),110)
        self.assertEqual(self.ledger.reserve(self.request('third',1),self.chain(),110),'accepted')

    def test_sibling_delegations_share_parent_budget(self):
        self.ledger.reserve(self.request('first',2),self.chain(),110)
        sibling=self.grant(self.manager,self.worker,'sibling','root-grant',depth=0,budget=3)
        payload=self.envelope(self.worker,'request','sibling-task',{'purpose':'synthetic-goal','action':'answer','resource':'synthetic-fixture','units':2},['sibling'])
        with self.assertRaises(Rejected):self.ledger.reserve(self.token(self.worker,payload),self.chain(sibling),110)
        self.assertIsNone(self.ledger.db.execute("SELECT id FROM grants WHERE id='sibling'").fetchone())

    def test_stale_revocation_and_ancestor_revoke(self):
        with self.assertRaises(Rejected):self.ledger.reserve(self.request(),self.chain(),130)
        self.refresh(120,['root-grant'])
        with self.assertRaises(Rejected):self.ledger.reserve(self.request(),self.chain(),125)

    def test_conflicting_ids_and_revocation_rollback(self):
        self.ledger.reserve(self.request(),self.chain(),110)
        with self.assertRaises(Rejected):self.ledger.reserve(self.request(units=2),self.chain(),110)
        self.refresh(120)
        with self.assertRaises(Rejected):self.refresh(100)

    def test_parallel_reservations_cannot_overspend(self):
        tokens=[self.request(str(i),2) for i in range(2)]
        chain=self.chain()
        def run(token):
            ledger=self.open_ledger()
            try:
                return ledger.reserve(token,chain,110)
            except Rejected:
                return 'rejected'
            finally:
                ledger.close()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,tokens))
        self.assertEqual(sorted(results),['accepted','rejected'])
        self.assertEqual(self.ledger.db.execute('SELECT spent FROM grants ORDER BY id').fetchall(),[(2,),(2,)])

    def test_persistent_ledger_cannot_change_authority_audience_or_freshness(self):
        for changes in ({'audience':'other-owner'}, {'authority':self.manager['kid']}, {'freshness':300}):
            options={'audience':'resource-owner','authority':self.root['kid'],'trusted_keys':self.keys,'freshness':30}
            options.update(changes)
            with self.subTest(changes=changes),self.assertRaises(Rejected): PermissionLedger(self.path,**options)

    def test_legacy_unbound_populated_ledger_requires_migration(self):
        self.ledger.db.execute('DELETE FROM policy')
        with self.assertRaises(Rejected): self.open_ledger()

    def test_untrusted_root_and_wrong_subject(self):
        grant=copy.deepcopy(self.root_grant);grant['sender']=self.manager['kid']
        with self.assertRaises(Rejected):self.ledger.reserve(self.request(),[self.token(self.manager,grant),self.chain()[1]],110)
        leaf=copy.deepcopy(self.leaf);leaf['body']['subject']=self.manager['kid']
        with self.assertRaises(Rejected):self.ledger.reserve(self.request(),self.chain(leaf),110)

if __name__=='__main__':unittest.main()
