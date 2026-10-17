"""Synthetic bounded goal exchange; no real calendars or arbitrary remote code."""
import json
import hashlib
from pathlib import Path
import tempfile

from begin_network.coordination import Mailbox
from begin_network.envelope import VERSION, ReplayStore, decode, generate_key, sign, verify
from begin_network.execution import FixtureWorker, receive_result
from begin_network.discovery_index import verify_index, ATTESTATION_PROFILE
from begin_network.intentions import Store
from begin_network.local_discovery import receive_query
from begin_network.permissions import GRANT_PROFILE, PermissionLedger
from begin_network.routing import Coordinator
from begin_network.sealed import encryption_key, seal, sealed_digest

NOW = 110
EXPECTED_OVERLAPS = [[570, 600], [800, 840]]


def envelope(key, kind, request_id, audience, body, proofs=None):
    return {'version':VERSION, 'type':kind, 'sender':key['kid'], 'id':request_id,
            'audience':audience, 'issued_at':100, 'expires_at':200,
            'body':body, 'proofs':proofs or []}


def signed(key, payload):
    return sign(payload, decode(key['private']))


def prepare(directory):
    """Create independent synthetic identities, trust policy, and sealed input."""
    directory = Path(directory)
    keys = {name:generate_key() for name in ('owner','delegate','requester','worker','ingress','relay')}
    trusted = {key['kid']:decode(key['public']) for key in keys.values()}
    worker_encryption, requester_encryption = encryption_key(), encryption_key()
    audience = keys['worker']['kid']
    root = envelope(keys['owner'], 'grant', 'mentor-root', audience,
        {'profile':GRANT_PROFILE, 'subject':keys['delegate']['kid'], 'purpose':'calendar-overlap',
         'actions':['available-overlap'], 'resource':'fixture:mentor', 'max_units':2, 'depth':1, 'parent':None})
    leaf = envelope(keys['delegate'], 'grant', 'mentor-requester', audience,
        {'profile':GRANT_PROFILE, 'subject':keys['requester']['kid'], 'purpose':'calendar-overlap',
         'actions':['available-overlap'], 'resource':'fixture:mentor', 'max_units':1, 'depth':0, 'parent':'mentor-root'}, ['mentor-root'])
    grant_tokens = [signed(keys['owner'], root), signed(keys['delegate'], leaf)]
    sealed_input = seal(json.dumps({'slots':[[570,630],[800,860]]}).encode(),
        decode(worker_encryption['public']), 'find-mentor-time', audience)
    request = envelope(keys['requester'], 'request', 'find-mentor-time', audience,
        {'purpose':'calendar-overlap', 'action':'available-overlap', 'resource':'fixture:mentor',
         'units':1, 'sealed_digest':sealed_digest(sealed_input),
         'routing':{'ingress':keys['ingress']['kid'], 'hop_limit':8}}, ['mentor-requester'])
    request_token = signed(keys['requester'], request)
    snapshot = signed(keys['owner'], envelope(keys['owner'], 'revocation', 'fresh-policy', audience,
        {'profile':GRANT_PROFILE, 'revoked':[]}))
    return {'directory':directory, 'keys':keys, 'trusted':trusted,
            'worker_encryption':worker_encryption, 'requester_encryption':requester_encryption,
            'grant_tokens':grant_tokens, 'request_token':request_token,
            'request':request, 'sealed_input':sealed_input, 'snapshot':snapshot}


def bootstrap(scenario):
    """Verify a synthetic publisher attestation of the repository method index.

    The fixture refreshes only a local copy's generation time under its fake clock.
    It never claims that the real seed index has a production publisher signature.
    """
    value = json.loads((Path(__file__).resolve().parents[1]/'discovery'/'index.json').read_text())
    value['generated_at'] = '1970-01-01T00:01:40Z'
    raw = json.dumps(value,sort_keys=True).encode()
    owner = scenario['keys']['owner']
    audience = 'synthetic-goal-bootstrap'
    attestation = signed(owner,envelope(owner,'response','goal-method-index',audience,
        {'profile':ATTESTATION_PROFILE,'index_sha256':hashlib.sha256(raw).hexdigest(),
         'protocol_version':VERSION,'generated_at':value['generated_at']}))
    checked = verify_index(raw,attestation,{owner['kid']:decode(owner['public'])},audience,now=NOW,max_age=100,
        requested_contracts=[{'id':'begin/owner-local-v1','method_version':'1','model':'per-session-pinned-model',
                              'dimensions':'dynamic','normalization':'l2'}])
    if checked['authority_granted'] or checked['nodes']:
        raise AssertionError('fixture index unexpectedly grants authority or claims operating nodes')
    return {'attestation_verified':True,'method':checked['methods'][0]['id'],
            'authority_granted':False,'operating_nodes':0,'publisher_policy':'locally-pinned-synthetic-owner'}


def discover(scenario, *, requester_topic='guitar', mentor_topic='guitar', requester_consent=True, mentor_consent=True):
    """Known-candidate synthetic formation/representation/discovery phase.

    Fixed topic coordinates demonstrate contracts, not learned semantic quality.
    This is application ordering, not cryptographic conditional key release.
    """
    if type(requester_consent) is not bool or type(mentor_consent) is not bool:
        raise ValueError('explicit fixture consent required')
    if not requester_consent or not mentor_consent:
        return {'outcome':'declined','full_request_disclosed':False}
    topics = ('guitar','piano')
    if requester_topic not in topics or mentor_topic not in topics:
        raise ValueError('only declared synthetic topic fixtures supported')
    store = Store()
    store.create('learner','integrated',perspectives={k: ['Learn '+requester_topic] for k in ('mirror','window','social')},aspirations=['Learn '+requester_topic],consent=True,disclosure=['aspirations'],
                 role='seek',available_from=100,available_until=190,expires_at=200)
    store.create('mentor','integrated',perspectives={k: ['Teach '+mentor_topic] for k in ('mirror','window','social')},facts=['Teach '+mentor_topic],consent=True,disclosure=['facts'],
                 role='offer',available_from=100,available_until=190,expires_at=200)
    def representation(id,topic):
        vector = store.vector(id,[float(topic==item) for item in topics],
                              'synthetic-goal-topics-v1','guitar-piano-fixture-v1')
        intention = store.get(id)
        return {'method':vector.method,'model':vector.model,'purpose':vector.purpose,'role':intention.role,
                'available_from':intention.available_from,'available_until':intention.available_until,'values':list(vector.values)}
    query,owner = representation('learner',requester_topic),representation('mentor',mentor_topic)
    keys = scenario['keys']; audience = keys['worker']['kid']
    box = seal(json.dumps(query).encode(),decode(scenario['worker_encryption']['public']),'mentor-discovery',audience)
    request = envelope(keys['requester'],'request','mentor-discovery',audience,
        {'purpose':'begin-discovery','action':'match','resource':'fixture:mentor-discovery','units':1,
         'sealed_digest':sealed_digest(box)},['mentor-match-grant'])
    grant = envelope(keys['owner'],'grant','mentor-match-grant',audience,
        {'subject':keys['requester']['kid'],'purpose':'begin-discovery','actions':['match'],
         'resource':'fixture:mentor-discovery','max_units':1,'delegation_depth':0})
    replay = ReplayStore(scenario['directory']/'matching-replay.sqlite')
    try:
        result = receive_query(signed(keys['requester'],request),signed(keys['owner'],grant),box,
            keys=scenario['trusted'],audience=audience,authority=keys['owner']['kid'],
            recipient_private=decode(scenario['worker_encryption']['private']),owner=owner,replay=replay,now=NOW)
        return dict(result,method=query['method'],model=query['model'],dimension=2,
                    representation_kind='manual-synthetic-fixture',candidate_bootstrap='known-local-fixture')
    finally:
        replay.close()


def route_original(scenario):
    """Verify and relay the signed original across distinct coordinator identities."""
    keys = scenario['keys']
    destination = keys['worker']['kid']
    nodes, stores, transmissions = {}, [], []
    def transport(peer, packet):
        transmissions.append(peer)
        return nodes[peer].receive(packet)
    try:
        for name, next_name in (('ingress','relay'), ('relay','worker'), ('worker',None)):
            replay = ReplayStore(scenario['directory'] / (name + '-routing.sqlite'))
            stores.append(replay)
            node = Coordinator(decode(keys[name]['private']),
                {keys[n]['kid']:decode(keys[n]['public']) for n in ('ingress','relay','worker')},
                {keys['requester']['kid']:decode(keys['requester']['public'])},
                {destination:[keys[next_name]['kid']]} if next_name else {}, replay, transport, clock=lambda:NOW)
            nodes[node.id] = node
        routed = nodes[keys['ingress']['kid']].submit(scenario['request_token'], destination)
        if routed != scenario['request']: raise AssertionError('routed original changed')
        return transmissions
    finally:
        for store in stores: store.close()


def open_worker(scenario):
    keys = scenario['keys']
    ledger = PermissionLedger(scenario['directory'] / 'owner-budget.sqlite',
        audience=keys['worker']['kid'], authority=keys['owner']['kid'], trusted_keys=scenario['trusted'])
    ledger.apply_revocations(scenario['snapshot'], NOW)
    worker = FixtureWorker(private=decode(keys['worker']['private']),
        encryption_private=decode(scenario['worker_encryption']['private']),
        requester_encryption_keys={keys['requester']['kid']:decode(scenario['requester_encryption']['public'])},
        ledger=ledger,
        resources={'fixture:mentor':{'kind':'synthetic','revision':'fixture-v1','slots':[[540,600],[780,840]]}})
    return ledger, worker


def receive(scenario, delivery, replay):
    message = json.loads(delivery.ciphertext)
    return receive_result(message['token'], message['box'],
        worker_keys={scenario['keys']['worker']['kid']:decode(scenario['keys']['worker']['public'])},
        audience=scenario['keys']['requester']['kid'],
        recipient_private=decode(scenario['requester_encryption']['private']),
        requester_keys={scenario['keys']['requester']['kid']:decode(scenario['keys']['requester']['public'])},
        expected_grant_tokens=scenario['grant_tokens'],
        request_token=scenario['request_token'], replay=replay, now=NOW)


def run(directory, **discovery_options):
    scenario = prepare(directory)
    selected = bootstrap(scenario)
    proposal = discover(scenario, **discovery_options)
    if proposal['outcome'] != 'proposed':
        return {'goal':'find compatible synthetic mentor availability','status':proposal['outcome'],
                'executions':0,'full_request_disclosed':False,'discovery':proposal}
    route = route_original(scenario)
    ledger, worker = open_worker(scenario)
    mailbox_path = scenario['directory'] / 'requester-mailbox.sqlite'
    recipient = scenario['keys']['requester']['kid']
    box = Mailbox(mailbox_path, clock=lambda:NOW)
    try:
        result = worker.execute(scenario['request_token'], scenario['grant_tokens'], scenario['sealed_input'], now=NOW)
        if result['duplicate'] or result['status'] != 'completed': raise AssertionError('first operation did not complete')
        operation = hashlib.sha256(scenario['request_token'].encode('ascii')).hexdigest()
        message = json.dumps({'token':result['token'], 'box':result['box']},sort_keys=True).encode()
        # Only encrypted output goes to the mailbox. Host pins the recipient identity.
        box.submit(operation, recipient, message, scenario['request']['expires_at'])
        duplicate = worker.execute(scenario['request_token'], scenario['grant_tokens'], scenario['sealed_input'], now=NOW)
        if not duplicate['duplicate'] or duplicate['token'] != result['token'] or duplicate['box'] != result['box']:
            raise AssertionError('duplicate execution did not return exact cached result')
        if box.submit(operation, recipient, message, scenario['request']['expires_at']) != 'pending':
            raise AssertionError('mailbox retry changed state')
        spent = dict(ledger.db.execute('SELECT id,spent FROM grants'))
        executions = ledger.db.execute("SELECT COUNT(*) FROM executions WHERE state='completed'").fetchone()[0]
        if spent != {'mentor-root':1, 'mentor-requester':1} or executions != 1:
            raise AssertionError('duplicate changed accounting or execution count')
        # Requester disconnects. Later it opens a new database connection.
        box.close()
        box = Mailbox(mailbox_path, clock=lambda:NOW)
        if box.retrieve(scenario['keys']['delegate']['kid']): raise AssertionError('wrong recipient can retrieve')
        deliveries = box.retrieve(recipient)
        if len(deliveries) != 1: raise AssertionError('expected one durable result')
        replay = ReplayStore(scenario['directory'] / 'requester-results.sqlite')
        try:
            received = receive(scenario, deliveries[0], replay)
        finally:
            replay.close()
        if received['output']['slots'] != EXPECTED_OVERLAPS: raise AssertionError('incorrect overlap calculation')
        if not box.claim(recipient, operation) or not box.acknowledge(recipient, operation):
            raise AssertionError('result not acknowledged')
        if box.retrieve(recipient): raise AssertionError('acknowledged result redelivered')
        return {'goal':'find compatible synthetic mentor availability', 'bootstrap':selected, 'discovery':proposal, 'route_hops':len(route),
            'verified_output':received['output'], 'provenance':received['provenance'],
            'budget_spent':spent, 'executions':executions, 'duplicate_reexecuted':False,
            'offline_retrieval_verified':True, 'real_calendar_access':False}
    finally:
        box.close()
        ledger.close()


def main():
    with tempfile.TemporaryDirectory(prefix='begin-goal-') as directory:
        print(json.dumps(run(directory), indent=2))


if __name__ == '__main__': main()
