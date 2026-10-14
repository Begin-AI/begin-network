"""Local, replaceable bootstrap verification. Advertisements confer no authority.

No URL fetching or endpoint connection occurs here. Trust anchors and paths are
selected by the host, never learned from the index or its own attestation.
"""
from datetime import datetime
import hashlib
import os
from pathlib import Path
import stat
import time
from jsonschema import ValidationError
from .envelope import VERSION, MAX_MESSAGE_BYTES, Rejected, strict_json, verify

ATTESTATION_PROFILE = 'begin-index-attestation-v1'
MAX_INDEX_BYTES = 1048576
CONTRACT_FIELDS = {'id', 'method_version', 'model', 'dimensions', 'normalization'}


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timezone required')
        return parsed.timestamp()
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        raise Rejected('invalid index timestamp') from exc


def verify_index(raw, attestation, trusted_keys, audience, *, now=None,
                 requested_contracts=(), capabilities=(), require_runtime=True,
                 max_age=3600, minimum_generated_at=None, revoked_signers=()):
    """Verify exact bytes and locally pinned attestation, then select records.

    minimum_generated_at is an optional host-maintained anti-rollback floor.
    Freshness is checked on every load; attestations are reusable within validity.
    No signer is privileged by company name. Returns unverified service ads.
    """
    now = int(time.time()) if now is None else now
    if type(now) is not int or type(max_age) is not int or max_age <= 0 or type(require_runtime) is not bool:
        raise Rejected('invalid local bootstrap policy')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INDEX_BYTES:
        raise Rejected('invalid index byte size/type')
    if not isinstance(trusted_keys, dict) or not trusted_keys:
        raise Rejected('locally pinned index signer required')
    envelope = verify(attestation, trusted_keys, audience, now=now,
                      revoked_keys=revoked_signers, max_lifetime=max_age)
    expected = {'profile', 'index_sha256', 'protocol_version', 'generated_at'}
    body = envelope['body']
    if envelope['type'] != 'response' or envelope['proofs'] or set(body) != expected or body['profile'] != ATTESTATION_PROFILE:
        raise Rejected('invalid index attestation profile')
    actual_digest = hashlib.sha256(raw).hexdigest()
    if body['index_sha256'] != actual_digest or body['protocol_version'] != VERSION:
        raise Rejected('index digest or version mismatch')
    value = strict_json(raw)
    # Local import avoids coupling package import to CLI initialization.
    from .cli import validate_index
    try:
        validate_index(value)
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise Rejected('invalid discovery index') from exc
    if body['generated_at'] != value['generated_at'] or body['protocol_version'] != value['protocol_version']:
        raise Rejected('index metadata not attested')
    generated = _timestamp(value['generated_at'])
    if not now-max_age <= generated <= envelope['issued_at']:
        raise Rejected('stale or future discovery index')
    if minimum_generated_at is not None:
        if type(minimum_generated_at) is not int or generated < minimum_generated_at:
            raise Rejected('index generation rollback')
    for node in value['nodes']:
        if _timestamp(node['expires_at']) <= now:
            raise Rejected('expired node advertisement')
    if not isinstance(requested_contracts, (list, tuple)) or not isinstance(capabilities, (list, tuple)) or any(c not in ('discovery', 'mailbox', 'coordination') for c in capabilities):
        raise Rejected('invalid requested discovery capabilities')
    selected=[];seen=set()
    by_id={method['id']:method for method in value['methods']}
    for contract in requested_contracts:
        if not isinstance(contract, dict) or set(contract) != CONTRACT_FIELDS or not isinstance(contract['id'], str) or contract['id'] in seen:
            raise Rejected('invalid or duplicate requested method contract')
        seen.add(contract['id'])
        method=by_id.get(contract['id'])
        if method is None or any(type(method[k]) is not type(contract[k]) or method[k] != contract[k] for k in CONTRACT_FIELDS) or not method['implemented'] or method['status']=='proposed' or (require_runtime and method['availability']!='runtime'):
            raise Rejected('unsupported requested method contract')
        selected.append(dict(method))
    nodes=[dict(node) for node in value['nodes'] if set(capabilities)<=set(node['capabilities'])]
    if capabilities and not nodes:
        raise Rejected('no advertised node supports requested capabilities')
    return {'protocol_version': value['protocol_version'], 'generated_at': value['generated_at'],
            'index_sha256': actual_digest, 'attested_by': envelope['sender'],
            'attestation_expires_at': envelope['expires_at'],
            'methods': selected if requested_contracts else value['methods'], 'nodes': nodes,
            'authority_granted': False}


def _read_local(path, limit):
    if not isinstance(path, (str, Path)) or '://' in str(path):
        raise Rejected('bootstrap sources must be explicitly chosen local paths')
    path=Path(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Rejected('bootstrap source must be a regular file')
        raw=stream.read(limit+1)
    if len(raw)>limit:
        raise Rejected('bootstrap file too large')
    return raw


def load_mirrors(sources, trusted_keys, audience, **policy):
    """Choose first valid locally selected (index_path, attestation_path) pair.

    A failed mirror cannot loosen policy for subsequent mirrors. Host policy may
    replace the list or trusted keys to use any independently operated bootstrap.
    """
    if not isinstance(sources, (list, tuple)) or not sources:
        raise Rejected('at least one local bootstrap source required')
    failures=[]
    for pair in sources:
        try:
            if not isinstance(pair, (list, tuple)) or len(pair)!=2:
                raise Rejected('invalid mirror path pair')
            raw=_read_local(pair[0],MAX_INDEX_BYTES)
            token=_read_local(pair[1],MAX_MESSAGE_BYTES).decode('utf-8').strip()
            result=verify_index(raw,token,trusted_keys,audience,**policy)
            result['source']=str(Path(pair[0]))
            result['rejected_mirrors']=len(failures)
            return result
        except (Rejected, OSError, UnicodeError) as exc:
            failures.append(type(exc).__name__)
    raise Rejected('no valid local discovery mirror (' + ', '.join(failures) + ')')
