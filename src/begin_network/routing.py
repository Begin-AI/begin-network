"""Explicit-policy local signed coordinator routing; no discovery or execution."""
import hashlib
import time
from .envelope import VERSION, Rejected, decode, key_id, public_key, sign, verify
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class Refused(Rejected):
    """A coordinator voluntarily declines routing."""


def digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


class Coordinator:
    """Route only to locally configured peers, verifying every signed hop.

    Transport is an injected callable (peer_id, packet). Each node must have its
    own ReplayStore. Origins and transit peers have separate explicit trust maps.
    No verified route grants permission to execute the original request.
    """
    def __init__(self, private, peers, origins, routes, replay, transport,
                 *, max_hops=8, clock=time.time):
        if type(max_hops) is not int or not 1 <= max_hops <= 16:
            raise ValueError('max_hops must be between 1 and 16')
        self.private = private
        self.id = key_id(public_key(Ed25519PrivateKey.from_private_bytes(private)))
        self.peers = dict(peers)
        self.origins = dict(origins)
        self.routes = {destination: tuple(values) for destination, values in routes.items()}
        self.replay = replay
        self.transport = transport
        self.max_hops = max_hops
        self.clock = clock

    def submit(self, original, destination, *, hop_limit=8):
        """Ingress accepts an origin token explicitly addressed to destination."""
        if type(hop_limit) is not int or not 1 <= hop_limit <= self.max_hops:
            raise Refused('unsupported hop limit')
        payload = verify(original, self.origins, destination, now=int(self.clock()))
        if payload['type'] != 'request':
            raise Refused('only requests can be routed')
        policy = self._origin_policy(payload)
        if policy['ingress'] != self.id or policy['hop_limit'] != hop_limit:
            raise Refused('origin routing policy mismatch')
        self.replay.admit(payload['sender'], payload['id'])
        if destination == self.id:
            return payload
        return self._forward({'original': original, 'hops': []}, payload, hop_limit, [])

    def receive(self, packet):
        if not isinstance(packet, dict) or set(packet) != {'original', 'hops'}:
            raise Rejected('invalid routing packet')
        hops = packet['hops']
        if not isinstance(hops, list) or not 1 <= len(hops) <= self.max_hops:
            raise Refused('invalid route length')
        original = packet['original']
        # Verify latest signer/audience before accepting any supplied routing data.
        latest = verify(hops[-1], self.peers, self.id, now=int(self.clock()))
        expected_fields = {'original_digest', 'destination', 'path', 'hop_limit', 'parent_digest'}
        if latest['type'] != 'request' or set(latest['body']) != expected_fields:
            raise Rejected('invalid routing envelope')
        destination = latest['body']['destination']
        if not isinstance(destination, str) or not destination:
            raise Rejected('invalid destination')
        payload = verify(original, self.origins, destination, now=int(self.clock()))
        if payload['type'] != 'request':
            raise Refused('only requests can be routed')
        policy = self._origin_policy(payload)
        original_digest = digest(original)
        path = []
        limit = latest['body']['hop_limit']
        if type(limit) is not int or limit != policy['hop_limit'] or not 1 <= limit <= self.max_hops or len(hops) > limit:
            raise Refused('hop limit exceeded')
        previous = original
        verified_hops = [verify(token, self.peers, self._audience(token), now=int(self.clock())) for token in hops]
        for index, (token, hop) in enumerate(zip(hops, verified_hops)):
            audience = self.id if index == len(hops) - 1 else verified_hops[index + 1]['sender']
            if hop['audience'] != audience:
                raise Rejected('broken hop audience chain')
            path.append(hop['sender'])
            expected = {'original_digest': original_digest, 'destination': destination,
                        'path': path[:], 'hop_limit': limit, 'parent_digest': digest(previous)}
            if hop['type'] != 'request' or hop['body'] != expected or hop['proofs'] or hop['expires_at'] != payload['expires_at']:
                raise Rejected('broken signed route binding')
            previous = token
        if path[0] != policy['ingress']:
            raise Refused('route does not begin at origin-selected ingress')
        if len(set(path)) != len(path) or self.id in path:
            raise Refused('routing loop')
        self.replay.admit(payload['sender'], payload['id'])
        if destination == self.id:
            return payload
        return self._forward(packet, payload, limit, path)

    @staticmethod
    def _origin_policy(payload):
        policy = payload['body'].get('routing')
        if not isinstance(policy, dict) or set(policy) != {'ingress','hop_limit'} or not isinstance(policy['ingress'],str) or not policy['ingress'] or type(policy['hop_limit']) is not int or not 1 <= policy['hop_limit'] <= 16:
            raise Refused('origin must sign ingress and hop limit')
        return policy

    @staticmethod
    def _audience(token):
        # This value only supplies verify's expected audience; verify authenticates
        # the token and the subsequent chain check binds it to the next signer.
        from .envelope import strict_json
        if not isinstance(token, str) or len(token) > 65536 or len(token.split('.')) != 3:
            raise Rejected('invalid hop token')
        value = strict_json(decode(token.split('.')[1]))
        if not isinstance(value, dict) or not isinstance(value.get('audience'), str):
            raise Rejected('invalid hop audience')
        return value['audience']

    def _forward(self, packet, payload, limit, path):
        if len(path) >= limit:
            raise Refused('hop limit exhausted')
        destination = payload['audience']
        failures = []
        for peer in self.routes.get(destination, ()):
            if peer not in self.peers or peer in path or peer == self.id:
                failures.append('untrusted peer or loop')
                continue
            new_path = path + [self.id]
            body = {'original_digest': digest(packet['original']), 'destination': destination,
                    'path': new_path, 'hop_limit': limit,
                    'parent_digest': digest(packet['hops'][-1] if packet['hops'] else packet['original'])}
            hop = {'version': VERSION, 'type': 'request', 'sender': self.id,
                   'id': hashlib.sha256((body['original_digest'] + repr(new_path) + peer).encode()).hexdigest(),
                   'audience': peer, 'issued_at': int(self.clock()),
                   'expires_at': payload['expires_at'], 'body': body, 'proofs': []}
            token = sign(hop, self.private)
            try:
                return self.transport(peer, {'original': packet['original'], 'hops': packet['hops'] + [token]})
            except (ConnectionError, Refused) as exc:
                failures.append(str(exc))
        raise Refused('no available permitted route: ' + '; '.join(failures))
