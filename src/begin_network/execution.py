"""Bounded synthetic goal executor with signed, encrypted result and durable state.

No arbitrary code, file paths, commands or network tools are accepted. Only the
registered deterministic fixture operation below is implemented.
"""
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .envelope import VERSION, Rejected, public_key, key_id, verify, sign, strict_json, validate_task_body
from .sealed import seal, sealed_digest, _decrypt_bound

METHOD = 'interval-intersection-v1'
RESULT_PROFILE = 'begin-task-result-v1'


def _slots(value, max_count=32):
    if not isinstance(value, list) or not 1 <= len(value) <= max_count:
        raise Rejected('invalid bounded time slot count')
    previous = -1
    for pair in value:
        if not isinstance(pair, list) or len(pair) != 2 or any(type(v) is not int for v in pair) or not 0 <= pair[0] < pair[1] <= 1440 or pair[0] < previous:
            raise Rejected('invalid or overlapping minute slots')
        previous = pair[1]
    return value


def intersections(left, right):
    _slots(left); _slots(right)
    return sorted([max(a,c),min(b,d)] for a,b in left for c,d in right if max(a,c)<min(b,d))


class FixtureWorker:
    def __init__(self, *, private, encryption_private, requester_encryption_keys, ledger, resources):
        self.private, self.encryption_private = private, encryption_private
        self.id = key_id(public_key(Ed25519PrivateKey.from_private_bytes(private)))
        if ledger.audience != self.id:
            raise Rejected('worker identity does not match permission audience')
        self.ledger, self.recipient_keys = ledger, dict(requester_encryption_keys)
        self.resources = {}
        for resource, fixture in resources.items():
            if not isinstance(resource,str) or not resource.startswith('fixture:') or not isinstance(fixture,dict) or set(fixture) != {'kind','revision','slots'} or fixture['kind'] != 'synthetic' or not isinstance(fixture['revision'],str) or not fixture['revision']:
                raise Rejected('only explicit synthetic fixture resources supported')
            _slots(fixture['slots'])
            self.resources[resource] = json.loads(json.dumps(fixture))
        ledger.db.execute('''CREATE TABLE IF NOT EXISTS executions (
            operation TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL,
            token TEXT, box TEXT)''')

    def execute(self, request_token, grant_tokens, box, *, now):
        if type(now) is not int:
            raise Rejected('integer execution timestamp required')
        request = verify(request_token,self.ledger.keys,self.id,now=now)
        body = validate_task_body(request['body'])
        if request['type'] != 'request' or body['purpose'] != 'calendar-overlap' or body['action'] != 'available-overlap' or body['units'] != 1 or body['resource'] not in self.resources:
            raise Rejected('unsupported fixed operation, cost or resource')
        if request['sender'] not in self.recipient_keys:
            raise Rejected('no locally pinned requester encryption key')
        if body.get('sealed_digest') != sealed_digest(box):
            raise Rejected('input not bound to signed task')
        operation = request['sender'] + ':' + request['id']
        request_digest = hashlib.sha256(request_token.encode('ascii')).hexdigest()
        admission = self.ledger.reserve(request_token,grant_tokens,now)
        row = self.ledger.db.execute('SELECT digest,state,token,box FROM executions WHERE operation=?',(operation,)).fetchone()
        if admission == 'duplicate':
            if row and row[0] != request_digest:
                raise Rejected('conflicting execution state')
            if row and row[1] == 'completed':
                return {'status':'completed','duplicate':True,'token':row[2],'box':json.loads(row[3])}
            return {'status':'failed' if row and row[1] == 'failed' else 'pending-or-interrupted','duplicate':True,'token':None,'box':None}
        self.ledger.db.execute("INSERT INTO executions(operation,digest,state) VALUES (?,?,'started')",(operation,request_digest))
        try:
            raw = _decrypt_bound(box,self.encryption_private,request)
            inputs = strict_json(raw)
            if not isinstance(inputs,dict) or set(inputs) != {'slots'}:
                raise Rejected('unsupported fixture inputs')
            fixture = self.resources[body['resource']]
            output = {'slots':intersections(inputs['slots'],fixture['slots'])}
            response_id = request_digest
            encrypted = seal(json.dumps(output,separators=(',',':')).encode(),self.recipient_keys[request['sender']],response_id,request['sender'])
            result = {'version':VERSION,'type':'response','sender':self.id,'id':response_id,
                      'audience':request['sender'],'issued_at':now,'expires_at':request['expires_at'],'proofs':[],
                      'body':{'profile':RESULT_PROFILE,'request_digest':request_digest,'status':'completed',
                              'sealed_digest':sealed_digest(encrypted),'provenance':{'kind':'synthetic-calculation','method':METHOD,
                              'resource_revision':fixture['revision']},
                              'grant_digests':[hashlib.sha256(t.encode('ascii')).hexdigest() for t in grant_tokens]}}
            token = sign(result,self.private)
            self.ledger.db.execute("UPDATE executions SET state='completed',token=?,box=? WHERE operation=?",(token,json.dumps(encrypted),operation))
            return {'status':'completed','duplicate':False,'token':token,'box':encrypted}
        except Exception:
            self.ledger.db.execute("UPDATE executions SET state='failed' WHERE operation=?",(operation,))
            raise


def receive_result(token, box, *, worker_keys, requester_keys, expected_grant_tokens, audience, recipient_private, request_token, replay, now):
    """Verify expected worker, request binding and integrity before opening output."""
    response = verify(token,worker_keys,audience,now=now)
    original = verify(request_token,requester_keys,response['sender'],now=now)
    if original['type'] != 'request' or original['sender'] != audience:
        raise Rejected('response not from original request worker or to original requester')
    task = validate_task_body(original['body'])
    if task['purpose'] != 'calendar-overlap' or task['action'] != 'available-overlap' or task['units'] != 1:
        raise Rejected('response operation does not match expected fixture task')
    body = response['body']
    required = {'profile','request_digest','status','sealed_digest','provenance','grant_digests'}
    expected = hashlib.sha256(request_token.encode('ascii')).hexdigest()
    if response['type'] != 'response' or response['proofs'] or set(body) != required or body['profile'] != RESULT_PROFILE or body['status'] != 'completed' or body['request_digest'] != expected or response['id'] != expected:
        raise Rejected('unexpected task result or request binding')
    provenance = body['provenance']
    if not isinstance(provenance,dict) or set(provenance) != {'kind','method','resource_revision'} or not isinstance(provenance.get('resource_revision'),str) or not provenance['resource_revision'] or provenance.get('kind') != 'synthetic-calculation' or provenance.get('method') != METHOD:
        raise Rejected('unsupported result provenance')
    if not isinstance(body['grant_digests'],list) or not 1 <= len(body['grant_digests']) <= 9 or any(not isinstance(d,str) or len(d)!=64 or any(c not in '0123456789abcdef' for c in d) for d in body['grant_digests']):
        raise Rejected('invalid grant provenance')
    if not isinstance(expected_grant_tokens,list) or not 1 <= len(expected_grant_tokens) <= 9 or any(not isinstance(t,str) for t in expected_grant_tokens) or body['grant_digests'] != [hashlib.sha256(t.encode('ascii')).hexdigest() for t in expected_grant_tokens]:
        raise Rejected('response does not reference expected grant chain')
    if body['sealed_digest'] != sealed_digest(box):
        raise Rejected('result ciphertext substitution')
    replay.admit(response['sender'],response['id'])
    output = strict_json(_decrypt_bound(box,recipient_private,response))
    if not isinstance(output,dict) or set(output) != {'slots'} or not isinstance(output['slots'],list):
        raise Rejected('invalid result shape')
    if output['slots']:
        _slots(output['slots'],max_count=63)
    return {'output':output,'provenance':body['provenance'],'request_digest':expected}
