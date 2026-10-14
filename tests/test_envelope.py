import copy
import tempfile
import unittest
from begin_network.envelope import *

class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.key = generate_key()
        self.keys = {self.key['kid']: decode(self.key['public'])}
        self.payload = {'version': VERSION, 'type': 'request', 'sender': self.key['kid'], 'id': 'operation-1',
                        'audience': 'receiver', 'issued_at': 100, 'expires_at': 200, 'body': {}, 'proofs': []}

    def signed(self, payload=None):
        return sign(payload or self.payload, decode(self.key['private']))

    def check(self, token=None, **kwargs):
        return verify(token or self.signed(), self.keys, kwargs.pop('audience', 'receiver'), now=kwargs.pop('now', 150), **kwargs)

    def test_malformed_inputs_fail_closed(self):
        for token in ('A.A.A', self.signed(dict(self.payload, type=[]))):
            with self.subTest(token=token[:20]), self.assertRaises(Rejected): self.check(token)
        for raw in (b'{"n":1e999}', '{"id":1}'.encode('utf-16'), ('[' * 1100 + '0' + ']' * 1100).encode()):
            with self.assertRaises(Rejected): strict_json(raw)

    def test_round_trip(self):
        self.assertEqual(self.check(), self.payload)

    def test_tampering_rejected(self):
        parts = self.signed().split('.')
        modified = dict(self.payload, audience='attacker')
        parts[1] = encode(json.dumps(modified).encode())
        with self.assertRaises(Rejected): self.check('.'.join(parts))

    def test_scope_and_time_rejected(self):
        for kwargs in ({'audience': 'other'}, {'now': 200}, {'now': 99}, {'revoked_keys': [self.key['kid']]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Rejected): self.check(**kwargs)

    def test_unsupported_headers(self):
        parts = self.signed().split('.')
        parts[0] = encode(b'{"alg":"none","typ":"begin+jws-v1","kid":"x"}')
        with self.assertRaises(Rejected): self.check('.'.join(parts))

    def test_bad_shape(self):
        for field, value in [('expires_at', True), ('proofs', 'approved'), ('version', 'future'), ('body', []), ('extra', 'ignore')]:
            payload = dict(self.payload, **{field: value})
            with self.subTest(field=field), self.assertRaises(Rejected): self.check(self.signed(payload))

    def test_duplicate_json(self):
        with self.assertRaises(Rejected): strict_json(b'{"id":1,"id":2}')

    def test_replay_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = folder + '/seen.sqlite'
            store = ReplayStore(path)
            self.check(replay=store)
            store.close()
            store = ReplayStore(path)
            with self.assertRaises(Rejected): self.check(replay=store)
            store.close()

    def test_unknown_key(self):
        with self.assertRaises(Rejected): verify(self.signed(), {}, 'receiver', now=150)

    def test_permission_scope(self):
        authority = generate_key()
        grant = dict(self.payload, type='grant', sender=authority['kid'], id='grant-1', body={
            'subject': self.key['kid'], 'purpose': 'synthetic-help', 'actions': ['answer'], 'resource': 'fixture',
            'max_units': 1, 'delegation_depth': 0})
        token = sign(grant, decode(authority['private']))
        checked_grant = verify(token, {authority['kid']: decode(authority['public'])}, 'receiver', now=150)
        request = dict(self.payload, proofs=['grant-1'], body={'purpose': 'synthetic-help', 'action': 'answer', 'resource': 'fixture', 'units': 1})
        checked_request = self.check(self.signed(request))
        self.assertTrue(authorize(checked_request, checked_grant, authority['kid'], 150))
        for field, value in [('units', 2), ('purpose', 'different'), ('action', 'spend'), ('resource', 'private')]:
            bad = copy.deepcopy(checked_request); bad['body'][field] = value
            with self.subTest(field=field), self.assertRaises(Rejected): authorize(bad, checked_grant, authority['kid'], 150)
        with self.assertRaises(Rejected): authorize(checked_request, checked_grant, authority['kid'], 150, ['grant-1'])

if __name__ == '__main__': unittest.main()
