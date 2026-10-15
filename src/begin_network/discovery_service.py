"""Authenticated HTTPS front end and durable scheduler for one private index node.

Operator configuration alone chooses code, peers, certificates and admitted keys.
This is a bounded synthetic pilot service, not production Internet hardening.
"""
import argparse
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import os
from pathlib import Path
import signal
import sqlite3
import ssl
import subprocess
import sys
import threading
import time

from .discovery_session import validate_session
from .envelope import Rejected, decode, key_id, strict_json, verify
from .runtime_bridge import canonical, require
from .shared_index import IndexNode, PARAMETERS, PROFILE, field_type, fingerprint, public_snapshot, signed

API = 'begin-discovery-service-v1'
ROLES = {'upload': 'enroll', 'snapshot': 'query', 'prepare': 'query', 'commit': 'query',
         'result': 'query', 'cancel': 'query'}


def write_private(path, value):
    temporary = path.with_suffix('.new')
    fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def load_config(path):
    config = strict_json(Path(path).read_bytes())
    require(config.get('data_policy') == 'synthetic-only', 'synthetic-only operator policy required')
    require(type(config['party_index']) is int and 0 <= config['party_index'] < 3, 'invalid node index')
    worker = Path(config['worker_path']).resolve()
    support = worker.with_name('support.py')
    for source in (worker, support):
        require(hashlib.sha256(source.read_bytes()).hexdigest() == config['pinned_sources'][source.name], 'unpinned worker source')
    spec = importlib.util.spec_from_file_location('begin_pinned_support', support)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.source_hashes() == config['pinned_sources'], 'runtime source differs from operator pins')
    for kid, client in config['clients'].items():
        require(key_id(decode(client['public'])) == kid and set(client['roles']) <= {'enroll', 'query'}, 'invalid admitted client')
    require(config['pinned_parties'][config['party_index']]['kid'] == config['node_key']['kid'], 'wrong node identity')
    config['allowed_requesters'] = {kid: client['public'] for kid, client in config['clients'].items() if 'query' in client['roles']}
    field_type()  # Initialize optional arithmetic library on the main thread.
    return config


class NodeService:
    def __init__(self, config):
        self.config = config
        self.node = IndexNode(config['state_directory'], config['node_key'], config['pool'])
        self.db = self.node.db
        self.db.execute('CREATE TABLE IF NOT EXISTS api_requests (sender TEXT,id TEXT,digest TEXT,expires INTEGER,response TEXT,PRIMARY KEY(sender,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,owner TEXT,digest TEXT,expires INTEGER,state TEXT,config TEXT,consent TEXT)')

    def close(self):
        self.node.close()

    def call(self, token):
        now = int(time.time())
        keys = {kid: decode(value['public']) for kid, value in self.config['clients'].items()}
        request = verify(token, keys, self.node.key['kid'], now=now, max_lifetime=60)
        body = request['body']
        require(request['type'] == 'request' and not request['proofs'] and
                set(body) == {'profile', 'operation', 'payload'} and body['profile'] == API and
                body['operation'] in ROLES, 'invalid service operation')
        owner, operation = request['sender'], body['operation']
        require(ROLES[operation] in self.config['clients'][owner]['roles'], 'operation not admitted by node operator')
        digest = fingerprint(token)
        self.db.execute('DELETE FROM api_requests WHERE expires<=?', (now,))
        old = self.db.execute('SELECT digest,response FROM api_requests WHERE sender=? AND id=?', (owner, request['id'])).fetchone()
        if old:
            require(old[0] == digest and old[1] is not None, 'conflicting or interrupted API retry')
            return strict_json(old[1])
        require(self.db.execute('SELECT COUNT(*) FROM api_requests WHERE sender=?', (owner,)).fetchone()[0] < 256,
                'short-lived API request budget exhausted')
        try:
            self.db.execute('INSERT INTO api_requests VALUES (?,?,?,?,NULL)', (owner, request['id'], digest, request['expires_at']))
        except sqlite3.IntegrityError as exc:
            raise Rejected('concurrent API retry') from exc
        result = self.dispatch(operation, body['payload'], owner)
        response = {'token': signed(self.node.key, owner, request['id'],
            {'profile': API, 'request_digest': digest, 'result': result}, now, now + 60, kind='response')}
        self.db.execute('UPDATE api_requests SET response=? WHERE sender=? AND id=?', (canonical(response), owner, request['id']))
        return response

    def job(self, identifier, owner):
        require(isinstance(identifier, str) and 1 <= len(identifier) <= 128, 'invalid job ID')
        row = self.db.execute('SELECT owner,digest,expires,state,config,consent FROM jobs WHERE id=?', (identifier,)).fetchone()
        require(row is not None and row[0] == owner and int(time.time()) < row[2], 'unknown, unauthorized or expired job')
        return {'owner': row[0], 'digest': row[1], 'expires': row[2], 'state': row[3],
                'config': strict_json(row[4]) if row[4] else None, 'consent': row[5]}

    def worker_config(self, payload):
        require(isinstance(payload, dict) and set(payload) == {'session', 'query_share', 'requester_consent'}, 'invalid preparation')
        config = {key: self.config[key] for key in
                  ('node_key', 'pool', 'pinned_sources', 'pinned_parties', 'pinned_keys', 'allowed_requesters')}
        return dict(config, **payload, consents=[])

    def dispatch(self, operation, payload, owner):
        require(isinstance(payload, dict), 'object payload required')
        now = int(time.time())
        self.db.execute("UPDATE jobs SET state='expired',config=NULL WHERE expires<=? AND state!='expired'", (now,))
        if operation == 'upload':
            return self.node.apply(payload)
        if operation == 'snapshot':
            require(set(payload) == {'contract'}, 'invalid snapshot request')
            rows = self.node.snapshot(payload['contract'])
            return {'pool': self.node.pool, 'records': public_snapshot(rows),
                    'boxes': {r['body']['record_id']: r['body']['card_box'] for r in rows}}
        if operation == 'prepare':
            config = self.worker_config(payload)
            require(config['session']['requester']['address'] == owner, 'job owner must sign preparation')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                session, _ = validate_session(config, self.node, self.config['party_index'], require_consents=False)
                old = self.db.execute('SELECT owner,digest,consent FROM jobs WHERE id=?', (session['id'],)).fetchone()
                if old:
                    require(old[:2] == (owner, fingerprint(session)), 'conflicting preparation')
                    self.db.execute('COMMIT')
                    return {'consent': old[2], 'duplicate': True}
                require(self.db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('prepared','queued','running')").fetchone()[0] == 0,
                        'node is reserved for another session')
                require(self.db.execute('SELECT COUNT(*) FROM jobs WHERE owner=?', (owner,)).fetchone()[0] < PARAMETERS['max_queries_per_key'],
                        'cumulative preparation budget exhausted')
                consent = signed(self.node.key, 'shared-index:' + session['id'], session['id'],
                    {'profile': PROFILE, 'session_digest': fingerprint(session)}, now, session['expires_at'])
                self.db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)', (session['id'], owner, fingerprint(session),
                    session['expires_at'], 'prepared', canonical(config), consent))
                self.db.execute('COMMIT')
            except Exception:
                self.db.execute('ROLLBACK')
                raise
            return {'consent': consent, 'duplicate': False}
        require(set(payload) == ({'id', 'consents'} if operation == 'commit' else {'id'}), 'invalid job operation')
        job = self.job(payload['id'], owner)
        if operation == 'commit':
            if job['state'] != 'prepared':
                return {'state': job['state']}
            config = dict(job['config'], consents=payload['consents'])
            validate_session(config, self.node, self.config['party_index'])
            self.db.execute("UPDATE jobs SET state='queued',config=? WHERE id=? AND state='prepared'",
                            (canonical(config), payload['id']))
            return {'state': self.job(payload['id'], owner)['state']}
        if operation == 'cancel':
            require(job['state'] in ('prepared', 'cancelled'), 'only an uncommitted reservation can be cancelled')
            self.db.execute("UPDATE jobs SET state='cancelled',config=NULL WHERE id=? AND state='prepared'", (payload['id'],))
            return {'state': self.job(payload['id'], owner)['state']}
        require(operation == 'result', 'unknown job operation')
        result = None
        if job['state'] == 'complete':
            row = self.db.execute('SELECT result FROM sessions WHERE id=? AND requester=? AND digest=?',
                                  (payload['id'], owner, job['digest'])).fetchone()
            require(row and row[0], 'completed result unavailable')
            result = strict_json(row[0])
        return {'state': job['state'], 'result': result}


class Scheduler(threading.Thread):
    def __init__(self, config, lock_fd):
        super().__init__(daemon=True)
        self.config, self.lock_fd = config, lock_fd
        self.stopping = threading.Event()
        self.child = None

    def run(self):
        service = NodeService(self.config)
        try:
            # An interrupted attempt never reruns automatically. Already completed
            # worker results can be recovered without doing another computation.
            service.db.execute("UPDATE jobs SET state=CASE WHEN EXISTS (SELECT 1 FROM sessions s WHERE s.id=jobs.id AND s.result IS NOT NULL) THEN 'complete' ELSE 'failed' END,config=NULL WHERE state='running'")
            while not self.stopping.is_set():
                now = int(time.time())
                service.db.execute("UPDATE jobs SET state='expired',config=NULL WHERE expires<=?", (now,))
                row = service.db.execute("SELECT id,config FROM jobs WHERE state='queued' ORDER BY rowid LIMIT 1").fetchone()
                if row is None:
                    self.stopping.wait(0.1)
                    continue
                identifier, raw = row
                service.db.execute("UPDATE jobs SET state='running' WHERE id=? AND state='queued'", (identifier,))
                root = Path(self.config['state_directory'])
                try:
                    config = strict_json(raw)
                    validate_session(config, service.node, self.config['party_index'])
                    write_private(root / 'input.json', config)
                    (root / 'result.json').unlink(missing_ok=True)
                    command = [sys.executable, self.config['worker_path'], '-I', str(self.config['party_index']), '-T', '1', '--ssl']
                    for peer in self.config['pinned_parties']:
                        command += ['-P', peer['host'] + ':' + str(peer['port'])]
                    # Keeping the node lock in the bounded child prevents a restart
                    # from mixing a new worker with an orphan on the same ports.
                    self.child = subprocess.Popen(command, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                  pass_fds=(self.lock_fd,))
                    self.child.wait(timeout=125)
                    output = service.db.execute('SELECT result FROM sessions WHERE id=?', (identifier,)).fetchone()
                    state = 'complete' if output and output[0] else 'failed'
                except (Rejected, OSError, ValueError, KeyError, subprocess.TimeoutExpired):
                    state = 'failed'
                finally:
                    if self.child is not None and self.child.poll() is None:
                        self.child.kill()
                        self.child.wait(timeout=5)
                    self.child = None
                    for name in ('input.json', 'result.json'):
                        (root / name).unlink(missing_ok=True)
                service.db.execute('UPDATE jobs SET state=?,config=NULL WHERE id=?', (state, identifier))
        finally:
            service.close()

    def stop(self):
        self.stopping.set()
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
        self.join(timeout=10)


def handler_factory(config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            service = None
            self.connection.settimeout(10)
            try:
                require(self.path == '/rpc' and not self.headers.get('Transfer-Encoding') and
                        len(self.headers.get_all('Content-Length', [])) == 1, 'invalid request framing')
                size = int(self.headers['Content-Length'])
                require(0 < size <= 100000 and self.headers.get_content_type() == 'application/json', 'invalid request body')
                raw = self.rfile.read(size)
                require(len(raw) == size, 'truncated request')
                value = strict_json(raw)
                require(isinstance(value, dict) and set(value) == {'token'}, 'signed operation required')
                service = NodeService(config)
                response = service.call(value['token'])
                body, status = canonical({'result': response}).encode(), 200
            except (Rejected, ValueError, KeyError, TypeError, OSError, sqlite3.Error):
                body, status = b'{"error":"rejected discovery operation"}', 400
            finally:
                if service:
                    service.close()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Synthetic private discovery node; operator-managed POSIX host')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    service = NodeService(config)
    service.close()
    root = Path(config['state_directory'])
    lock_fd = os.open(root / 'service.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    server = ThreadingHTTPServer((config.get('bind', '127.0.0.1'), config.get('port', 0)), handler_factory(config))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(config['certificate'], config['private_key'])
    server.socket = context.wrap_socket(server.socket, server_side=True)
    scheduler = Scheduler(config, lock_fd)
    scheduler.start()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(canonical({'port': server.server_address[1], 'node': config['node_key']['kid']}), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        scheduler.stop()
        os.close(lock_fd)


if __name__ == '__main__':
    main()
