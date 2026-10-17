"""Synthetic owner-local discovery. Transit nodes see encrypted matching inputs.

The counterpart learns the authorized query vector. This is NOT private matching
against a malicious counterpart, anonymous discovery, or global candidate search.
"""
import json
import math
from .envelope import Rejected, strict_json, verify, authorize
from .sealed import open_match_query, sealed_digest

FIELDS = {'method', 'model', 'purpose', 'role', 'available_from', 'available_until', 'values'}


def validate_query(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise Rejected('unsupported matching query fields')
    if any(not isinstance(value[k], str) or not value[k] for k in ('method', 'model', 'purpose')) or value['role'] not in ('seek', 'offer', 'peer'):
        raise Rejected('invalid matching contract')
    if value['purpose'] != 'integrated':
        raise Rejected('legacy single-purpose representation rejected')
    if type(value['available_from']) is not int or type(value['available_until']) is not int or value['available_from'] >= value['available_until']:
        raise Rejected('invalid availability')
    vector = value['values']
    if not isinstance(vector, list) or not 1 <= len(vector) <= 384 or any(type(v) not in (int, float) or abs(v) > 1 or not math.isfinite(v) for v in vector):
        raise Rejected('invalid query vector')
    if not math.isclose(sum(v*v for v in vector), 1, abs_tol=1e-6):
        raise Rejected('query must be L2 normalized')
    return value


def evaluate(query, owner, now, *, threshold=0.5):
    validate_query(query); validate_query(owner)
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not -1 <= threshold <= 1:
        raise Rejected('invalid matching threshold')
    if any(query[k] != owner[k] for k in ('method', 'model', 'purpose')) or len(query['values']) != len(owner['values']):
        raise Rejected('incompatible matching contract')
    roles = (query['role'], owner['role'])
    if roles not in (('seek','offer'), ('offer','seek'), ('peer','peer')):
        return False
    if max(now, query['available_from'], owner['available_from']) >= min(query['available_until'], owner['available_until']):
        return False
    return sum(a*b for a,b in zip(query['values'], owner['values'])) >= threshold


def receive_query(request_token, grant_token, box, *, keys, audience, authority, recipient_private, owner, replay, now):
    """Host explicitly chooses authority, keys, owner data and consent policy.

    Caller only invokes this handler for opted-in owners. It returns a boolean,
    not a transferable proof of honest computation or a permission to disclose.
    """
    request = verify(request_token, keys, audience, now=now)
    grant = verify(grant_token, keys, audience, now=now)
    authorize(request, grant, authority, now)
    if request['body']['action'] != 'match' or request['body']['purpose'] != 'begin-discovery':
        raise Rejected('explicit matching permission required')
    if request['body'].get('sealed_digest') != sealed_digest(box):
        raise Rejected('sealed query not bound to signed request')
    replay.admit(request['sender'], request['id'])
    raw = open_match_query(box, recipient_private, request, grant, authority, now)
    query = strict_json(raw)
    result = evaluate(query, owner, now)
    return {'request_id':request['id'], 'outcome':'proposed' if result else 'no-match', 'full_request_disclosed':False}
