import copy
import unittest
from begin_network.envelope import *
from begin_network.sealed import encryption_key, seal, open_authorized, sealed_digest

class SealedTests(unittest.TestCase):
    def setUp(self):
        self.key = encryption_key()
        self.sender, self.authority = generate_key(), generate_key()
        self.request = {'version': VERSION, 'type':'request', 'sender':self.sender['kid'], 'id':'task', 'audience':'owner',
                        'issued_at':100, 'expires_at':200, 'proofs':['grant'], 'body':{'purpose':'help','action':'answer','resource':'synthetic','units':1}}
        self.grant = dict(self.request, type='grant', sender=self.authority['kid'], id='grant', proofs=[],
                          body={'subject':self.sender['kid'],'purpose':'help','actions':['answer'],'resource':'synthetic','max_units':1,'delegation_depth':0})
        self.box = seal(b'synthetic private intention',decode(self.key['public']),'task','owner')
        self.request['body']['sealed_digest'] = sealed_digest(self.box)
        self.request = verify(sign(self.request,decode(self.sender['private'])),{self.sender['kid']:decode(self.sender['public'])},'owner',now=150)
        self.grant = verify(sign(self.grant,decode(self.authority['private'])),{self.authority['kid']:decode(self.authority['public'])},'owner',now=150)

    def open(self, **kwargs):
        args = {'box':self.box,'recipient_private':decode(self.key['private']),'request':self.request,'grant':self.grant,
                'authority':self.authority['kid'],'now':150,'matched':True}
        args.update(kwargs)
        return open_authorized(**args)

    def test_authorized_round_trip(self):
        self.assertEqual(self.open(),b'synthetic private intention')

    def test_unmatched_and_revoked(self):
        for kwargs in ({'matched':False},{'revoked_grants':['grant']},{'now':200}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Rejected): self.open(**kwargs)

    def test_wrong_key_and_context(self):
        with self.assertRaises(Rejected): self.open(recipient_private=decode(encryption_key()['private']))
        with self.assertRaises(Rejected): self.open(request=dict(self.request,id='other'))

    def test_tamper(self):
        box = copy.deepcopy(self.box)
        raw = bytearray(decode(box['ciphertext'])); raw[0] ^= 1
        box['ciphertext'] = encode(bytes(raw))
        with self.assertRaises(Rejected): self.open(box=box)

    def test_attacker_cannot_substitute_ciphertext(self):
        replacement = seal(b'attacker text', decode(self.key['public']), 'task', 'owner')
        with self.assertRaises(Rejected): self.open(box=replacement)
