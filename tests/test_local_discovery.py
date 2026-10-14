import copy
import json
import tempfile
import unittest
from begin_network.envelope import generate_key, decode, sign, Rejected, ReplayStore
from begin_network.sealed import encryption_key, seal, sealed_digest, open_match_query
from begin_network.local_discovery import receive_query, evaluate
from begin_network.coordination import Mailbox

class LocalDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.requester,self.owner=[generate_key() for _ in range(2)]
        self.encryption=encryption_key()
        self.keys={k['kid']:decode(k['public']) for k in (self.requester,self.owner)}
        self.query={'method':'synthetic-l2-v1','model':'manual-fixture','purpose':'window','role':'seek',
                    'available_from':100,'available_until':190,'values':[1.0,0.0]}
        self.candidate=dict(self.query,role='offer')
        self.box=seal(json.dumps(self.query).encode(),decode(self.encryption['public']),'query-1',self.owner['kid'])
        self.request=self.envelope(self.requester,'request','query-1',{'purpose':'begin-discovery','action':'match',
                   'resource':'synthetic-owner-intention','units':1,'sealed_digest':sealed_digest(self.box)},['match-grant'])
        self.grant=self.envelope(self.owner,'grant','match-grant',{'subject':self.requester['kid'],'purpose':'begin-discovery',
                   'actions':['match'],'resource':'synthetic-owner-intention','max_units':1,'delegation_depth':0})
        self.replay=ReplayStore(self.tmp.name+'/replay.sqlite')

    def tearDown(self):self.replay.close();self.tmp.cleanup()

    def envelope(self,key,type,id,body,proofs=None):
        return {'version':'0.1-draft','type':type,'sender':key['kid'],'id':id,'audience':self.owner['kid'],
                'issued_at':100,'expires_at':200,'body':body,'proofs':proofs or []}

    def tokens(self):return sign(self.request,decode(self.requester['private'])),sign(self.grant,decode(self.owner['private']))

    def receive(self,**changes):
        request,grant=self.tokens()
        options={'keys':self.keys,'audience':self.owner['kid'],'authority':self.owner['kid'],
                 'recipient_private':decode(self.encryption['private']),'owner':self.candidate,'replay':self.replay,'now':150}
        options.update(changes)
        return receive_query(request,grant,self.box,**options)

    def test_pre_match_only_query_disclosed_and_replay_rejected(self):
        result=self.receive()
        self.assertEqual(result,{'request_id':'query-1','outcome':'proposed','full_request_disclosed':False})
        with self.assertRaises(Rejected):self.receive()

    def test_replay_rejected_before_expensive_decrypt_and_compare(self):
        from unittest.mock import patch
        import begin_network.local_discovery as module
        with patch.object(module,'open_match_query',wraps=module.open_match_query) as decrypt:
            self.receive()
            with self.assertRaises(Rejected):self.receive()
            self.assertEqual(decrypt.call_count,1)

    def test_forwarder_cannot_decrypt(self):
        with self.assertRaises(Rejected):self.receive(recipient_private=decode(encryption_key()['private']))

    def test_expired_or_wrong_matching_permission(self):
        with self.assertRaises(Rejected):self.receive(now=200)
        self.request['body']['action']='answer'
        with self.assertRaises(Rejected):self.receive()

    def test_no_match_role_time_and_semantic(self):
        for candidate in (dict(self.candidate,role='seek'),dict(self.candidate,available_until=140),dict(self.candidate,values=[0.0,1.0])):
            self.assertFalse(evaluate(self.query,candidate,150))
        with self.assertRaises(Rejected):evaluate(self.query,dict(self.candidate,model='other-model'),150)

    def test_oversized_coordinates_rejected(self):
        with self.assertRaises(Rejected): evaluate(dict(self.query,values=[10**1000,0]),self.candidate,150)

    def test_ciphertext_substitution_rejected(self):
        self.box=seal(b'{"attacker":"payload"}',decode(self.encryption['public']),'query-1',self.owner['kid'])
        with self.assertRaises(Rejected):self.receive()

    def test_offline_encrypted_mailbox_then_local_evaluation(self):
        path=self.tmp.name+'/mailbox.sqlite'
        mailbox=Mailbox(path,clock=lambda:150)
        request,grant=self.tokens()
        bundle=json.dumps({'request':request,'grant':grant,'box':self.box}).encode()
        self.assertNotIn(b'synthetic-l2-v1',bundle)
        mailbox.submit('query-1',self.owner['kid'],bundle,200)
        mailbox.close()
        mailbox=Mailbox(path,clock=lambda:160)
        self.assertEqual(mailbox.retrieve('other-owner'),[])
        delivery=mailbox.retrieve(self.owner['kid'])[0]
        restored=json.loads(delivery.ciphertext)
        self.assertTrue(mailbox.claim(self.owner['kid'],'query-1'))
        result=receive_query(restored['request'],restored['grant'],restored['box'],keys=self.keys,
            audience=self.owner['kid'],authority=self.owner['kid'],recipient_private=decode(self.encryption['private']),
            owner=self.candidate,replay=self.replay,now=160)
        self.assertEqual(result['outcome'],'proposed')
        self.assertTrue(mailbox.acknowledge(self.owner['kid'],'query-1'))
        self.assertFalse(mailbox.claim(self.owner['kid'],'query-1'))
        mailbox.close()

if __name__=='__main__':unittest.main()
