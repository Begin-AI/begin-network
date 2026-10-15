"""Bounded introductions released by the experimental shared candidate index.

An invitation is a bearer contact capability, not a computation proof or human
identity. Knowing it permits one proposal; disclosure still needs both owners.
"""
import secrets
import uuid

from .envelope import Rejected, decode, key_id, verify

PROFILE = 'begin-discovery-invitation-v1'


def check(condition, message):
    if not condition:
        raise Rejected(message)


def public_identity(identity):
    check(isinstance(identity, dict) and set(identity) ==
          {'address', 'signing_public', 'encryption_public'}, 'invalid introduction identity')
    check(len(decode(identity['signing_public'])) == 32 and
          key_id(decode(identity['signing_public'])) == identity['address'], 'identity key mismatch')
    check(len(decode(identity['encryption_public'])) == 32, 'invalid encryption key')
    return identity


def invitation_payload(card, now):
    check(isinstance(card, dict) and set(card) == {'identity', 'token'}, 'invalid invitation card')
    identity = public_identity(card['identity'])
    payload = verify(card['token'], {identity['address']: decode(identity['signing_public'])},
                     'begin-discovery-introduction', now=now)
    body = payload['body']
    check(payload['type'] == 'grant' and not payload['proofs'] and
          set(body) == {'profile', 'identity', 'pool', 'capability'} and
          body['profile'] == PROFILE and body['identity'] == identity and
          isinstance(body['pool'], str) and len(body['pool']) == 64 and
          isinstance(body['capability'], str) and len(body['capability']) == 64,
          'invalid invitation scope')
    return payload


class Introductions:
    """Mixin: host-selected pools; no arbitrary trust pins from tool arguments."""

    def configure_discovery_pools(self, pools):
        check(isinstance(pools, list) and len(pools) <= 8 and all(
            isinstance(p, str) and len(p) == 64 and all(c in '0123456789abcdef' for c in p)
            for p in pools), 'invalid operator discovery pools')
        self.put('discovery_policy', 'pools', pools)

    def _discovery_pool(self, pool):
        check(pool in (self.get('discovery_policy', 'pools') or []), 'pool not selected by operator')

    def offer_discovery(self, intention_id, pool, *, ttl=600):
        """Opt into one unfamiliar contact, without publishing an identity or vector."""
        self._discovery_pool(pool)
        check(type(ttl) is int and 1 <= ttl <= 3600, 'invalid invitation lifespan')
        with self.transaction():
            from .runtime_bridge import canonical, digest
            item, representation = self.representation(intention_id)
            active = [v for v in self.records('invitations').values()
                      if v['expires'] > self.now() and not v['revoked']]
            check(len(active) < 32, 'active invitation limit reached')
            invitation_id = str(uuid.uuid4())
            identity = {k: self.identity()[k] for k in ('address', 'signing_public', 'encryption_public')}
            expiry = min(self.now() + ttl, item.expires_at, item.available_until)
            token = self.signed('grant', invitation_id, 'begin-discovery-introduction',
                {'profile': PROFILE, 'identity': identity, 'pool': pool, 'capability': secrets.token_hex(32)}, expiry)
            card = {'identity': identity, 'token': token}
            self.put('invitations', invitation_id, {'card': card, 'intention': intention_id,
                'revision': item.revision, 'representation_digest': digest(canonical(representation)),
                'expires': expiry, 'revoked': False, 'used': None})
        return {'invitation_id': invitation_id, 'card': card, 'expires_at': expiry,
                'scope': 'private index enrollment only; bearer invitation permits one proposal'}

    def revoke_discovery(self, invitation_id):
        with self.transaction():
            invitation = self.get('invitations', invitation_id)
            check(invitation is not None, 'unknown invitation')
            invitation['revoked'] = True
            self.put('invitations', invitation_id, invitation)
        return {'revoked': invitation_id}

    def _live_invitation(self, invitation_id):
        from .runtime_bridge import canonical, digest
        invitation = self.get('invitations', invitation_id)
        check(invitation is not None and not invitation['revoked'] and self.now() < invitation['expires'],
              'invitation expired, revoked or unknown')
        self._discovery_pool(invitation_payload(invitation['card'], self.now())['body']['pool'])
        _, representation = self.representation(invitation['intention'], invitation['revision'])
        check(invitation['representation_digest'] == digest(canonical(representation)), 'representation changed since enrollment')
        return invitation

    def contact_discovered(self, intention_id, card, description, *, idempotency_key):
        from .runtime_bridge import canonical, digest
        payload = invitation_payload(card, self.now())
        self._discovery_pool(payload['body']['pool'])
        check(isinstance(description, str) and 0 < len(description) <= 4096, 'invalid description')
        check(isinstance(idempotency_key, str) and 1 <= len(idempotency_key) <= 128, 'invalid retry key')
        fingerprint = digest(canonical([intention_id, card, description]))
        with self.transaction():
            cached = self.get('introductions_sent', idempotency_key)
            if cached:
                check(cached['digest'] == fingerprint, 'conflicting introduction retry')
                return {'request_id': cached['request'], 'duplicate': True}
            item, _ = self.representation(intention_id)
            peer = card['identity']['address']
            check(peer != self.id, 'self introduction forbidden')
            self.pin_peer(card['identity'])
            request_id = str(uuid.uuid4())
            expires = min(payload['expires_at'], item.expires_at, item.available_until)
            identity = {k: self.identity()[k] for k in ('address', 'signing_public', 'encryption_public')}
            token = self.signed('request', request_id, peer,
                {'profile': PROFILE, 'invitation_digest': digest(card['token']), 'identity': identity}, expires,
                [payload['id']])
            self.put('threads', request_id, {'direction': 'outgoing', 'peer': peer, 'intention': intention_id,
                'revision': item.revision, 'expires': expires, 'request': token, 'status': 'discovering',
                'description': description, 'grant_id': payload['id'], 'discovery': 'shared-index-invitation'})
            message_id = self._queue(peer, {'kind': 'introduction', 'card': card, 'request': token}, expires)
            packet = self.get('outbox', message_id)
            # Self-certification is only enough to attempt an invitation. It never
            # admits a normal query or permits replacing an existing peer key.
            packet['signing_public'] = self.signing['public']
            self.put('outbox', message_id, packet)
            self.put('introductions_sent', idempotency_key, {'digest': fingerprint, 'request': request_id})
        return {'request_id': request_id, 'duplicate': False, 'full_request_disclosed': False}

    def _receive_introduction(self, outer, content, public):
        from .runtime_bridge import digest
        check(set(content) == {'kind', 'card', 'request'}, 'invalid introduction')
        payload = invitation_payload(content['card'], self.now())
        check(payload['sender'] == self.id, 'invitation for another owner')
        invitation = self._live_invitation(payload['id'])
        check(invitation['card'] == content['card'] and invitation['used'] is None, 'invitation used or substituted')
        # The outer signer has already been authenticated, but is not a trusted peer.
        request = verify(content['request'], {outer['sender']: public}, self.id, now=self.now())
        body = request['body']
        check(request['type'] == 'request' and request['sender'] == outer['sender'] and
              request['expires_at'] == outer['expires_at'] and request['expires_at'] <= invitation['expires'] and
              request['proofs'] == [payload['id']] and set(body) == {'profile', 'invitation_digest', 'identity'} and
              body['profile'] == PROFILE and body['invitation_digest'] == digest(content['card']['token']),
              'invalid introduction request binding')
        identity = public_identity(body['identity'])
        check(decode(identity['signing_public']) == public and identity['address'] == outer['sender'],
              'introduction sender substitution')
        check(self.get('threads', request['id']) is None, 'thread collision')
        self.pin_peer(identity)
        grant_id = str(uuid.uuid4())
        grant = self.signed('grant', grant_id, self.id, {'subject': outer['sender'], 'purpose': 'begin-discovery',
            'actions': ['introduce'], 'resource': payload['id'], 'max_units': 1, 'delegation_depth': 0}, request['expires_at'])
        self.put('grants', grant_id, {'token': grant, 'intention': invitation['intention'],
            'revision': invitation['revision'], 'peer': outer['sender'], 'limit': 1, 'revoked': False,
            'invitation_id': payload['id']})
        invitation['used'] = request['id']
        self.put('invitations', payload['id'], invitation)
        self.put('threads', request['id'], {'direction': 'incoming', 'peer': outer['sender'], 'request': content['request'],
            'intention': invitation['intention'], 'revision': invitation['revision'], 'grant_id': grant_id,
            'expires': request['expires_at'], 'status': 'proposed', 'discovery': 'shared-index-invitation'})
        self._queue(outer['sender'], {'kind': 'proposal', 'request_id': request['id'],
                    'request_digest': digest(content['request']), 'outcome': 'proposed'}, request['expires_at'])
        self.put('inbox', outer['id'], {'request_id': request['id'], 'kind': 'proposal', 'outcome': 'proposed',
            'discovery': 'shared-index-invitation', 'expires': request['expires_at'], 'acknowledged': False})
