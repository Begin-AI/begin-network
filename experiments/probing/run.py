"""Chosen-query leakage measurement against the actual synthetic owner-local API.

No external data, services, model weights or persisted private keys are used.
"""
import json
import math
import tempfile
from pathlib import Path

from begin_network.envelope import ReplayStore, decode, generate_key, sign
from begin_network.local_discovery import receive_query
from begin_network.sealed import encryption_key, seal, sealed_digest


def run(rounds=12):
    if type(rounds) is not int or not 1 <= rounds <= 20:
        raise ValueError('rounds must be 1..20')
    requester, owner = generate_key(), generate_key()
    encryption = encryption_key()
    keys = {key['kid']: decode(key['public']) for key in (requester, owner)}
    truth = 0.37  # synthetic benchmark truth, never sent to the probing requester
    candidate = {'method': 'synthetic-l2-v1', 'model': 'chosen-query-fixture-v1',
                 'purpose': 'window', 'role': 'offer', 'available_from': 100,
                 'available_until': 190, 'values': [math.cos(truth), math.sin(truth)]}

    def envelope(key, kind, identifier, body, proofs=None):
        return {'version': '0.1-draft', 'type': kind, 'sender': key['kid'],
                'id': identifier, 'audience': owner['kid'], 'issued_at': 100,
                'expires_at': 200, 'body': body, 'proofs': proofs or []}

    grant = envelope(owner, 'grant', 'probe-grant', {
        'subject': requester['kid'], 'purpose': 'begin-discovery', 'actions': ['match'],
        'resource': 'synthetic-owner-intention', 'max_units': 1, 'delegation_depth': 0})
    grant_token = sign(grant, decode(owner['private']))
    low, high = 0.0, math.pi / 2
    transcript = []
    with tempfile.TemporaryDirectory(prefix='begin-probing-') as directory:
        replay = ReplayStore(str(Path(directory) / 'replay.sqlite'))
        try:
            for index in range(rounds):
                midpoint = (low + high) / 2
                angle = midpoint + math.pi / 3
                identifier = 'synthetic-probe-%d' % index
                query = dict(candidate, role='seek', values=[math.cos(angle), math.sin(angle)])
                box = seal(json.dumps(query).encode(), decode(encryption['public']),
                           identifier, owner['kid'])
                request = envelope(requester, 'request', identifier, {
                    'purpose': 'begin-discovery', 'action': 'match',
                    'resource': 'synthetic-owner-intention', 'units': 1,
                    'sealed_digest': sealed_digest(box)}, ['probe-grant'])
                result = receive_query(sign(request, decode(requester['private'])), grant_token,
                    box, keys=keys, audience=owner['kid'], authority=owner['kid'],
                    recipient_private=decode(encryption['private']), owner=candidate,
                    replay=replay, now=150)
                matched = result['outcome'] == 'proposed'
                transcript.append({'probe': index, 'angle': angle, 'matched': matched})
                if matched:
                    low = midpoint
                else:
                    high = midpoint
        finally:
            replay.close()
    estimate = (low + high) / 2
    return {'scope': 'synthetic known-owner 2D chosen-query experiment',
            'mechanism': 'actual signed encrypted receive_query API; direct per-request grant',
            'rounds': rounds, 'accepted_queries': len(transcript), 'per_request_units': 1,
            'grant_max_units': 1, 'grant_is_cumulative': False,
            'assumptions': ['known two-dimensional unit vector in first quadrant',
                            'stable owner vector and availability', 'known fixed cosine threshold 0.5',
                            'authorized requester may select arbitrary normalized query vectors'],
            'synthetic_truth_angle': truth, 'recovered_interval': [low, high],
            'estimated_angle': estimate, 'absolute_angle_error': abs(estimate - truth),
            'interval_width': high - low, 'transcript': transcript,
            'conclusion': 'Boolean outcomes leak direction under repeated chosen queries; P2 not passed'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, allow_nan=False))
