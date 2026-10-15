"""Optional SDK/process/TLS integration. Install .[client] on Python 3.11+."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from begin_network.discovery_index import ATTESTATION_PROFILE
from begin_network.encoders import SyntheticEncoder
from begin_network.envelope import VERSION, decode, generate_key, sign
from begin_network.runtime_bridge import Participant, canonical

HAS_MCP = sys.version_info >= (3, 11) and importlib.util.find_spec('mcp') is not None
HAS_MPC = importlib.util.find_spec('mpyc') is not None


def test_certificate(root):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Begin synthetic loopback test')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(private.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True).sign(private, hashes.SHA256()))
    (root / 'tls.pem').write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    fd = os.open(root / 'tls.key', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


@unittest.skipUnless(HAS_MCP, 'install optional .[client] dependencies on Python 3.11+')
class MCPProcessTests(unittest.TestCase):
    def test_two_mcp_participants_original_runtime_and_blind_https_relay(self):
        self.exercise()

    @unittest.skipUnless(HAS_MPC, 'install optional hash-locked MPyC experiment dependency')
    def test_unfamiliar_mcp_participants_shared_index_and_https_relay(self):
        self.exercise(shared_index=True)

    def exercise(self, shared_index=False):
        with tempfile.TemporaryDirectory(prefix='begin-runtime-mcp-') as folder:
            root = Path(folder)
            test_certificate(root)
            committee = None
            if shared_index:
                sys.path.insert(0, str(Path(__file__).parents[1] / 'experiments/shared_index'))
                from harness import Committee
                committee = Committee(root / 'discovery-pool')
            identities = []
            for name in ('a', 'b'):
                participant = Participant(root / name, encoder=SyntheticEncoder())
                identities.append(participant.identity())
                participant.close()
            relay_config = {'data_policy': 'synthetic-only', 'database': str(root / 'relay.sqlite'),
                'service_id': 'independent-fixture-relay', 'certificate': str(root / 'tls.pem'),
                'private_key': str(root / 'tls.key'),
                'participant_keys': {i['address']: i['signing_public'] for i in identities}}
            (root / 'relay.json').write_text(canonical(relay_config))
            child = subprocess.Popen([sys.executable, '-m', 'begin_network.relay_transport', '--config', str(root / 'relay.json')],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                ready, _, _ = select.select([child.stdout], [], [], 10)
                self.assertTrue(ready, 'relay readiness timed out')
                line = child.stdout.readline()
                if not line:
                    raise AssertionError('relay exited before ready: ' + child.stderr.read(4096))
                address = json.loads(line)
                endpoint = 'https://127.0.0.1:' + str(address['port'])
                now = int(time.time())
                stamp = lambda n: datetime.fromtimestamp(n, timezone.utc).isoformat().replace('+00:00', 'Z')
                index = json.loads((Path(__file__).parents[1] / 'discovery/index.json').read_text())
                index['generated_at'] = stamp(now)
                index['nodes'] = [{'id': relay_config['service_id'], 'endpoint': endpoint,
                    'capabilities': ['mailbox'], 'expires_at': stamp(now + 900), 'trust': 'unverified-advertisement'}]
                raw = canonical(index).encode()
                publisher = generate_key()
                attestation = sign({'version': VERSION, 'type': 'response', 'sender': publisher['kid'], 'id': 'fixture-index',
                    'audience': 'fixture-bootstrap', 'issued_at': now, 'expires_at': now + 900, 'proofs': [],
                    'body': {'profile': ATTESTATION_PROFILE, 'index_sha256': hashlib.sha256(raw).hexdigest(),
                    'protocol_version': VERSION, 'generated_at': index['generated_at']}}, decode(publisher['private']))
                (root / 'index.json').write_bytes(raw); (root / 'index.jws').write_text(attestation)
                for name, peer in (('a', identities[1]), ('b', identities[0])):
                    config = {'data_policy': 'synthetic-only', 'state_directory': str(root / name),
                        'encoder': json.loads(os.environ.get('BEGIN_TEST_ENCODER', '{"kind":"synthetic"}')),
                        'peers': [] if committee else [peer], 'discovery_pools': [committee.id] if committee else [],
                        'relay': {'id': relay_config['service_id'], 'endpoint': endpoint, 'ca_file': str(root / 'tls.pem')},
                        'bootstrap': {'sources': [[str(root / 'offline-index'), str(root / 'offline-signature')],
                                                 [str(root / 'index.json'), str(root / 'index.jws')]],
                                      'pins': {publisher['kid']: publisher['public']}, 'audience': 'fixture-bootstrap'}}
                    (root / (name + '.json')).write_text(canonical(config))
                asyncio.run(self.exchange(root, identities, now, committee))
                with sqlite3.connect(root / 'relay.sqlite') as db:
                    count = db.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0]
                    self.assertEqual(count, 6)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM deliveries WHERE state!='acknowledged'").fetchone()[0], 0)
                self.assertNotIn(b'Synthetic private description', (root / 'relay.sqlite').read_bytes())
            finally:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=5)
                child.stdout.close(); child.stderr.close()
                if committee:
                    committee.close()

    async def exchange(self, root, identities, now, committee=None):
        from mcp import Client, StdioServerParameters

        def client(name):
            return Client(StdioServerParameters(command=sys.executable,
                args=['-m', 'begin_network.mcp_adapter', '--config', str(root / (name + '.json'))]), read_timeout_seconds=20)

        async def call(client, name, args=None, *, error=False):
            result = await client.call_tool(name, args or {})
            self.assertEqual(result.is_error, error, str(result.content))
            return result.structured_content

        async with client('a') as a, client('b') as b:
            tools = await a.list_tools()
            self.assertEqual(len(tools.tools), 15)
            self.assertEqual((await call(a, 'begin_identity'))['address'], identities[0]['address'])
            for c, key, role in ((a, 'need', 'seek'), (b, 'offer', 'offer')):
                await call(c, 'begin_set_intention', {'intention_id': key, 'purpose': 'window',
                    'facts': [], 'aspirations': ['synthetic guitar'], 'inferences': [], 'role': role,
                    'available_from': now, 'available_until': now + 600, 'expires_at': now + 900,
                    'consent': True, 'disclosure': ['aspirations']})
            if committee:
                from begin_network.shared_index import enroll
                from begin_network.encoders import LocalMiniLM
                config = json.loads(os.environ.get('BEGIN_TEST_ENCODER', '{"kind":"synthetic"}'))
                encoder = SyntheticEncoder() if config['kind'] == 'synthetic' else LocalMiniLM(config['directory'], config['file_hashes'])
                offer = await call(b, 'begin_offer_discovery', {'intention_id': 'offer', 'pool': committee.id})
                # Synthetic harness reads each owner's runner state only to feed its
                # local enrollment/query adapter. Each worker receives one share.
                pa = Participant(root / 'a', encoder=encoder)
                pb = Participant(root / 'b', encoder=encoder)
                try:
                    self.assertEqual(pa.records('peers'), {})
                    self.assertEqual(pb.records('peers'), {})
                    _, owner = pb.representation('offer')
                    _, query = pa.representation('need')
                    _, uploads = enroll(offer['card'], owner, committee.id, committee.keys, now=int(time.time()))
                    for node, upload in zip(committee.nodes, uploads):
                        node.apply(upload)
                    cards, *_ = committee.search(query, pa)
                    self.assertEqual(len(cards), 1)
                finally:
                    pa.close(); pb.close()
                tool = 'begin_contact_discovered'
                args = {'intention_id': 'need', 'card': cards[0],
                        'description': 'Synthetic private description: guitar mentoring request.', 'idempotency_key': 'one'}
            else:
                grant = await call(b, 'begin_allow_matching', {'peer': identities[0]['address'], 'intention_id': 'offer'})
                tool = 'begin_discover'
                args = {'intention_id': 'need', 'peer': identities[1]['address'], 'grant': grant['grant'],
                        'description': 'Synthetic private description: guitar mentoring request.', 'idempotency_key': 'one'}
            submission = await call(a, tool, args)
            self.assertEqual((await call(a, tool, args))['request_id'], submission['request_id'])
            request_id = submission['request_id']
            await call(a, 'begin_disclose_request', {'request_id': request_id}, error=True)
            owner_inbox = await call(b, 'begin_check_inbox')
            self.assertEqual(owner_inbox['messages'][0]['outcome'], 'proposed')
            await call(a, 'begin_check_inbox')
            await call(a, 'begin_disclose_request', {'request_id': request_id}, error=True)
            await call(b, 'begin_accept_match', {'request_id': request_id})
            await call(a, 'begin_check_inbox')
            await call(a, 'begin_disclose_request', {'request_id': request_id})
            owner_inbox = await call(b, 'begin_check_inbox')
            self.assertEqual(next(m for m in owner_inbox['messages'] if m['kind'] == 'description')['text'], args['description'])
            await call(b, 'begin_reply', {'request_id': request_id, 'text': 'Synthetic willingness response.', 'idempotency_key': 'response'})
        # Both MCP server processes exited. Fresh requester recovers identity and
        # a response held only as encrypted data at the separate relay process.
        async with client('a') as a:
            self.assertEqual((await call(a, 'begin_identity'))['address'], identities[0]['address'])
            inbox = await call(a, 'begin_check_inbox')
            self.assertTrue(any(m.get('text') == 'Synthetic willingness response.' for m in inbox['messages']))
            await call(a, 'begin_reply', {'request_id': request_id, 'text': 'Synthetic related follow-up.', 'idempotency_key': 'followup'})
            for item in inbox['messages']:
                await call(a, 'begin_acknowledge', {'message_id': item['message_id']})
            self.assertEqual((await call(a, 'begin_check_inbox'))['messages'], [])
        async with client('b') as b:
            inbox = await call(b, 'begin_check_inbox')
            self.assertTrue(any(m.get('text') == 'Synthetic related follow-up.' for m in inbox['messages']))
            for item in inbox['messages']:
                await call(b, 'begin_acknowledge', {'message_id': item['message_id']})


if __name__ == '__main__':
    unittest.main()
