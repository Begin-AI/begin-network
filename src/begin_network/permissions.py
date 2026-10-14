"""Experimental delegation and durable unit accounting for a single resource owner.

Each owner selects its own root authority. This is not global money settlement.
All grant/request/revocation inputs are signed tokens and verified here.
"""
import hashlib
import sqlite3
from .envelope import Rejected, verify, validate_task_body

GRANT_PROFILE = 'begin-delegation-v1'


def _scope(grant):
    body = grant['body']
    fields = {'profile', 'subject', 'purpose', 'actions', 'resource', 'max_units', 'depth', 'parent'}
    if grant['type'] != 'grant' or set(body) != fields or body['profile'] != GRANT_PROFILE:
        raise Rejected('invalid delegation grant profile')
    for key in ('subject', 'purpose', 'resource'):
        if not isinstance(body[key], str) or not body[key]:
            raise Rejected('invalid scope text')
    if not isinstance(body['actions'], list) or not body['actions'] or any(not isinstance(a, str) or not a for a in body['actions']) or len(body['actions']) != len(set(body['actions'])):
        raise Rejected('invalid allowed actions')
    if type(body['depth']) is not int or not 0 <= body['depth'] <= 8 or type(body['max_units']) is not int or not 0 <= body['max_units'] <= 1000000000:
        raise Rejected('invalid grant budget/depth')
    if body['parent'] is not None and (not isinstance(body['parent'], str) or not body['parent']):
        raise Rejected('invalid parent reference')
    return body


class PermissionLedger:
    """Atomic acceptance/reservation; accepted work is never auto-refunded.

    One ledger MUST govern each root budget, across all delegations. Replicas
    cannot independently spend the same budget. Reservations authorize admission,
    not arbitrary code execution or compensation.
    """
    def __init__(self, path, *, audience, authority, trusted_keys, freshness=60):
        if type(freshness) is not int or freshness <= 0:
            raise Rejected('invalid revocation freshness')
        self.audience, self.authority = audience, authority
        self.keys, self.freshness = dict(trusted_keys), freshness
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), audience TEXT NOT NULL, authority TEXT NOT NULL, freshness INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS grants (
            id TEXT PRIMARY KEY, digest TEXT NOT NULL, ceiling INTEGER NOT NULL, spent INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS revoked (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS freshness (singleton INTEGER PRIMARY KEY CHECK(singleton=1), issued INTEGER NOT NULL, expiry INTEGER NOT NULL, digest TEXT NOT NULL);''')

        self.db.execute('BEGIN IMMEDIATE')
        try:
            policy = self.db.execute('SELECT audience,authority,freshness FROM policy WHERE singleton=1').fetchone()
            expected = (audience, authority, freshness)
            if policy is None and any(self.db.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone() for table in ('grants', 'operations', 'revoked', 'freshness')):
                raise Rejected('unbound populated ledger requires explicit migration')
            if policy and policy != expected:
                raise Rejected('ledger policy mismatch; explicit migration required')
            self.db.execute('INSERT OR IGNORE INTO policy VALUES (1,?,?,?)', expected)
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def apply_revocations(self, token, now):
        payload = verify(token, self.keys, self.audience, now=now)
        body = payload['body']
        if payload['type'] != 'revocation' or payload['sender'] != self.authority or set(body) != {'profile', 'revoked'} or body['profile'] != GRANT_PROFILE or not isinstance(body['revoked'], list) or any(not isinstance(i, str) or not i for i in body['revoked']):
            raise Rejected('invalid authority revocation snapshot')
        digest = hashlib.sha256(token.encode()).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            previous = self.db.execute('SELECT issued,digest FROM freshness WHERE singleton=1').fetchone()
            if previous and (payload['issued_at'] < previous[0] or (payload['issued_at'] == previous[0] and digest != previous[1])):
                raise Rejected('revocation snapshot rollback/conflict')
            for grant_id in body['revoked']:
                self.db.execute('INSERT OR IGNORE INTO revoked VALUES (?)', (grant_id,))
            self.db.execute('INSERT OR REPLACE INTO freshness VALUES (1,?,?,?)', (payload['issued_at'], payload['expires_at'], digest))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def reserve(self, request_token, grant_tokens, now):
        """Verify and atomically reserve across all ancestor budgets.

        Returns 'accepted' or 'duplicate'. Caller MUST NOT execute a duplicate.
        Scope/revocation/freshness are checked even on retry.
        """
        if not isinstance(grant_tokens, list) or not 1 <= len(grant_tokens) <= 9:
            raise Rejected('invalid grant chain length')
        request = verify(request_token, self.keys, self.audience, now=now)
        if request['type'] != 'request':
            raise Rejected('expected task request')
        task = validate_task_body(request['body'])
        chain = []
        ids = set()
        for token in grant_tokens:
            grant = verify(token, self.keys, self.audience, now=now)
            scope = _scope(grant)
            if grant['id'] in ids:
                raise Rejected('repeated grant in chain')
            ids.add(grant['id'])
            if not chain:
                if grant['sender'] != self.authority or scope['parent'] is not None or grant['proofs']:
                    raise Rejected('untrusted root grant')
            else:
                parent, parent_scope, _ = chain[-1]
                if grant['sender'] != parent_scope['subject'] or scope['parent'] != parent['id'] or grant['proofs'] != [parent['id']]:
                    raise Rejected('broken delegation chain')
                if scope['purpose'] != parent_scope['purpose'] or scope['resource'] != parent_scope['resource'] or not set(scope['actions']) <= set(parent_scope['actions']) or not scope['depth'] < parent_scope['depth'] or scope['max_units'] > parent_scope['max_units'] or grant['issued_at'] < parent['issued_at'] or grant['expires_at'] > parent['expires_at']:
                    raise Rejected('delegation expands authority')
            chain.append((grant, scope, hashlib.sha256(token.encode()).hexdigest()))
        leaf, leaf_scope, _ = chain[-1]
        if request['sender'] != leaf_scope['subject'] or request['proofs'] != [leaf['id']] or task['purpose'] != leaf_scope['purpose'] or task['resource'] != leaf_scope['resource'] or task['action'] not in leaf_scope['actions']:
            raise Rejected('request outside delegated scope')
        if request['issued_at'] < leaf['issued_at'] or request['expires_at'] > leaf['expires_at']:
            raise Rejected('request outlives delegation')
        digest = hashlib.sha256(request_token.encode()).hexdigest()
        operation_id = request['sender'] + ':' + request['id']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            fresh = self.db.execute('SELECT issued,expiry FROM freshness WHERE singleton=1').fetchone()
            if not fresh or not fresh[0] <= now < min(fresh[1], fresh[0] + self.freshness):
                raise Rejected('revocation snapshot stale or missing')
            for grant, scope, grant_digest in chain:
                if self.db.execute('SELECT 1 FROM revoked WHERE id=?', (grant['id'],)).fetchone():
                    raise Rejected('grant or ancestor revoked')
                row = self.db.execute('SELECT digest,ceiling FROM grants WHERE id=?', (grant['id'],)).fetchone()
                if row and row != (grant_digest, scope['max_units']):
                    raise Rejected('conflicting grant identifier')
                self.db.execute('INSERT OR IGNORE INTO grants(id,digest,ceiling) VALUES (?,?,?)', (grant['id'], grant_digest, scope['max_units']))
            existing = self.db.execute('SELECT digest FROM operations WHERE id=?', (operation_id,)).fetchone()
            if existing:
                if existing[0] != digest:
                    raise Rejected('conflicting operation identifier')
                result = 'duplicate'
            else:
                for grant, scope, _ in chain:
                    changed = self.db.execute('UPDATE grants SET spent=spent+? WHERE id=? AND spent+?<=ceiling', (task['units'], grant['id'], task['units'])).rowcount
                    if changed != 1:
                        raise Rejected('cumulative resource budget exhausted')
                self.db.execute('INSERT INTO operations VALUES (?,?)', (operation_id, digest))
                result = 'accepted'
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise
