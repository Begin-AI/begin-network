"""Synthetic controller only. Deployment must distribute state to separate owners.

This harness can see all synthetic inputs and creates fixture trust anchors.
The worker receives only its own state. No OS isolation or live deployment claim.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from begin_network.envelope import decode, generate_key, strict_json
from begin_network.runtime_bridge import canonical, require
from begin_network.shared_index import (IndexNode, PARAMETERS, PROFILE, contract, enroll, fingerprint,
    private_row, public_snapshot, reconstruct, share, signed)
from support import source_hashes

HERE = Path(__file__).resolve().parent


def private_write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(canonical(value))


def certificates(directories):
    """Ephemeral test CA, separate node keys, verified mutual TLS in MPyC."""
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Synthetic independent discovery pool')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .sign(ca_key, hashes.SHA256()))
    for i, directory in enumerate(directories):
        root = directory / '.config'
        root.mkdir(mode=0o700)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = 'MPyC party ' + str(i)
        cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
            .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), False)
            .sign(ca_key, hashes.SHA256()))
        (root / 'mpyc_ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
        (root / ('party_' + str(i) + '.crt')).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        path = root / ('party_' + str(i) + '.key')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


class Committee:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(mode=0o700)
        self.keys = [generate_key() for _ in range(3)]
        self.id = fingerprint({'profile': PROFILE, 'keys': [key['public'] for key in self.keys],
                               'parameters': PARAMETERS, 'sources': source_hashes()})
        self.dirs = [self.root / str(i) for i in range(3)]
        self.nodes = [IndexNode(directory, key, self.id) for directory, key in zip(self.dirs, self.keys)]
        self.pins = {key['kid']: decode(key['public']) for key in self.keys}
        certificates(self.dirs)
        self.last_metrics = []

    def close(self):
        for node in self.nodes:
            node.close()

    def enroll(self, participant, intention_id, *, minimum_score=500000):
        pools = participant.get('discovery_policy', 'pools') or []
        participant.configure_discovery_pools(list(dict.fromkeys(pools + [self.id])))
        offer = participant.offer_discovery(intention_id, self.id)
        _, representation = participant.representation(intention_id)
        owner, uploads = enroll(offer['card'], representation, self.id, self.keys, now=int(time.time()),
                                minimum_score=minimum_score)
        for node, upload in zip(self.nodes, uploads):
            node.apply(upload)
        return owner, uploads, offer

    def prepare(self, representation, requester, *, minimum_score=500000, query_override=None):
        method = contract(representation)
        rows = self.nodes[0].snapshot(method)
        records = public_snapshot(rows)
        require(records, 'no compatible candidate records')
        require(all(public_snapshot(node.snapshot(method)) == records for node in self.nodes), 'nodes disagree on snapshot')
        shares = share(private_row(representation, minimum_score=minimum_score) if query_override is None else query_override)
        ports, sockets = [], []
        for _ in range(3):
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            sockets.append(sock)
            ports.append(sock.getsockname()[1])
        for sock in sockets:
            sock.close()
        now = int(time.time())
        identity = {k: requester.identity()[k] for k in ('address', 'signing_public', 'encryption_public')}
        session = {'profile': PROFILE, 'id': str(uuid.uuid4()), 'pool': self.id, 'issued_at': now,
                   'expires_at': min(now + 240, min(row['expires'] for row in rows)),
                   'parameters': PARAMETERS, 'sources': source_hashes(), 'contract': method,
                   'records': records, 'requester': identity, 'query_digests': [fingerprint(s) for s in shares],
                   'parties': [{'index': i, 'host': '127.0.0.1', 'port': port, 'kid': self.keys[i]['kid']}
                               for i, port in enumerate(ports)]}
        body = {'profile': PROFILE, 'session_digest': fingerprint(session)}
        consent = lambda key: signed(key, 'shared-index:' + session['id'], str(uuid.uuid4()), body, now, session['expires_at'])
        common = {'pool': self.id, 'session': session, 'pinned_sources': source_hashes(),
                  'pinned_parties': session['parties'], 'pinned_keys': {key['kid']: key['public'] for key in self.keys},
                  'allowed_requesters': {requester.id: requester.signing['public']},
                  'requester_consent': consent(requester.signing), 'consents': [consent(key) for key in self.keys]}
        configs = [dict(common, node_key=key, query_share=values) for key, values in zip(self.keys, shares)]
        return session, configs

    def run(self, configs, *, missing=None, expect_failure=False):
        children, logs = [], []
        self.last_metrics = []
        try:
            for i, (config, directory) in enumerate(zip(configs, self.dirs)):
                (directory / 'result.json').unlink(missing_ok=True)
                private_write(directory / 'input.json', config)
                if missing == i:
                    continue
                cmd = [sys.executable, str(HERE / 'party.py'), '-I', str(i), '-T', '1', '--ssl']
                for peer in config['session']['parties']:
                    cmd += ['-P', peer['host'] + ':' + str(peer['port'])]
                log = open(directory / 'worker.log', 'w+')
                logs.append(log)
                children.append(subprocess.Popen(cmd, cwd=directory, stdout=log, stderr=subprocess.STDOUT))
            deadline = time.monotonic() + 110
            for child in children:
                child.wait(timeout=max(1, deadline - time.monotonic()))
            for child, log in zip(children, logs):
                log.seek(0)
                output = log.read()
                if child.returncode and not expect_failure:
                    raise RuntimeError(output[-6000:])
                for line in output.splitlines():
                    if line.startswith('METRICS '):
                        self.last_metrics.append(strict_json(line[8:]))
            return [strict_json((directory / 'result.json').read_bytes()) for directory in self.dirs
                    if (directory / 'result.json').exists()]
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
            for child in children:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            for log in logs:
                log.close()

    def search(self, representation, requester, **kwargs):
        session, configs = self.prepare(representation, requester, **kwargs)
        results = self.run(configs)
        boxes = {row['body']['record_id']: row['body']['card_box'] for row in self.nodes[0].snapshot(session['contract'])}
        cards = reconstruct(session, results, self.pins, requester.encryption['private'], boxes, now=int(time.time()))
        return cards, session, results, configs, boxes
