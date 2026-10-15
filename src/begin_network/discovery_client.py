"""Requester-side HTTPS discovery orchestration with operator-pinned peers.

Prepared jobs contain private query shares: callers must persist them privately.
No node private key or node database is available to this client.
"""
from concurrent.futures import ThreadPoolExecutor
import time
import uuid

from .envelope import decode, key_id, verify
from .relay_transport import HTTPSRelay
from .runtime_bridge import require
from .sealed import sealed_digest
from .shared_index import PARAMETERS, PROFILE, contract, fingerprint, private_row, reconstruct, share, signed

API = 'begin-discovery-service-v1'


class RemotePool:
    def __init__(self, config):
        self.config = config
        self.nodes = config['nodes']
        require(len(self.nodes) == 3 and len({n['kid'] for n in self.nodes}) == 3, 'three distinct nodes required')
        require([n['kid'] for n in self.nodes] == [p['kid'] for p in config['parties']], 'node order differs from topology')
        for node in self.nodes:
            require(key_id(decode(node['public'])) == node['kid'], 'node key binding invalid')
        self.pins = {n['kid']: decode(n['public']) for n in self.nodes}
        self.transports = [HTTPSRelay(n['kid'], n['endpoint'], ca_file=n.get('ca_file')) for n in self.nodes]

    def rpc(self, index, key, operation, payload):
        now, identifier = int(time.time()), str(uuid.uuid4())
        token = signed(key, self.nodes[index]['kid'], identifier,
                       {'profile': API, 'operation': operation, 'payload': payload}, now, now + 60)
        response = self.transports[index].call('rpc', {'token': token})
        require(isinstance(response, dict) and set(response) == {'token'}, 'invalid signed response')
        envelope = verify(response['token'], {self.nodes[index]['kid']: self.pins[self.nodes[index]['kid']]},
                          key['kid'], now=int(time.time()), max_lifetime=60)
        body = envelope['body']
        require(envelope['type'] == 'response' and envelope['id'] == identifier and not envelope['proofs'] and
                set(body) == {'profile', 'request_digest', 'result'} and body['profile'] == API and
                body['request_digest'] == fingerprint(token), 'response does not bind request')
        return body['result']

    def each(self, key, operation, payloads):
        require(len(payloads) == 3, 'three node payloads required')
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.rpc, i, key, operation, p) for i, p in enumerate(payloads)]
            # Finish all requests before propagating a failure. Retries reuse the
            # saved session and uploads, never generate another query silently.
            return [future.result() for future in futures]

    def upload(self, admission_key, uploads):
        return self.each(admission_key, 'upload', uploads)

    def plan(self, representation, requester, *, minimum_score=500000):
        method = contract(representation)
        snapshots = self.each(requester.signing, 'snapshot', [{'contract': method}] * 3)
        first = snapshots[0]
        require(all(s == first for s in snapshots) and first['pool'] == self.config['pool'], 'nodes disagree on snapshot')
        records, boxes = first['records'], first['boxes']
        require(0 < len(records) <= PARAMETERS['max_records'] and
                len({r['id'] for r in records}) == len(records) and set(boxes) == {r['id'] for r in records} and
                all(sealed_digest(boxes[r['id']]) == r['card_digest'] for r in records), 'invalid candidate snapshot')
        shares = share(private_row(representation, minimum_score=minimum_score))
        now = int(time.time())
        identity = {k: requester.identity()[k] for k in ('address', 'signing_public', 'encryption_public')}
        session = {'profile': PROFILE, 'id': str(uuid.uuid4()), 'pool': self.config['pool'],
                   'issued_at': now, 'expires_at': min(now + 240, min(r['expires'] for r in records)),
                   'parameters': PARAMETERS, 'sources': self.config['sources'], 'parties': self.config['parties'],
                   'contract': method, 'records': records, 'requester': identity,
                   'query_digests': [fingerprint(s) for s in shares]}
        require(session['expires_at'] > now, 'candidate snapshot expired')
        consent = signed(requester.signing, 'shared-index:' + session['id'], session['id'],
                         {'profile': PROFILE, 'session_digest': fingerprint(session)}, now, session['expires_at'])
        return {'session': session, 'boxes': boxes, 'preparations': [
            {'session': session, 'query_share': s, 'requester_consent': consent} for s in shares]}

    def start(self, job, requester):
        self.check_job(job, requester)
        prepared = self.each(requester.signing, 'prepare', job['preparations'])
        consents = [value['consent'] for value in prepared]
        session = job['session']
        for node, token in zip(self.nodes, consents):
            envelope = verify(token, {node['kid']: self.pins[node['kid']]}, 'shared-index:' + session['id'],
                              now=int(time.time()), max_lifetime=300)
            require(envelope['type'] == 'request' and not envelope['proofs'] and
                    envelope['expires_at'] == session['expires_at'] and envelope['body'] ==
                    {'profile': PROFILE, 'session_digest': fingerprint(session)}, 'invalid node consent')
        return self.each(requester.signing, 'commit', [{'id': session['id'], 'consents': consents}] * 3)

    def check_job(self, job, requester):
        session = job['session']
        require(session['pool'] == self.config['pool'] and session['parties'] == self.config['parties'] and
                session['sources'] == self.config['sources'] and session['requester']['address'] == requester.id and
                int(time.time()) < session['expires_at'], 'wrong or expired private job')

    def poll(self, job, requester):
        self.check_job(job, requester)
        states = self.each(requester.signing, 'result', [{'id': job['session']['id']}] * 3)
        if all(s['state'] == 'complete' for s in states):
            cards = reconstruct(job['session'], [s['result'] for s in states], self.pins,
                                requester.encryption['private'], job['boxes'], now=int(time.time()))
            return {'state': 'complete', 'cards': cards}
        return {'state': 'failed' if any(s['state'] in ('failed', 'cancelled', 'expired') for s in states) else 'pending',
                'nodes': [s['state'] for s in states]}
