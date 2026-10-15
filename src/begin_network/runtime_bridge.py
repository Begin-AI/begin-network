"""Participant-side bridge into the original Begin runtime; synthetic data only.

Participant state belongs on a chosen trusted runner, never on a blind relay.
The owner-local matcher reveals authorized query vectors to the counterpart.
This is not complete P2, global candidate search or a production key service.
"""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .coordination import Mailbox
from .discovery_index import load_mirrors
from .envelope import VERSION, Rejected, decode, generate_key, key_id, sign, strict_json, verify
from .intentions import Intention, Store
from .introductions import Introductions
from .local_discovery import receive_query
from .sealed import encryption_key, seal, sealed_digest, _decrypt_bound, open_authorized

PACKET = 'begin-participant-packet-v1'
OWNER_LOCAL = {'id': 'begin/owner-local-v1', 'method_version': '1',
               'model': 'per-session-pinned-model', 'dimensions': 'dynamic', 'normalization': 'l2'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require(condition, reason):
    if not condition:
        raise Rejected(reason)


class TransactionReplay:
    """Reuse original replay admission inside the participant's atomic commit."""
    def __init__(self, db):
        self.db = db

    def admit(self, sender, request_id):
        try:
            self.db.execute('INSERT INTO replay VALUES (?,?)', (sender, request_id))
        except sqlite3.IntegrityError as exc:
            raise Rejected('replayed request') from exc


class Participant(Introductions):
    def __init__(self, directory, *, encoder, clock=time.time):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(not self.directory.is_symlink(), 'participant directory must not be a symlink')
        require(self.directory.stat().st_mode & 0o077 == 0, 'participant directory must be private (0700)')
        self.clock, self.encoder = clock, encoder
        path = self.directory / 'participant.sqlite'
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        require(path.stat().st_mode & 0o077 == 0, 'participant state must be private (0600)')
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (namespace TEXT, key TEXT, value TEXT NOT NULL, PRIMARY KEY(namespace,key))')
        self.db.execute('CREATE TABLE IF NOT EXISTS replay (sender TEXT, id TEXT, PRIMARY KEY(sender,id))')
        with self.transaction():
            identity = self.get('private', 'identity')
            if identity is None:
                identity = {'signing': generate_key(), 'encryption': encryption_key()}
                self.put('private', 'identity', identity)
        self.signing, self.encryption = identity['signing'], identity['encryption']
        self.id = self.signing['kid']

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def now(self):
        return int(self.clock())

    def get(self, namespace, key):
        row = self.db.execute('SELECT value FROM records WHERE namespace=? AND key=?', (namespace, key)).fetchone()
        return strict_json(row[0]) if row else None

    def put(self, namespace, key, value):
        self.db.execute('INSERT INTO records VALUES (?,?,?) ON CONFLICT(namespace,key) DO UPDATE SET value=excluded.value',
                        (namespace, key, canonical(value)))

    def records(self, namespace):
        return {key: strict_json(value) for key, value in self.db.execute('SELECT key,value FROM records WHERE namespace=? ORDER BY key', (namespace,))}

    def identity(self):
        return {'address': self.id, 'signing_public': self.signing['public'],
                'encryption_public': self.encryption['public'], 'custody': 'participant-selected runner',
                'data_policy': 'synthetic-only', 'processing': 'runner can read its participant data',
                'private_discovery': 'owner-local; counterpart learns authorized query; metadata visible'}

    def pin_peer(self, identity):
        """Operator configuration, deliberately not a client tool or index side effect."""
        require(key_id(decode(identity['signing_public'])) == identity['address'], 'peer signing key mismatch')
        require(len(decode(identity['encryption_public'])) == 32, 'invalid peer encryption key')
        old = self.get('peers', identity['address'])
        peer = {k: identity[k] for k in ('address', 'signing_public', 'encryption_public')}
        require(old is None or old == peer, 'key replacement requires explicit migration')
        self.put('peers', identity['address'], peer)

    def keys(self):
        return dict({p['address']: decode(p['signing_public']) for p in self.records('peers').values()},
                    **{self.id: decode(self.signing['public'])})

    def peer(self, address):
        peer = self.get('peers', address)
        require(peer is not None and address != self.id, 'peer not independently pinned')
        return peer

    def signed(self, kind, message_id, audience, body, expires, proofs=None):
        require(self.now() < expires <= self.now() + 3600, 'expiry must be within one hour')
        return sign({'version': VERSION, 'type': kind, 'sender': self.id, 'id': message_id,
                     'audience': audience, 'issued_at': self.now(), 'expires_at': expires,
                     'body': body, 'proofs': proofs or []}, decode(self.signing['private']))

    def _store(self):
        store = Store()
        for key, value in self.records('intentions').items():
            store._intentions[key] = Intention(**value)
        return store

    def set_intention(self, intention_id, *, purpose, facts, aspirations, inferences, role,
                      available_from, available_until, expires_at, consent, disclosure,
                      expected_revision=None):
        require(isinstance(intention_id, str) and 1 <= len(intention_id) <= 128, 'invalid intention ID')
        require(len(canonical([facts, aspirations, inferences])) <= 8192, 'intention too large')
        with self.transaction():
            store = self._store()
            options = dict(facts=facts, aspirations=aspirations, inferences=inferences, role=role,
                           available_from=available_from, available_until=available_until,
                           expires_at=expires_at, consent=consent, disclosure=disclosure)
            if self.get('intentions', intention_id) is None:
                require(expected_revision is None, 'unknown intention revision')
                require(len(store._intentions) < 32, 'intention limit reached')
                item = store.create(intention_id, purpose, **options)
            else:
                require(store.get(intention_id).purpose == purpose, 'purpose is immutable; create another intention')
                item = store.edit(intention_id, expected_revision, **options)
            self.put('intentions', intention_id, asdict(item))
            return asdict(item)

    def retire_intention(self, intention_id, expected_revision):
        with self.transaction():
            store = self._store()
            item = store.retire(intention_id, expected_revision)
            self.put('intentions', intention_id, asdict(item))
            return asdict(item)

    def representation(self, intention_id, revision=None):
        store = self._store()
        item = store.get(intention_id)
        store._active(item, self.now())
        require(revision is None or item.revision == revision, 'intention edited since authorization')
        # The encoder is pinned operator code; a tool cannot download or choose code.
        vector = store.vector(intention_id, self.encoder.encode(item), self.encoder.method, self.encoder.model)
        return item, {'method': vector.method, 'model': vector.model, 'purpose': vector.purpose,
                      'role': item.role, 'available_from': item.available_from,
                      'available_until': item.available_until, 'values': list(vector.values)}

    def allow_matching(self, peer, intention_id, *, max_queries=1, ttl=600):
        """Explicit owner opt-in; total per-intention peer budget persists across grants."""
        self.peer(peer)
        require(type(max_queries) is int and 1 <= max_queries <= 3, 'synthetic query budget must be 1..3')
        require(type(ttl) is int and 1 <= ttl <= 3600, 'invalid grant lifespan')
        with self.transaction():
            item, _ = self.representation(intention_id)
            expires = min(self.now() + ttl, item.expires_at)
            grant_id = str(uuid.uuid4())
            token = self.signed('grant', grant_id, self.id,
                {'subject': peer, 'purpose': 'begin-discovery', 'actions': ['match'],
                 'resource': intention_id, 'max_units': 1, 'delegation_depth': 0}, expires)
            self.put('grants', grant_id, {'token': token, 'intention': intention_id, 'revision': item.revision,
                                         'peer': peer, 'limit': max_queries, 'revoked': False})
            return {'grant': token, 'scope': 'query representation only; no request disclosure', 'expires_at': expires}

    def revoke_matching(self, grant_id):
        with self.transaction():
            grant = self.get('grants', grant_id)
            require(grant is not None, 'unknown grant')
            grant['revoked'] = True
            self.put('grants', grant_id, grant)
        return {'revoked': grant_id}

    def select_service(self, sources, pins, audience, *, service_id):
        """Sources, pins and service ID come from operator config, never tool text."""
        checked = load_mirrors(sources, pins, audience, now=self.now(),
                               requested_contracts=[OWNER_LOCAL], capabilities=['mailbox'])
        node = next((n for n in checked['nodes'] if n['id'] == service_id), None)
        require(node is not None, 'configured mailbox not advertised by selected index')
        self.put('bootstrap', 'selected', {'service': node, 'digest': checked['index_sha256'],
                 'expires': min(checked['attestation_expires_at'], self.now() + 300,
                                int(datetime.fromisoformat(node['expires_at'].replace('Z', '+00:00')).timestamp())),
                 'attested_by': checked['attested_by'], 'rejected_mirrors': checked['rejected_mirrors']})
        return checked

    def _selected(self):
        selected = self.get('bootstrap', 'selected')
        require(selected is not None and self.now() < selected['expires'], 'refresh verified discovery index')
        return selected['service']

    def _queue(self, recipient, content, expires):
        self._selected()
        peer = self.peer(recipient)
        message_id = str(uuid.uuid4())
        box = seal(canonical(content).encode(), decode(peer['encryption_public']), message_id, recipient)
        token = self.signed('response', message_id, recipient,
                            {'profile': PACKET, 'sealed_digest': sealed_digest(box)}, expires)
        packet = {'token': token, 'box': box}
        self.put('outbox', message_id, packet)
        return message_id

    def discover(self, intention_id, peer, grant_token, description, *, idempotency_key):
        require(isinstance(description, str) and 0 < len(description) <= 4096, 'invalid synthetic description')
        require(isinstance(idempotency_key, str) and 1 <= len(idempotency_key) <= 128, 'invalid retry key')
        self.peer(peer)
        fingerprint = digest(canonical([intention_id, peer, grant_token, description]))
        with self.transaction():
            cached = self.get('submissions', idempotency_key)
            if cached:
                require(cached['digest'] == fingerprint, 'conflicting retry')
                return {'request_id': cached['request'], 'duplicate': True}
            item, query = self.representation(intention_id)
            grant = verify(grant_token, self.keys(), peer, now=self.now())
            require(grant['sender'] == peer and grant['body'].get('subject') == self.id, 'grant must come from counterpart')
            request_id = str(uuid.uuid4())
            expires = min(grant['expires_at'], item.expires_at)
            box = seal(canonical(query).encode(), decode(self.peer(peer)['encryption_public']), request_id, peer)
            token = self.signed('request', request_id, peer,
                {'purpose': 'begin-discovery', 'action': 'match', 'resource': grant['body']['resource'],
                 'units': 1, 'sealed_digest': sealed_digest(box)}, expires, [grant['id']])
            from .envelope import authorize
            authorize(verify(token, self.keys(), peer, now=self.now()), grant, peer, self.now())
            self.put('threads', request_id, {'direction': 'outgoing', 'peer': peer, 'intention': intention_id,
                     'revision': item.revision, 'expires': expires, 'request': token, 'status': 'discovering',
                     'description': description, 'grant_id': grant['id']})
            self._queue(peer, {'kind': 'query', 'request': token, 'grant': grant_token, 'box': box}, expires)
            self.put('submissions', idempotency_key, {'digest': fingerprint, 'request': request_id})
            return {'request_id': request_id, 'duplicate': False, 'full_request_disclosed': False}

    def _thread(self, request_id, direction=None):
        thread = self.get('threads', request_id)
        require(thread is not None and self.now() < thread['expires'], 'unknown or expired thread')
        require(direction is None or thread['direction'] == direction, 'wrong thread direction')
        self.representation(thread['intention'], thread['revision'])
        return thread

    def _live_grant(self, grant_id):
        grant = self.get('grants', grant_id)
        require(grant is not None and not grant['revoked'], 'matching grant revoked or unknown')
        verify(grant['token'], self.keys(), self.id, now=self.now())
        self.representation(grant['intention'], grant['revision'])
        if 'invitation_id' in grant:
            self._live_invitation(grant['invitation_id'])
        return grant

    def accept(self, request_id):
        """Counterpart explicitly permits receiving the scoped description after fit."""
        with self.transaction():
            thread = self._thread(request_id, 'incoming')
            self._live_grant(thread['grant_id'])
            if thread['status'] == 'accepted':
                return {'request_id': request_id, 'status': 'accepted', 'duplicate': True}
            require(thread['status'] == 'proposed', 'positive, unaccepted match required')
            grant_id = str(uuid.uuid4())
            token = self.signed('grant', grant_id, self.id,
                {'subject': thread['peer'], 'purpose': 'begin-discovery', 'actions': ['disclose'],
                 'resource': request_id, 'max_units': 1, 'delegation_depth': 0}, thread['expires'])
            thread.update(status='accepted', disclosure_grant=token)
            self.put('threads', request_id, thread)
            self._queue(thread['peer'], {'kind': 'accepted', 'request_id': request_id,
                        'request_digest': digest(thread['request']), 'grant': token}, thread['expires'])
        return {'request_id': request_id, 'status': 'accepted'}

    def disclose(self, request_id):
        """Requester separately approves releasing the stored description."""
        with self.transaction():
            thread = self._thread(request_id, 'outgoing')
            if thread['status'] == 'disclosed':
                return {'request_id': request_id, 'status': 'disclosed', 'duplicate': True}
            require(thread['status'] == 'accepted', 'counterpart acceptance required before disclosure')
            grant = verify(thread['disclosure_grant'], self.keys(), thread['peer'], now=self.now())
            require(grant['sender'] == thread['peer'], 'unexpected disclosure authority')
            message_id = str(uuid.uuid4())
            box = seal(thread['description'].encode(), decode(self.peer(thread['peer'])['encryption_public']), message_id, thread['peer'])
            token = self.signed('request', message_id, thread['peer'],
                {'purpose': 'begin-discovery', 'action': 'disclose', 'resource': request_id,
                 'units': 1, 'sealed_digest': sealed_digest(box)}, thread['expires'], [grant['id']])
            self._queue(thread['peer'], {'kind': 'description', 'request_id': request_id,
                        'request': token, 'grant': thread['disclosure_grant'], 'box': box}, thread['expires'])
            thread.update(status='disclosed')
            self.put('threads', request_id, thread)
        return {'request_id': request_id, 'status': 'disclosed'}

    def reply(self, request_id, text, *, idempotency_key):
        require(isinstance(text, str) and 0 < len(text) <= 4096, 'invalid response')
        require(isinstance(idempotency_key, str) and 1 <= len(idempotency_key) <= 128, 'invalid retry key')
        fingerprint = digest(canonical([request_id, text]))
        with self.transaction():
            cached = self.get('replies', idempotency_key)
            if cached:
                require(cached['digest'] == fingerprint, 'conflicting reply retry')
                return {'message_id': cached['id'], 'duplicate': True}
            thread = self._thread(request_id)
            require(thread['status'] == 'disclosed', 'description must be authorized and disclosed first')
            if thread['direction'] == 'incoming':
                self._live_grant(thread['grant_id'])
            message_id = self._queue(thread['peer'], {'kind': 'reply', 'request_id': request_id,
                                     'request_digest': digest(thread['request']), 'text': text}, thread['expires'])
            self.put('replies', idempotency_key, {'digest': fingerprint, 'id': message_id})
            return {'message_id': message_id, 'duplicate': False}

    def decline(self, request_id):
        """Stop a thread and notify the peer; previously learned content stays learned."""
        with self.transaction():
            thread = self._thread(request_id)
            if thread['status'] == 'declined':
                return {'request_id': request_id, 'status': 'declined', 'duplicate': True}
            require(thread['status'] != 'no-match', 'thread already ended without a match')
            self._queue(thread['peer'], {'kind': 'declined', 'request_id': request_id,
                        'request_digest': digest(thread['request'])}, thread['expires'])
            thread.pop('description', None)
            thread.pop('disclosure_grant', None)
            thread['status'] = 'declined'
            self.put('threads', request_id, thread)
        return {'request_id': request_id, 'status': 'declined'}

    def receive(self, packet):
        require(isinstance(packet, dict) and set(packet) in ({'token', 'box'}, {'token', 'box', 'signing_public'}), 'invalid packet')
        require(len(canonical(packet)) <= 65536, 'packet too large')
        keys = self.keys()
        introduction_key = decode(packet['signing_public']) if 'signing_public' in packet else None
        if introduction_key is not None:
            require(len(introduction_key) == 32, 'invalid introduction signer')
            keys[key_id(introduction_key)] = introduction_key
        outer = verify(packet['token'], keys, self.id, now=self.now())
        require(outer['type'] == 'response' and not outer['proofs'] and
                outer['body'] == {'profile': PACKET, 'sealed_digest': sealed_digest(packet['box'])}, 'invalid packet profile')
        if introduction_key is None:
            self.peer(outer['sender'])
        else:
            require(key_id(introduction_key) == outer['sender'], 'introduction key not bound to sender')
        fingerprint = digest(canonical(packet))
        with self.transaction():
            seen = self.get('received', outer['sender'] + ':' + outer['id'])
            if seen:
                require(seen == fingerprint, 'conflicting delivery')
                return {'duplicate': True}
            content = strict_json(_decrypt_bound(packet['box'], decode(self.encryption['private']), outer))
            if introduction_key is not None:
                require(isinstance(content, dict) and content.get('kind') == 'introduction', 'new key only permits introduction')
                self._receive_introduction(outer, content, introduction_key)
            else:
                self._handle(outer, content)
            self.put('received', outer['sender'] + ':' + outer['id'], fingerprint)
        return {'duplicate': False}

    def _handle(self, outer, content):
        require(isinstance(content, dict), 'invalid participant content')
        kind = content.get('kind')
        if kind == 'query':
            require(set(content) == {'kind', 'request', 'grant', 'box'}, 'invalid query packet')
            request = verify(content['request'], self.keys(), self.id, now=self.now())
            grant = verify(content['grant'], self.keys(), self.id, now=self.now())
            require(request['sender'] == outer['sender'] and request['expires_at'] == outer['expires_at'], 'query sender/expiry mismatch')
            permission = self._live_grant(grant['id'])
            require(permission['token'] == content['grant'], 'grant substitution')
            budget_key = permission['peer'] + ':' + permission['intention']
            spent = self.get('query_budgets', budget_key) or 0
            require(spent < permission['limit'], 'cumulative matching budget exhausted')
            _, owner = self.representation(permission['intention'], permission['revision'])
            result = receive_query(content['request'], content['grant'], content['box'], keys=self.keys(),
                audience=self.id, authority=self.id, recipient_private=decode(self.encryption['private']),
                owner=owner, replay=TransactionReplay(self.db), now=self.now())
            self.put('query_budgets', budget_key, spent + 1)
            thread = {'direction': 'incoming', 'peer': request['sender'], 'request': content['request'],
                      'intention': permission['intention'], 'revision': permission['revision'],
                      'grant_id': grant['id'], 'expires': request['expires_at'], 'status': result['outcome']}
            require(self.get('threads', request['id']) is None, 'thread collision')
            self.put('threads', request['id'], thread)
            self._queue(request['sender'], {'kind': 'proposal', 'request_id': request['id'],
                        'request_digest': digest(content['request']), 'outcome': result['outcome']}, request['expires_at'])
            self.put('inbox', outer['id'], {'request_id': request['id'], 'kind': 'proposal',
                      'outcome': result['outcome'], 'expires': request['expires_at'], 'acknowledged': False})
            return
        require(kind in ('proposal', 'accepted', 'description', 'reply', 'declined'), 'unsupported packet content')
        request_id = content.get('request_id')
        thread = self._thread(request_id)
        require(thread['peer'] == outer['sender'] and thread['expires'] == outer['expires_at'], 'thread sender/expiry mismatch')
        if thread['direction'] == 'incoming':
            self._live_grant(thread['grant_id'])
        if kind != 'description':
            require(content.get('request_digest') == digest(thread['request']), 'original request binding mismatch')
        if kind == 'declined':
            require(set(content) == {'kind', 'request_id', 'request_digest'}, 'invalid decline')
            thread.pop('description', None)
            thread.pop('disclosure_grant', None)
            thread['status'] = 'declined'
        elif kind == 'proposal':
            require(set(content) == {'kind', 'request_id', 'request_digest', 'outcome'}, 'invalid proposal')
            require(thread['direction'] == 'outgoing' and thread['status'] == 'discovering' and
                    content['outcome'] in ('proposed', 'no-match'), 'unexpected proposal')
            thread['status'] = content['outcome']
        elif kind == 'accepted':
            require(set(content) == {'kind', 'request_id', 'request_digest', 'grant'}, 'invalid acceptance')
            require(thread['direction'] == 'outgoing' and thread['status'] == 'proposed', 'proposal required')
            grant = verify(content['grant'], self.keys(), outer['sender'], now=self.now())
            require(grant['type'] == 'grant' and grant['sender'] == outer['sender'] and grant['expires_at'] == thread['expires'] and
                    grant['body'] == {'subject': self.id, 'purpose': 'begin-discovery', 'actions': ['disclose'],
                    'resource': request_id, 'max_units': 1, 'delegation_depth': 0}, 'invalid disclosure grant')
            thread.update(status='accepted', disclosure_grant=content['grant'])
        elif kind == 'description':
            require(set(content) == {'kind', 'request_id', 'request', 'grant', 'box'}, 'invalid disclosure')
            require(thread['direction'] == 'incoming' and thread['status'] == 'accepted' and
                    content['grant'] == thread['disclosure_grant'], 'disclosure not accepted')
            request = verify(content['request'], self.keys(), self.id, now=self.now())
            grant = verify(content['grant'], self.keys(), self.id, now=self.now())
            require(request['sender'] == outer['sender'] and request['body'].get('resource') == request_id and
                    request['body'].get('action') == 'disclose', 'wrong disclosure scope')
            text = open_authorized(content['box'], decode(self.encryption['private']), request, grant,
                                   self.id, self.now(), matched=True).decode('utf-8')
            require(0 < len(text) <= 4096, 'invalid description')
            content = {'kind': 'description', 'request_id': request_id, 'text': text}
            thread.update(status='disclosed')
        else:
            require(set(content) == {'kind', 'request_id', 'request_digest', 'text'} and
                    isinstance(content['text'], str) and 0 < len(content['text']) <= 4096 and
                    thread['status'] == 'disclosed', 'reply outside authorized thread')
        self.put('threads', request_id, thread)
        visible = {k: v for k, v in content.items() if k not in ('grant', 'request_digest')}
        self.put('inbox', outer['id'], dict(visible, expires=thread['expires'], acknowledged=False))

    def inbox(self):
        self.expire()
        return [dict(message_id=key, **value) for key, value in self.records('inbox').items()
                if value['expires'] > self.now() and not value['acknowledged']]

    def expire(self):
        """Remove expired payloads while keeping deduplication history, on access.

        This is logical deletion, not a promise to erase backups or endpoint knowledge.
        """
        with self.transaction():
            for key, thread in self.records('threads').items():
                if thread['expires'] <= self.now() and thread['status'] != 'expired':
                    self.put('threads', key, {'expires': thread['expires'], 'status': 'expired'})
            for key, item in self.records('inbox').items():
                if item['expires'] <= self.now():
                    self.put('inbox', key, {'expires': item['expires'], 'acknowledged': True})
            for key, packet in self.records('outbox').items():
                header = strict_json(decode(packet['token'].split('.')[1]))
                if header['expires_at'] <= self.now():
                    self.db.execute("DELETE FROM records WHERE namespace='outbox' AND key=?", (key,))

    def acknowledge(self, message_id):
        with self.transaction():
            item = self.get('inbox', message_id)
            require(item is not None, 'unknown inbox message')
            self.put('inbox', message_id, {'expires': item['expires'], 'acknowledged': True})
        return {'acknowledged': message_id}

    def flush(self, relay):
        self.expire()
        selected = self._selected()
        require(relay.id == selected['id'], 'transport not selected by verified index')
        delivered = []
        for key, packet in self.records('outbox').items():
            relay.submit(packet)
            self.db.execute("DELETE FROM records WHERE namespace='outbox' AND key=?", (key,))
            delivered.append(key)
        return delivered

    def poll(self, relay):
        selected = self._selected()
        require(relay.id == selected['id'], 'transport not selected by verified index')
        authorization = self.signed('request', str(uuid.uuid4()), relay.id,
                                    {'operation': 'retrieve'}, self.now() + 60)
        received, pending = [], list(relay.retrieve(authorization))
        # Mailbox order is not protocol order. Process eligible messages, then
        # retry deferred ones after prerequisites committed; bound passes by size.
        while pending:
            deferred = []
            for delivery in pending:
                try:
                    self.receive(strict_json(delivery.ciphertext))
                except (Rejected, ValueError, KeyError, TypeError):
                    deferred.append(delivery)
                    continue
                ack = self.signed('request', str(uuid.uuid4()), relay.id,
                    {'operation': 'acknowledge', 'message_id': delivery.operation_id}, self.now() + 60)
                relay.acknowledge(ack)
                received.append(delivery.operation_id)
            if len(deferred) == len(pending):
                break
            pending = deferred
        self.last_delivery_errors = [d.operation_id for d in pending]
        return received


class BlindRelay:
    """Existing durable Mailbox plus independently verified participant signatures.

    No participant decryption keys or plaintext intentions. Transport binding and
    TLS belong to the operator-facing adapter; this class does not open sockets.
    """
    def __init__(self, path, service_id, keys, *, clock=time.time):
        self.id, self.keys, self.clock = service_id, dict(keys), clock
        self.mailbox = Mailbox(path, clock=clock)
        self.mailbox.db.execute('CREATE TABLE IF NOT EXISTS replay (sender TEXT, id TEXT, PRIMARY KEY(sender,id))')

    def close(self):
        self.mailbox.close()

    def submit(self, packet):
        require(isinstance(packet, dict) and set(packet) in ({'token', 'box'}, {'token', 'box', 'signing_public'}), 'invalid packet')
        require(len(canonical(packet)) <= 65536, 'packet too large')
        # The unsigned audience is used only to select a pinned destination.
        require(isinstance(packet['token'], str) and len(packet['token'].split('.')) == 3, 'invalid signed packet')
        raw = strict_json(decode(packet['token'].split('.')[1]))
        require(isinstance(raw, dict), 'invalid envelope')
        audience = raw.get('audience')
        require(audience in self.keys, 'unknown mailbox recipient')
        envelope = verify(packet['token'], self.keys, audience, now=int(self.clock()))
        if 'signing_public' in packet:
            require(decode(packet['signing_public']) == self.keys[envelope['sender']], 'relay signer substitution')
        require(envelope['type'] == 'response' and not envelope['proofs'] and
                envelope['body'] == {'profile': PACKET, 'sealed_digest': sealed_digest(packet['box'])}, 'invalid relay packet')
        return self.mailbox.submit(digest(packet['token']), audience, canonical(packet).encode(), envelope['expires_at'])

    def retrieve(self, token):
        auth = verify(token, self.keys, self.id, now=int(self.clock()), replay=TransactionReplay(self.mailbox.db))
        require(auth['type'] == 'request' and not auth['proofs'] and auth['body'] == {'operation': 'retrieve'}, 'invalid mailbox authorization')
        return self.mailbox.retrieve(auth['sender'])

    def acknowledge(self, token):
        auth = verify(token, self.keys, self.id, now=int(self.clock()), replay=TransactionReplay(self.mailbox.db))
        require(auth['type'] == 'request' and not auth['proofs'] and set(auth['body']) == {'operation', 'message_id'} and
                auth['body']['operation'] == 'acknowledge', 'invalid acknowledgement')
        self.mailbox.claim(auth['sender'], auth['body']['message_id'])
        return self.mailbox.acknowledge(auth['sender'], auth['body']['message_id'])
