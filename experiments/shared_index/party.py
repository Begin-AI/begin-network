"""One independently started discovery node. Reads only its own private shard.

Fixed passive-security circuit; no executable code or trust anchors from queries.
Outputs contain encrypted additive shares, never scores, vectors or open cards.
"""
import asyncio
from importlib.metadata import version
import os
from pathlib import Path
import secrets
import time

from mpyc.runtime import mpc
from begin_network.envelope import decode, strict_json, verify
from begin_network.runtime_bridge import canonical, require
from begin_network.shared_index import (IndexNode, PARAMETERS, PROFILE, fingerprint, norm_tolerance,
    public_snapshot, validate_shares, seal_json, signed)
from begin_network.sealed import sealed_digest
from support import source_hashes


def preflight(config, node):
    from begin_network.discovery_session import validate_session
    require(version('mpyc') == PARAMETERS['mpyc'] and mpc.options.sec_param == 30 and not mpc.options.no_prss and
            mpc.options.ssl and mpc.threshold == 1 and len(mpc.parties) == 3, 'unsupported MPC security profile')
    require(source_hashes() == config['pinned_sources'], 'unapproved local source')
    session, rows = validate_session(config, node, mpc.pid)
    for expected, actual in zip(session['parties'], mpc.parties):
        require((actual.host, actual.port) == (expected['host'], expected['port']), 'wrong runtime topology')
    return session, rows


def valid_row(row, dim, secint):
    vector = row[:dim]
    purpose, role, start, end, floor, active = row[dim:dim+6]
    norm = mpc.in_prod(vector, vector)
    tolerance = norm_tolerance(dim)
    checks = [(v >= -1000) * (v <= 1000) for v in vector]
    checks += [(norm >= 1000000 - tolerance), (norm <= 1000000 + tolerance),
               (purpose >= 0), (purpose <= 2), (role >= 0), (role <= 2),
               (start >= 0), (end < 2**40), (start < end),
               (floor >= 200000), (floor <= 1000000), (active == 1)]
    return mpc.prod(checks)


async def compute(config, rows):
    session = config['session']
    dim = session['contract']['dimensions']
    secint = mpc.SecInt(48)
    field = secint.field
    query = [secint(field(v)) for v in config['query_share']]
    query_valid = valid_row(query, dim, secint)
    results = []
    for stored in rows:
        row = [secint(field(v)) for v in stored['body']['shares']]
        valid = query_valid * valid_row(row, dim, secint)
        # Purpose, role, time and independent exploration floors remain separate
        # from geometry. Neither party's lower threshold overrides the other's.
        qp, qr, qs, qe, qfloor, _ = query[dim:dim+6]
        cp, cr, cs, ce, cfloor, _ = row[dim:dim+6]
        roles = ((qr == 0) * (cr == 1) + (qr == 1) * (cr == 0) + (qr == 2) * (cr == 2))
        score = mpc.in_prod(query[:dim], row[:dim])
        fit = mpc.prod([valid, qp == cp, roles, qs < ce, cs < qe,
                        qe > session['issued_at'], ce > session['issued_at'], score >= qfloor, score >= cfloor])
        key = row[dim+6:]
        fit *= mpc.prod([(v >= 0) * (v <= 255) for v in key])
        results += [fit] + [fit * v for v in key]
    # Convert to fresh 3-of-3 additive output shares. Sending raw Shamir result
    # shares would let a requester reconstruct after only two node releases.
    # Each node contributes a full-field one-time mask, kept private locally.
    masks = [secrets.randbelow(field.modulus) for _ in results]
    for sender in range(3):
        values = masks if sender == mpc.pid else [0] * len(results)
        secret_masks = mpc.input([secint(field(v)) for v in values], senders=sender)
        results = [value - mask for value, mask in zip(results, secret_masks)]
    masked = await mpc.output(results, raw=True)
    return [(mask + (value.value if mpc.pid == 0 else 0)) % field.modulus for mask, value in zip(masks, masked)]


async def main():
    config = strict_json(Path('input.json').read_bytes())
    node = IndexNode('.', config['node_key'], config['pool'])
    try:
        session, rows = preflight(config, node)
        cached = node.reserve(session, session['requester']['address'])
        if cached is not None:
            Path('result.json').write_text(canonical(cached))
            print('CACHED', flush=True)
            return
        print('PREFLIGHT_OK', flush=True)
        await asyncio.wait_for(mpc.start(), timeout=10)
        agreements = await asyncio.wait_for(mpc.transfer(fingerprint(session)), timeout=10)
        require(agreements == [fingerprint(session)] * 3, 'connected peers selected different sessions')
        start = time.perf_counter()
        values = await asyncio.wait_for(compute(config, rows), timeout=90)
        box = seal_json(values, session['requester']['encryption_public'], session['id'], session['requester']['address'])
        result = {'box': box, 'token': signed(node.key, session['requester']['address'], session['id'],
            {'profile': PROFILE, 'session_digest': fingerprint(session), 'sealed_digest': sealed_digest(box)},
            int(time.time()), session['expires_at'], kind='response')}
        node.complete(session, result)
        Path('result.json').write_text(canonical(result))
        metrics = {'party': mpc.pid, 'pid': os.getpid(), 'rows': len(rows), 'tls': True,
                   'elapsed_seconds': time.perf_counter()-start,
                   'bytes_sent': sum(p.protocol.nbytes_sent for p in mpc.parties if p.pid != mpc.pid),
                   'learns_match_bits': False, 'learns_complete_vectors': False}
        await asyncio.wait_for(mpc.shutdown(), timeout=10)
        print('METRICS ' + canonical(metrics), flush=True)
    finally:
        node.close()


mpc.run(main())
