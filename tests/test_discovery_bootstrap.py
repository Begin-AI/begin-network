import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from begin_network.envelope import VERSION, Rejected, generate_key, decode, sign
from begin_network.discovery_index import verify_index, load_mirrors, ATTESTATION_PROFILE

ROOT=Path(__file__).resolve().parents[1]

def stamp(seconds):return datetime.fromtimestamp(seconds,timezone.utc).isoformat().replace('+00:00','Z')

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.key=generate_key();self.keys={self.key['kid']:decode(self.key['public'])}
        self.index=json.loads((ROOT/'discovery/index.json').read_text())
        self.index['generated_at']=stamp(100)
        self.index['nodes']=[{'id':'synthetic-independent','endpoint':'https://node.example.org','capabilities':['mailbox','discovery'],'expires_at':stamp(200),'trust':'unverified-advertisement'}]
        method=self.index['methods'][0]
        self.contract={k:method[k] for k in ('id','method_version','model','dimensions','normalization')}

    def raw(self,index=None):return json.dumps(index or self.index).encode()

    def token(self,raw=None,key=None,**changes):
        raw=self.raw() if raw is None else raw;key=key or self.key
        value=json.loads(raw)
        envelope={'version':VERSION,'type':'response','sender':key['kid'],'id':'synthetic-attestation',
                  'audience':'local-bootstrap','issued_at':100,'expires_at':200,'proofs':[],
                  'body':{'profile':ATTESTATION_PROFILE,'index_sha256':hashlib.sha256(raw).hexdigest(),'protocol_version':VERSION,'generated_at':value['generated_at']}}
        envelope.update(changes)
        return sign(envelope,decode(key['private']))

    def check(self,raw=None,token=None,**policy):
        raw=self.raw() if raw is None else raw
        return verify_index(raw,token or self.token(raw),self.keys,'local-bootstrap',now=policy.pop('now',150),**policy)

    def test_pinned_attestation_returns_exact_contract_and_ads_without_authority(self):
        result=self.check(requested_contracts=[self.contract],capabilities=['mailbox'])
        self.assertEqual(result['methods'][0]['id'],self.contract['id'])
        self.assertEqual(result['nodes'][0]['id'],'synthetic-independent')
        self.assertFalse(result['authority_granted'])

    def test_raw_byte_tampering_even_whitespace_rejected(self):
        raw=self.raw()
        with self.assertRaises(Rejected):self.check(raw+b' ',self.token(raw))

    def test_unsigned_forged_expired_and_wrong_audience_rejected(self):
        foreign=generate_key()
        for token in ('unsigned',self.token(key=foreign),self.token(expires_at=150),self.token(audience='other')):
            with self.subTest(token=token[:15]),self.assertRaises(Rejected):self.check(token=token)

    def test_stale_generated_index_and_host_rollback_floor(self):
        old=copy.deepcopy(self.index);old['generated_at']=stamp(0)
        with self.assertRaises(Rejected):self.check(self.raw(old),max_age=100)
        with self.assertRaises(Rejected):self.check(minimum_generated_at=101)
        self.assertEqual(self.check(minimum_generated_at=100)['generated_at'],stamp(100))

    def test_expired_node_is_rejected(self):
        index=copy.deepcopy(self.index);index['nodes'][0]['expires_at']=stamp(150)
        with self.assertRaises(Rejected):self.check(self.raw(index))

    def test_unsupported_contract_model_revision_dimension_or_method(self):
        for field,value in [('id','unknown'),('method_version','2'),('model','other'),('dimensions',384),('normalization','l2')]:
            contract=dict(self.contract,**{field:value})
            with self.subTest(field=field),self.assertRaises(Rejected):self.check(requested_contracts=[contract])
        with self.assertRaises(Rejected):self.check(capabilities=['coordination'])

    def test_experiment_method_requires_explicit_local_opt_in(self):
        method=next(m for m in self.index['methods'] if m['availability']=='experiment')
        contract={k:method[k] for k in self.contract}
        with self.assertRaises(Rejected):self.check(requested_contracts=[contract])
        self.assertEqual(self.check(requested_contracts=[contract],require_runtime=False)['methods'][0]['id'],method['id'])

    def test_schema_private_fields_and_duplicate_records_rejected(self):
        for index in (dict(self.index,vectors=[]),dict(self.index,methods=self.index['methods']+[self.index['methods'][0]])):
            with self.assertRaises(Rejected):self.check(self.raw(index))

    def test_mirror_failover_and_independent_replacement_signer(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'index.json').write_bytes(self.raw());(p/'token').write_text(self.token())
            result=load_mirrors([(p/'missing',p/'missing-token'),(p/'index.json',p/'token')],self.keys,'local-bootstrap',now=150)
            self.assertEqual(result['rejected_mirrors'],1)
            independent=generate_key();(p/'token').write_text(self.token(key=independent))
            result=load_mirrors([(p/'index.json',p/'token')],{independent['kid']:decode(independent['public'])},'local-bootstrap',now=150)
            self.assertEqual(result['attested_by'],independent['kid'])

    def test_no_url_fetch_or_signer_discovery(self):
        with self.assertRaises(Rejected):load_mirrors([('https://node.example.org/index.json','https://node.example.org/token')],self.keys,'local-bootstrap',now=150)
        with self.assertRaises(Rejected):verify_index(self.raw(),self.token(),{},'local-bootstrap',now=150)
        with self.assertRaises(Rejected):self.check(revoked_signers=[self.key['kid']])

    def test_attestation_metadata_and_profile_exact(self):
        for changes in ({'type':'request'},{'proofs':['implied-authority']},{'body':{'profile':'unknown'}}):
            with self.assertRaises(Rejected):self.check(token=self.token(**changes))
        index=copy.deepcopy(self.index);index['protocol_version']='future'
        with self.assertRaises(Rejected):self.check(self.raw(index))

if __name__=='__main__':unittest.main()
