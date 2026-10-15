"""Same-host HTTPS service integration; no independently operated host claim."""
import copy
import asyncio
import importlib.util
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests'))
from test_runtime_mcp import test_certificate
from harness import Committee, private_write
from support import source_hashes
from begin_network.discovery_client import RemotePool
from begin_network.envelope import generate_key, strict_json
from begin_network.encoders import SyntheticEncoder
from begin_network.runtime_bridge import Participant
from begin_network.shared_index import enroll, revocations


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='begin-node-service-')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.committee = Committee(self.root / 'nodes')
        self.committee.close()  # From here, all enrollment and job access is HTTPS.
        self.people = []
        self.children = []
        self.addCleanup(self.cleanup)
        self.requester = self.person('requester', 'seek')
        self.candidate = self.person('candidate', 'offer')
        self.enroller = generate_key()  # Separate pseudonym; not candidate address.
        self.other = generate_key()
        sockets = [socket.socket() for _ in range(3)]
        for sock in sockets:
            sock.bind(('127.0.0.1', 0))
        self.parties = [{'index': i, 'host': '127.0.0.1', 'port': s.getsockname()[1], 'kid': self.committee.keys[i]['kid']}
                        for i, s in enumerate(sockets)]
        for sock in sockets:
            sock.close()
        self.configs = []
        nodes = []
        for i, directory in enumerate(self.committee.dirs):
            test_certificate(directory)
            config = {'data_policy': 'synthetic-only', 'state_directory': str(directory), 'party_index': i,
                'node_key': self.committee.keys[i], 'pool': self.committee.id,
                'worker_path': str(Path(__file__).with_name('party.py').resolve()), 'pinned_sources': source_hashes(),
                'pinned_parties': self.parties, 'pinned_keys': {k['kid']: k['public'] for k in self.committee.keys},
                'clients': {self.requester.id: {'public': self.requester.signing['public'], 'roles': ['query']},
                            self.enroller['kid']: {'public': self.enroller['public'], 'roles': ['enroll']},
                            self.other['kid']: {'public': self.other['public'], 'roles': ['query']}},
                'certificate': str(directory / 'tls.pem'), 'private_key': str(directory / 'tls.key'), 'port': 0}
            self.configs.append(config)
            port = self.launch(i)
            nodes.append({'kid': config['node_key']['kid'], 'public': config['node_key']['public'],
                          'endpoint': 'https://127.0.0.1:' + str(port), 'ca_file': config['certificate']})
        self.remote = RemotePool({'pool': self.committee.id, 'sources': source_hashes(), 'parties': self.parties, 'nodes': nodes})
        self.candidate.configure_discovery_pools([self.committee.id])
        self.offer = self.candidate.offer_discovery('intent', self.committee.id)
        _, representation = self.candidate.representation('intent')
        self.owner, self.uploads = enroll(self.offer['card'], representation, self.committee.id, self.committee.keys, now=int(time.time()))
        self.remote.upload(self.enroller, self.uploads)

    def person(self, name, role):
        p = Participant(self.root / name, encoder=SyntheticEncoder())
        now = int(time.time())
        p.set_intention('intent', purpose='window', role=role, facts=[], aspirations=['synthetic guitar'], inferences=[],
                        consent=True, disclosure=['aspirations'], available_from=now, available_until=now+600, expires_at=now+900)
        self.people.append(p)
        return p

    def launch(self, i):
        path = self.committee.dirs[i] / 'service.json'
        private_write(path, self.configs[i])
        child = subprocess.Popen([sys.executable, '-m', 'begin_network.discovery_service', '--config', str(path)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.children.append(child)
        ready, _, _ = select.select([child.stdout], [], [], 15)
        self.assertTrue(ready, 'service startup timed out')
        line = child.stdout.readline()
        if not line:
            self.fail('service failed before readiness; inspect private fixture diagnostics')
        return strict_json(line)['port']

    def cleanup(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
        for child in self.children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()
            child.stderr.close()
        for p in self.people:
            p.close()

    def plan(self):
        _, representation = self.requester.representation('intent')
        return self.remote.plan(representation, self.requester)

    def test_https_enrollment_discovery_durable_result_and_authorization(self):
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, generate_key(), 'snapshot', {'contract': {}})
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, self.enroller, 'snapshot', {'contract': {}})
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, self.requester.signing, 'upload', self.uploads[0])
        job = self.plan()
        self.assertNotIn('shares', str(job['boxes']))
        self.assertNotIn(self.candidate.id, str(job))
        self.assertNotIn('synthetic guitar', str(job))
        # No controller-generated node consents or direct database enrollment.
        self.remote.start(job, self.requester)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = self.remote.poll(job, self.requester)
            if result['state'] != 'pending':
                break
            time.sleep(0.1)
        self.assertEqual(result['state'], 'complete', result)
        self.assertEqual(result['cards'], [self.offer['card']])
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, self.other, 'result', {'id': job['session']['id']})
        # Reopening a real service preserves the encrypted output, without rerun.
        child = self.children[0]
        child.terminate()
        child.wait(timeout=10)
        self.configs[0]['port'] = int(self.remote.nodes[0]['endpoint'].rsplit(':', 1)[1])
        self.launch(0)
        self.assertEqual(self.remote.poll(job, self.requester), result)
        self.assertEqual(self.remote.start(job, self.requester), [{'state': 'complete'}] * 3)

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'optional MCP SDK required')
    def test_mcp_tools_enroll_search_restart_and_withdraw_over_https(self):
        self.remote.upload(self.enroller, revocations(self.owner, self.committee.keys, now=int(time.time())))
        for name in ('candidate', 'requester'):
            remote = dict(self.remote.config, enrollment_key=self.enroller)
            config = {'data_policy': 'synthetic-only', 'state_directory': str(self.root / name),
                      'encoder': {'kind': 'synthetic'}, 'peers': [], 'discovery_pools': [self.committee.id],
                      'discovery_services': {self.committee.id: remote},
                      'relay': {'id': 'unused-relay', 'endpoint': 'https://127.0.0.1:1'}, 'bootstrap': {}}
            private_write(self.root / (name + '.json'), config)
        asyncio.run(self.mcp_discovery())

    async def mcp_discovery(self):
        from mcp import Client, StdioServerParameters
        def client(name):
            return Client(StdioServerParameters(command=sys.executable,
                args=['-m', 'begin_network.mcp_adapter', '--config', str(self.root / (name + '.json'))]), read_timeout_seconds=20)
        async def call(c, name, args):
            result = await c.call_tool(name, args)
            self.assertFalse(result.is_error, str(result.content))
            return result.structured_content
        async with client('candidate') as c, client('requester') as r:
            self.assertEqual(len((await r.list_tools()).tools), 20)
            args = {'pool': self.committee.id, 'intention_id': 'intent', 'idempotency_key': 'one'}
            enrollment = await call(c, 'begin_publish_intention', args)
            self.assertEqual(await call(c, 'begin_publish_intention', args), enrollment)
            search = await call(r, 'begin_search_network', args)
        # Both participant adapters stop; node services continue the saved job.
        async with client('requester') as r, client('candidate') as c:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                result = await call(r, 'begin_check_search', {'search_id': search['search_id']})
                if result['state'] != 'pending':
                    break
                await asyncio.sleep(0.1)
            self.assertEqual(result['state'], 'complete', result)
            self.assertEqual([m['identity']['address'] for m in result['matches']], [self.candidate.id])
            await call(c, 'begin_withdraw_enrollment', {'enrollment_id': enrollment['enrollment_id']})
            revoked = self.candidate.records('invitations')
            self.assertTrue(all(v['revoked'] or k == self.offer['invitation_id'] for k, v in revoked.items()))

    def test_missing_consents_mutation_and_revocation_fail_closed(self):
        job = self.plan()
        preparations = job['preparations']
        prepared = self.remote.each(self.requester.signing, 'prepare', preparations)
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, self.requester.signing, 'commit', {'id': job['session']['id'], 'consents': [prepared[0]['consent']]})
        changed = copy.deepcopy(preparations[0])
        changed['query_share'][0] += 1
        with self.assertRaises(HTTPError):
            self.remote.rpc(0, self.requester.signing, 'prepare', changed)
        self.remote.upload(self.enroller, revocations(self.owner, self.committee.keys, now=int(time.time())))
        with self.assertRaises(HTTPError):
            self.remote.each(self.requester.signing, 'commit', [{'id': job['session']['id'], 'consents': [p['consent'] for p in prepared]}] * 3)
        states = self.remote.each(self.requester.signing, 'result', [{'id': job['session']['id']}] * 3)
        self.assertTrue(all(s == {'state': 'prepared', 'result': None} for s in states))
        self.remote.each(self.requester.signing, 'cancel', [{'id': job['session']['id']}] * 3)
        self.assertEqual(self.remote.poll(job, self.requester)['state'], 'failed')


if __name__ == '__main__':
    unittest.main()
