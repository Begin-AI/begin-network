"""Cross-runtime Ed25519/JWS wire interoperability without external npm packages."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from begin_network.envelope import Rejected, decode, encode, generate_key, sign, verify


NODE = shutil.which('node')
HARNESS = Path(__file__).with_name('interop_node.mjs')


@unittest.skipUnless(NODE, 'Node.js unavailable; cross-runtime interoperability unverified')
class NodeInteropTests(unittest.TestCase):
    def call_node(self, request, *, success=True):
        result = subprocess.run([NODE, str(HARNESS)], input=json.dumps(request), text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def payload(self, sender='placeholder'):
        return {'version': '0.1-draft', 'type': 'request', 'sender': sender,
                'id': 'independent-runtime', 'audience': 'recipient',
                'issued_at': 100, 'expires_at': 200,
                'body': {'purpose': 'interoperability', 'unicode': 'café ☕'}, 'proofs': []}

    def test_python_signature_verified_by_node(self):
        key = generate_key()
        payload = self.payload(key['kid'])
        token = sign(payload, decode(key['private']))
        result = self.call_node({'action': 'verify', 'token': token, 'public': key['public']})
        self.assertTrue(result['valid'])
        self.assertEqual(result['payload'], payload)

    def test_node_signature_verified_by_python(self):
        result = self.call_node({'action': 'sign', 'payload': self.payload()})
        verified = verify(result['token'], {result['kid']: decode(result['public'])}, 'recipient', now=150)
        self.assertEqual(verified, result['payload'])

    def test_node_rejects_tampered_python_payload_and_wrong_key(self):
        key = generate_key()
        token = sign(self.payload(key['kid']), decode(key['private']))
        parts = token.split('.')
        body = self.payload(key['kid'])
        body['body']['purpose'] = 'tampered'
        parts[1] = encode(json.dumps(body).encode())
        result = self.call_node({'action': 'verify', 'token': '.'.join(parts), 'public': key['public']}, success=False)
        self.assertFalse(result['valid'])
        wrong = generate_key()
        result = self.call_node({'action': 'verify', 'token': token, 'public': wrong['public']}, success=False)
        self.assertFalse(result['valid'])

    def test_python_rejects_tampered_node_signature_and_audience(self):
        result = self.call_node({'action': 'sign', 'payload': self.payload()})
        keys = {result['kid']: decode(result['public'])}
        parts = result['token'].split('.')
        signature = bytearray(decode(parts[2]))
        signature[0] ^= 1
        parts[2] = encode(signature)
        with self.assertRaises(Rejected):
            verify('.'.join(parts), keys, 'recipient', now=150)
        with self.assertRaises(Rejected):
            verify(result['token'], keys, 'different-recipient', now=150)
