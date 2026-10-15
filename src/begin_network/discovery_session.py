"""Shared preflight for node APIs and workers; inputs never supply trust policy."""
import time
from .envelope import decode, verify
from .runtime_bridge import require
from .shared_index import PARAMETERS, PROFILE, fingerprint, public_snapshot, validate_shares


def validate_session(config, node, index, *, require_consents=True):
    session = config['session']
    fields = {'profile', 'id', 'pool', 'issued_at', 'expires_at', 'parameters', 'sources', 'parties',
              'contract', 'records', 'requester', 'query_digests'}
    require(isinstance(session, dict) and set(session) == fields and session['profile'] == PROFILE and
            isinstance(session['id'], str) and 1 <= len(session['id']) <= 128, 'invalid index session')
    require(session['sources'] == config['pinned_sources'] and session['parameters'] == PARAMETERS and
            session['pool'] == node.pool, 'unapproved method or pool')
    now = int(time.time())
    require(type(session['issued_at']) is int and type(session['expires_at']) is int and
            session['issued_at'] <= now < session['expires_at'] and
            0 < session['expires_at'] - session['issued_at'] <= 300, 'expired or future session')
    require(session['parties'] == config['pinned_parties'] and len(session['parties']) == 3 and
            len(session['query_digests']) == 3, 'unapproved committee topology')
    peers = []
    for i, expected in enumerate(session['parties']):
        require(set(expected) == {'index', 'host', 'port', 'kid'} and type(expected['index']) is int and
                expected['index'] == i and isinstance(expected['host'], str) and expected['host'] and
                type(expected['port']) is int and 1024 <= expected['port'] <= 65535, 'invalid committee party')
        peers.append(expected['kid'])
    require(len(set(peers)) == 3 and peers[index] == node.key['kid'], 'wrong node identity')
    pins = {kid: decode(public) for kid, public in config['pinned_keys'].items()}
    require(set(pins) == set(peers), 'unapproved committee keys')
    requester = session['requester']
    require(isinstance(requester, dict) and set(requester) == {'address', 'signing_public', 'encryption_public'} and
            config['allowed_requesters'].get(requester['address']) == requester['signing_public'],
            'requester not admitted by node operator')
    require(len(decode(requester['encryption_public'])) == 32, 'invalid result encryption key')
    expected_body = {'profile': PROFILE, 'session_digest': fingerprint(session)}
    authorization = verify(config['requester_consent'], {requester['address']: decode(requester['signing_public'])},
                           'shared-index:' + session['id'], now=now, max_lifetime=300)
    require(authorization['type'] == 'request' and authorization['body'] == expected_body and
            authorization['expires_at'] == session['expires_at'] and not authorization['proofs'], 'wrong requester consent')
    if require_consents:
        signers = set()
        require(isinstance(config['consents'], list) and len(config['consents']) == 3, 'three consents required')
        for token in config['consents']:
            consent = verify(token, pins, 'shared-index:' + session['id'], now=now, max_lifetime=300)
            require(consent['type'] == 'request' and consent['body'] == expected_body and
                    consent['expires_at'] == session['expires_at'] and not consent['proofs'] and
                    consent['sender'] not in signers, 'invalid committee consent')
            signers.add(consent['sender'])
        require(signers == set(peers), 'unanimous committee consent required')
    query = config['query_share']
    method = session['contract']
    require(isinstance(method, dict) and set(method) == {'method', 'model', 'dimensions', 'normalization'} and
            type(method['dimensions']) is int and 1 <= method['dimensions'] <= 384 and
            method['normalization'] == 'l2-quantized-1000', 'invalid method contract')
    validate_shares(query, method['dimensions'] + 6)
    require(fingerprint(query) == session['query_digests'][index], 'query share changed')
    rows = node.snapshot(method)
    require(0 < len(rows) <= PARAMETERS['max_records'] and public_snapshot(rows) == session['records'] and
            all(session['expires_at'] <= row['expires'] for row in rows), 'index snapshot changed or expired')
    return session, rows
