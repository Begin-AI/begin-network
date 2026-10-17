"""Synthetic-only secret-shared candidate index, optional MPyC dependency.

One node holds one Shamir share, never a complete representation or opening key.
Three nodes jointly scan purpose-bound records. This is a bounded linear scan,
not an anonymous or malicious-secure global nearest-neighbour index.
"""
import hashlib
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .envelope import VERSION, decode, encode, generate_key, key_id, sign, strict_json, verify
from .introductions import invitation_payload
from .local_discovery import validate_query
from .runtime_bridge import canonical, require
from .sealed import encryption_key, seal, sealed_digest, _decrypt_bound

PROFILE = 'begin-shared-index-v2'
PARAMETERS = {'mpyc': '0.11', 'integer_bits': 48, 'security_parameter': 30,
              'parties': 3, 'passive_corruption_threshold': 1, 'scale': 1000,
              'max_records': 8, 'max_queries_per_key': 3, 'transport': 'mutual-tls',
              'output': 'three-additive-shares-encrypted-to-requester',
              'representation': 'balanced-mirror-window-social-v2'}
# The fixed slot binds the integrated v2 representation, not a selected perspective.
PURPOSE = {'integrated': 2}
ROLE = {'seek': 0, 'offer': 1, 'peer': 2}


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def contract(representation):
    validate_query(representation)
    return {'method': representation['method'], 'model': representation['model'],
            'dimensions': len(representation['values']), 'normalization': 'l2-quantized-1000'}


def field_type():
    import contextlib
    import sys
    if 'mpyc.runtime' in sys.modules and hasattr(sys.modules['mpyc.runtime'], 'mpc'):
        return sys.modules['mpyc.runtime'].mpc.SecInt(PARAMETERS['integer_bits']).field
    # MPyC startup logs must never corrupt a participant server's MCP stdout.
    # The optional runtime parses process arguments at import. Our service's
    # --config is JSON containing private keys, not an MPyC INI file. Never let
    # the dependency interpret or log the host application's arguments.
    arguments = sys.argv
    try:
        sys.argv = [arguments[0]]
        with contextlib.redirect_stdout(sys.stderr):
            from mpyc.runtime import mpc
    finally:
        sys.argv = arguments
    return mpc.SecInt(PARAMETERS['integer_bits']).field


def share(values):
    from mpyc.thresha import random_split
    return random_split(field_type(), values, 1, 3)


def private_row(representation, *, minimum_score=500000, active=True):
    validate_query(representation)
    require(representation['purpose'] in PURPOSE and type(active) is bool, 'unsupported purpose/consent')
    require(type(minimum_score) is int and 200000 <= minimum_score <= 1000000, 'invalid exploration threshold')
    require(0 <= representation['available_from'] < representation['available_until'] < 2**40, 'time out of range')
    return [round(v * 1000) for v in representation['values']] + [PURPOSE[representation['purpose']],
        ROLE[representation['role']], representation['available_from'], representation['available_until'],
        minimum_score, int(active)]


def seal_json(value, recipient_public, message_id, audience):
    return seal(canonical(value).encode(), decode(recipient_public), message_id, audience)


def open_json(box, private, message_id, audience):
    return strict_json(_decrypt_bound(box, decode(private), {'id': message_id, 'audience': audience,
                      'body': {'sealed_digest': sealed_digest(box)}}))


def signed(key, audience, message_id, body, now, expires, kind='request'):
    return sign({'version': VERSION, 'type': kind, 'sender': key['kid'], 'id': message_id,
        'audience': audience, 'issued_at': now, 'expires_at': expires, 'body': body, 'proofs': []}, decode(key['private']))


def enroll(card, representation, pool, nodes, *, now, minimum_score=500000):
    """Owner-side only: fresh unlinkable update key and independent random shares.

    Returned private owner state must never be copied to a discovery node.
    Uploads belong to a private transport, never the public bootstrap index.
    """
    payload = invitation_payload(card, now)
    require(payload['body']['pool'] == pool and len(nodes) == 3, 'wrong enrollment pool')
    record_id = str(uuid.uuid4())
    opening = encryption_key()
    box = seal_json(card, opening['public'], record_id, pool)
    shares = share(private_row(representation, minimum_score=minimum_score) + list(decode(opening['private'])))
    owner = {'record_id': record_id, 'update_key': generate_key(), 'revision': 1, 'pool': pool,
             'expires': payload['expires_at']}
    uploads = []
    for node, values in zip(nodes, shares):
        body = {'profile': PROFILE, 'pool': pool, 'record_id': record_id, 'revision': 1, 'operation': 'enroll',
                'contract': contract(representation), 'card_box': box, 'shares': values}
        token = signed(owner['update_key'], node['kid'], record_id + ':1', body, now, owner['expires'])
        uploads.append({'public': owner['update_key']['public'], 'token': token})
    return owner, uploads


def revocations(owner, nodes, *, now):
    owner['revision'] += 1
    return [{'public': owner['update_key']['public'], 'token': signed(owner['update_key'], node['kid'],
        owner['record_id'] + ':' + str(owner['revision']), {'profile': PROFILE, 'pool': owner['pool'],
        'record_id': owner['record_id'], 'revision': owner['revision'], 'operation': 'revoke'}, now,
        owner['expires'], kind='revocation')} for node in nodes]


class IndexNode:
    """Persistent private shard and fail-closed local admission ledger.

    The operator approves import/transport and requester keys. Self-certified
    update keys authorize only edits to their own opaque record, not other rows.
    """
    def __init__(self, directory, key, pool, *, clock=time.time):
        root = Path(directory)
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(not root.is_symlink() and root.stat().st_mode & 0o077 == 0, 'private node directory required')
        path = root / 'index.sqlite'
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        require(path.stat().st_mode & 0o077 == 0, 'private index database required')
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, public TEXT, revision INTEGER, value TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, requester TEXT, digest TEXT, result TEXT)')
        self.key, self.pool, self.clock = key, pool, clock

    def close(self):
        self.db.close()

    def apply(self, upload):
        require(isinstance(upload, dict) and set(upload) == {'public', 'token'}, 'invalid private upload')
        public = decode(upload['public'])
        envelope = verify(upload['token'], {key_id(public): public}, self.key['kid'], now=int(self.clock()))
        body = envelope['body']
        common = {'profile', 'pool', 'record_id', 'revision', 'operation'}
        require(body.get('profile') == PROFILE and body.get('pool') == self.pool and not envelope['proofs'] and
                isinstance(body.get('record_id'), str) and 1 <= len(body['record_id']) <= 128 and
                type(body.get('revision')) is int and body['revision'] >= 1, 'invalid record update')
        operation = body['operation']
        if operation == 'enroll':
            require(envelope['type'] == 'request' and set(body) == common | {'contract', 'card_box', 'shares'}, 'invalid enrollment')
            method = body['contract']
            require(isinstance(method, dict) and set(method) == {'method', 'model', 'dimensions', 'normalization'} and
                    all(isinstance(method[k], str) and 0 < len(method[k]) <= 512 for k in ('method', 'model')) and
                    type(method['dimensions']) is int and 1 <= method['dimensions'] <= 384 and
                    method['normalization'] == 'l2-quantized-1000', 'invalid method contract')
            validate_shares(body['shares'], method['dimensions'] + 6 + 32)
            require(len(canonical(body['card_box'])) <= 10000, 'card too large')
        else:
            require(operation == 'revoke' and envelope['type'] == 'revocation' and set(body) == common, 'invalid revocation')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT public,revision,value FROM records WHERE id=?', (body['record_id'],)).fetchone()
            value = canonical({'body': body, 'expires': envelope['expires_at']})
            if old:
                require(old[0] == upload['public'], 'record update signer changed')
                if old[1] == body['revision'] and old[2] == value:
                    self.db.execute('COMMIT')
                    return {'duplicate': True}
                require(body['revision'] > old[1], 'record rollback or conflicting update')
            else:
                require(operation == 'enroll' and body['revision'] == 1, 'first revision must enroll')
                require(self.db.execute('SELECT COUNT(*) FROM records').fetchone()[0] < PARAMETERS['max_records'], 'index full')
            self.db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?)',
                            (body['record_id'], upload['public'], body['revision'], value))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise
        return {'duplicate': False}

    def snapshot(self, method):
        rows = []
        for record_id, value in self.db.execute('SELECT id,value FROM records ORDER BY id').fetchall():
            row = strict_json(value)
            body = row['body']
            if row['expires'] <= int(self.clock()) and body['operation'] == 'enroll':
                tombstone = {k: body[k] for k in ('profile', 'pool', 'record_id', 'revision')}
                tombstone['operation'] = 'expired'
                self.db.execute('UPDATE records SET value=? WHERE id=?',
                    (canonical({'body': tombstone, 'expires': row['expires']}), record_id))
                continue
            if (body.get('profile') == PROFILE and body.get('pool') == self.pool and
                    row['expires'] > int(self.clock()) and body['operation'] == 'enroll' and body['contract'] == method):
                rows.append(row)
        return rows

    def reserve(self, session, requester):
        digest = fingerprint(session)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT requester,digest,result FROM sessions WHERE id=?', (session['id'],)).fetchone()
            if old:
                require(old[0] == requester and old[1] == digest, 'conflicting session retry')
                require(old[2] is not None, 'previous attempt incomplete; budget remains consumed')
                self.db.execute('COMMIT')
                return strict_json(old[2])
            count = self.db.execute('SELECT COUNT(*) FROM sessions WHERE requester=?', (requester,)).fetchone()[0]
            require(count < PARAMETERS['max_queries_per_key'], 'cumulative query budget exhausted')
            self.db.execute('INSERT INTO sessions VALUES (?,?,?,NULL)', (session['id'], requester, digest))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise
        return None

    def complete(self, session, result):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            require(int(self.clock()) < session['expires_at'], 'session expired during computation')
            require(public_snapshot(self.snapshot(session['contract'])) == session['records'], 'index changed during computation')
            updated = self.db.execute('UPDATE sessions SET result=? WHERE id=? AND digest=? AND result IS NULL',
                            (canonical(result), session['id'], fingerprint(session)))
            require(updated.rowcount == 1, 'session not reserved or already completed')
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise


def validate_shares(values, width):
    modulus = field_type().modulus
    require(isinstance(values, list) and len(values) == width and all(type(v) is int and 0 <= v < modulus for v in values),
            'invalid field share encoding')


def public_snapshot(rows):
    # Private metadata agreed by the committee, not a public bootstrap advertisement.
    return [{'id': r['body']['record_id'], 'revision': r['body']['revision'], 'expires': r['expires'],
             'card_digest': sealed_digest(r['body']['card_box'])} for r in rows]


def norm_tolerance(dim):
    return math.ceil(1000 * math.sqrt(dim) + dim / 4)


def reconstruct(session, results, pins, requester_private, boxes, *, now):
    """Only the requester combines three independently masked, signed results."""
    require(len(results) == 3 and len(pins) == 3, 'all three node responses required')
    expected = [p['kid'] for p in session['parties']]
    require(set(pins) == set(expected), 'operator pins differ from selected committee')
    width = len(session['records']) * 33
    outputs = {}
    for result in results:
        envelope = verify(result['token'], pins, session['requester']['address'], now=now, max_lifetime=300)
        require(envelope['sender'] in expected and envelope['sender'] not in outputs and envelope['type'] == 'response' and
                not envelope['proofs'] and envelope['id'] == session['id'] and envelope['expires_at'] == session['expires_at'] and
                envelope['body'] == {'profile': PROFILE, 'session_digest': fingerprint(session),
                                    'sealed_digest': sealed_digest(result['box'])}, 'wrong result session or signer')
        values = open_json(result['box'], requester_private, session['id'], session['requester']['address'])
        validate_shares(values, width)
        outputs[envelope['sender']] = values
    modulus = field_type().modulus
    opened = [sum(values[i] for values in outputs.values()) % modulus for i in range(width)]
    cards = []
    for i, record in enumerate(session['records']):
        row = opened[33*i:33*(i+1)]
        require(row[0] in (0, 1), 'invalid matching output')
        if row[0] == 0:
            require(row[1:] == [0]*32, 'non-match released key material')
            continue
        require(all(0 <= v <= 255 for v in row[1:]), 'invalid opening key')
        box = boxes[record['id']]
        require(sealed_digest(box) == record['card_digest'], 'introduction ciphertext changed')
        card = open_json(box, encode(bytes(row[1:])), record['id'], session['pool'])
        invitation = invitation_payload(card, now)
        require(invitation['body']['pool'] == session['pool'], 'wrong invitation pool')
        cards.append(card)
    return cards
