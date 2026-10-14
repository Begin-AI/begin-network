"""Experimental receiver-bound encrypted content; not private semantic matching.

X25519 ephemeral/static agreement, HKDF-SHA256, AES-256-GCM. This composition
requires external review before real personal data. Receiver keys are pinned by host.
"""
import json
import hashlib
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .envelope import encode, decode, Rejected, authorize


def encryption_key():
    key = X25519PrivateKey.generate()
    return {'private': encode(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())),
            'public': encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))}


def context(request_id, audience):
    if not isinstance(request_id, str) or not request_id or not isinstance(audience, str) or not audience:
        raise Rejected('missing encryption context')
    return json.dumps(['begin-sealed-v1', request_id, audience], separators=(',', ':')).encode()


def derive(private, public, associated):
    shared = private.exchange(X25519PublicKey.from_public_bytes(public))
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=associated).derive(shared)


def seal(plaintext, recipient_public, request_id, audience):
    if not isinstance(plaintext, bytes) or len(plaintext) > 32768:
        raise Rejected('invalid sealed payload size/type')
    ephemeral = X25519PrivateKey.generate()
    associated = context(request_id, audience)
    nonce = os.urandom(12)
    key = derive(ephemeral, recipient_public, associated)
    return {'profile': 'begin-sealed-v1',
            'ephemeral': encode(ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
            'nonce': encode(nonce), 'ciphertext': encode(AESGCM(key).encrypt(nonce, plaintext, associated))}


def sealed_digest(box):
    return hashlib.sha256(json.dumps(box, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def open_authorized(box, recipient_private, request, grant, authority, now, *, matched, revoked_grants=()):
    """Inputs request/grant must be independently verified. Match is host policy.

    A caller that controls the private key can bypass this application API. This is
    not cryptographic enforcement against a malicious authorized key holder.
    """
    if matched is not True:
        raise Rejected('match required before disclosure')
    authorize(request, grant, authority, now, revoked_grants)
    return _decrypt_bound(box, recipient_private, request)


def open_match_query(box, recipient_private, request, grant, authority, now, *, revoked_grants=()):
    """Pre-match disclosure to an explicitly permitted participant, not a node.

    Does not release the separately sealed full request. Inputs must be verified.
    """
    authorize(request, grant, authority, now, revoked_grants)
    if request['body']['action'] != 'match' or request['body']['purpose'] != 'begin-discovery':
        raise Rejected('explicit matching permission required')
    return _decrypt_bound(box, recipient_private, request)


def _decrypt_bound(box, recipient_private, request):
    if not isinstance(box, dict) or set(box) != {'profile', 'ephemeral', 'nonce', 'ciphertext'} or box['profile'] != 'begin-sealed-v1':
        raise Rejected('invalid sealed profile')
    if request['body'].get('sealed_digest') != sealed_digest(box):
        raise Rejected('sealed content not bound to signed request')
    associated = context(request['id'], request['audience'])
    try:
        private = X25519PrivateKey.from_private_bytes(recipient_private)
        key = derive(private, decode(box['ephemeral']), associated)
        nonce, ciphertext = decode(box['nonce']), decode(box['ciphertext'])
        if len(nonce) != 12 or len(ciphertext) > 32784:
            raise Rejected('invalid sealed payload size')
        return AESGCM(key).decrypt(nonce, ciphertext, associated)
    except Exception as exc:
        raise Rejected('sealed content could not be opened') from exc
