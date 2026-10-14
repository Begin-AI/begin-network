"""Restricted JWS Ed25519 profile. Verification is local and fail-closed."""
import base64
import binascii
import hashlib
import json
import math
import sqlite3
import time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PROFILE = 'begin+jws-v1'
VERSION = '0.1-draft'
MAX_MESSAGE_BYTES = 65536

class Rejected(ValueError):
    pass


def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def decode(value):
    if not isinstance(value, str) or not value or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in value):
        raise Rejected('invalid base64url')
    try:
        raw = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    except (ValueError, binascii.Error) as exc:
        raise Rejected('invalid base64url') from exc
    if encode(raw) != value:
        raise Rejected('noncanonical base64url')
    return raw


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Rejected('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise Rejected('nonfinite JSON number')
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise Rejected('nonfinite JSON number')
        return number
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Rejected('invalid JSON: ' + str(exc)) from exc


def public_key(private):
    return private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def key_id(public):
    return 'ed25519:' + encode(hashlib.sha256(public).digest())


def generate_key():
    private = Ed25519PrivateKey.generate()
    return {'private': encode(private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())),
            'public': encode(public_key(private)), 'kid': key_id(public_key(private))}


def sign(payload, private_bytes):
    private = Ed25519PrivateKey.from_private_bytes(private_bytes)
    header = {'alg': 'EdDSA', 'typ': PROFILE, 'kid': key_id(public_key(private))}
    pieces = [encode(json.dumps(value, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()) for value in (header, payload)]
    signed = '.'.join(pieces)
    token = signed + '.' + encode(private.sign(signed.encode('ascii')))
    if len(token) > MAX_MESSAGE_BYTES:
        raise Rejected('message too large')
    return token


class ReplayStore:
    """Durable atomic replay admission; one SQLite database per recipient."""
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS seen (sender TEXT, id TEXT, PRIMARY KEY(sender,id))')

    def admit(self, sender, request_id):
        try:
            with self.db:
                self.db.execute('INSERT INTO seen VALUES (?,?)', (sender, request_id))
        except sqlite3.IntegrityError as exc:
            raise Rejected('replayed request') from exc

    def close(self):
        self.db.close()


def verify(token, trusted_keys, audience, now=None, replay=None, revoked_keys=(), max_lifetime=3600):
    if not isinstance(audience, str) or not audience:
        raise Rejected('invalid expected audience')
    if not isinstance(token, str) or len(token) > MAX_MESSAGE_BYTES:
        raise Rejected('invalid message size/type')
    parts = token.split('.')
    if len(parts) != 3:
        raise Rejected('expected compact JWS')
    header = strict_json(decode(parts[0]))
    if not isinstance(header, dict) or set(header) != {'alg', 'typ', 'kid'} or header['alg'] != 'EdDSA' or header['typ'] != PROFILE:
        raise Rejected('unsupported protected header')
    kid = header['kid']
    if not isinstance(kid, str) or kid in revoked_keys or kid not in trusted_keys:
        raise Rejected('unknown or revoked signer')
    public = trusted_keys[kid]
    if key_id(public) != kid:
        raise Rejected('key binding mismatch')
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(decode(parts[2]), (parts[0] + '.' + parts[1]).encode('ascii'))
    except (InvalidSignature, ValueError) as exc:
        raise Rejected('invalid signature') from exc
    payload = strict_json(decode(parts[1]))
    required = {'version', 'type', 'sender', 'id', 'audience', 'issued_at', 'expires_at', 'body', 'proofs'}
    if not isinstance(payload, dict) or set(payload) != required:
        raise Rejected('invalid envelope fields')
    if payload['version'] != VERSION or not isinstance(payload['type'], str) or payload['type'] not in {'request', 'response', 'grant', 'revocation'}:
        raise Rejected('unsupported version/type')
    if payload['sender'] != kid or payload['audience'] != audience:
        raise Rejected('sender/audience mismatch')
    if not isinstance(payload['id'], str) or not 1 <= len(payload['id']) <= 128 or not isinstance(payload['body'], dict) or not isinstance(payload['proofs'], list) or any(not isinstance(p, str) for p in payload['proofs']):
        raise Rejected('invalid envelope shape')
    issued, expiry = payload['issued_at'], payload['expires_at']
    now = int(time.time()) if now is None else now
    if type(issued) is not int or type(expiry) is not int or not issued <= now < expiry or not 0 < expiry - issued <= max_lifetime:
        raise Rejected('expired, future, or excessive lifetime')
    if replay is not None:
        replay.admit(kid, payload['id'])
    return payload


def authorize(request, grant, authority, now, revoked_grants=()):
    """Direct grant only. Inputs MUST already be cryptographically verified.

    This proves permission scope, not budget reservation or safe execution.
    Delegation chains and paid work are rejected by this reference profile.
    """
    if grant['type'] != 'grant' or request['type'] != 'request' or grant['sender'] != authority:
        raise Rejected('wrong grant authority/type')
    if grant['id'] in revoked_grants or grant['id'] not in request['proofs']:
        raise Rejected('missing or revoked grant')
    body = grant['body']
    expected = {'subject', 'purpose', 'actions', 'resource', 'max_units', 'delegation_depth'}
    if not isinstance(body, dict) or set(body) != expected or type(body['delegation_depth']) is not int or body['delegation_depth'] != 0:
        raise Rejected('unsupported grant/delegation')
    if body['subject'] != request['sender'] or grant['audience'] != request['audience']:
        raise Rejected('grant subject/audience mismatch')
    task = request['body']
    if not isinstance(task, dict) or set(task) not in ({'purpose', 'action', 'resource', 'units'}, {'purpose', 'action', 'resource', 'units', 'sealed_digest'}):
        raise Rejected('unsupported task fields')
    if any(not isinstance(body[k], str) or not body[k] for k in ('subject', 'purpose', 'resource')) or any(not isinstance(task[k], str) or not task[k] for k in ('purpose', 'action', 'resource')):
        raise Rejected('invalid scope values')
    if not isinstance(body['actions'], list) or any(not isinstance(a, str) for a in body['actions']):
        raise Rejected('invalid allowed actions')
    if task['purpose'] != body['purpose'] or task['action'] not in body['actions'] or task['resource'] != body['resource']:
        raise Rejected('scope mismatch')
    if type(task['units']) is not int or type(body['max_units']) is not int or not 0 <= task['units'] <= body['max_units']:
        raise Rejected('resource limit exceeded')
    if not grant['issued_at'] <= now < grant['expires_at'] or not request['issued_at'] <= now < request['expires_at']:
        raise Rejected('expired authorization/request')
    return True
