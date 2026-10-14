"""Synthetic loopback-only multi-process routing demo; not a public server."""
import argparse
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from begin_network.envelope import VERSION, Rejected, ReplayStore, decode, generate_key, sign, strict_json, verify
from begin_network.routing import Coordinator, Refused

MAX_BODY = 1024 * 1024
TIMEOUT = 5


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(url, value):
    target = urlparse(url)
    if target.scheme != 'http' or target.hostname != '127.0.0.1' or not target.port or target.username or target.password:
        raise ValueError('test transport permits numeric loopback HTTP only')
    body = json.dumps(value).encode()
    if len(body) > MAX_BODY:
        raise Rejected('test body too large')
    # Ignore environment proxy settings: this synthetic transport stays loopback.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(Request(url, data=body, headers={'Content-Type':'application/json'}), timeout=TIMEOUT) as response:
            raw = response.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY: raise Rejected('test response too large')
            return strict_json(raw)
    except HTTPError as exc:
        if exc.code == 409: raise Refused('remote node voluntarily refused') from exc
        raise Rejected('remote node rejected packet') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ConnectionError('loopback peer unavailable') from exc


def worker():
    config = strict_json(sys.stdin.buffer.readline(MAX_BODY + 1))
    replay = ReplayStore(config['store'])
    attempts = []
    def transport(peer, packet):
        attempts.append(peer)
        return post(config['endpoints'][peer] + '/route', packet)['payload']
    coordinator = Coordinator(decode(config['key']['private']),
        {k:decode(v) for k,v in config['peers'].items()},
        {k:decode(v) for k,v in config['origins'].items()},
        config['routes'], replay, transport)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(TIMEOUT)
        def log_message(self, *_): pass
        def do_POST(self):
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise Rejected('chunked requests unsupported')
                sizes = self.headers.get_all('Content-Length', [])
                if len(sizes) != 1 or not sizes[0].isdigit():
                    raise Rejected('one content length required')
                length = int(sizes[0])
                if not 0 < length <= MAX_BODY:
                    raise Rejected('test body size exceeded')
                raw = self.rfile.read(length)
                if len(raw) != length: raise Rejected('truncated body')
                data = strict_json(raw)
                if self.path == '/submit':
                    if not isinstance(data, dict) or set(data) != {'original','destination'}: raise Rejected('invalid submit')
                    payload = coordinator.submit(data['original'], data['destination'])
                elif self.path == '/route':
                    payload = coordinator.receive(data)
                else: raise Rejected('unknown endpoint')
                status, result = 200, {'payload':payload, 'attempts':attempts[:]}
            except Refused:
                status, result = 409, {'error':'refused'}
            except (Rejected, ValueError, KeyError, TypeError, TimeoutError):
                status, result = 400, {'error':'rejected'}
            encoded = json.dumps(result).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(encoded)

    server = HTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'port':server.server_port, 'pid':os.getpid(), 'kid':coordinator.id}), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        replay.close()


class ProcessNetwork:
    """Context manager that owns and reaps every demonstration subprocess."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.keys = {name:generate_key() for name in ('origin','a','b','c','offline')}
        self.children = []
        self.nodes = {}
        self.offline_socket = socket.socket()
        self.offline_socket.bind(('127.0.0.1', 0))  # Reserved but deliberately not listening.
        self.offline_url = 'http://127.0.0.1:' + str(self.offline_socket.getsockname()[1])

    def __enter__(self):
        try:
            self.start('c', {})
            self.start('b', {'c':['c']})
            self.start('a', {'c':['offline','b']})
            self.offline_socket.close()  # All live listener ports are allocated; release the offline reservation.
            return self
        except BaseException:
            self.close()
            raise

    def start(self, name, routes):
        endpoints = {self.keys[n]['kid']: info['url'] for n,info in self.nodes.items()}
        endpoints[self.keys['offline']['kid']] = self.offline_url
        config = {'key':self.keys[name], 'store':str(self.directory / (name + '.sqlite')),
            'peers':{k['kid']:k['public'] for n,k in self.keys.items() if n != 'origin'},
            'origins':{self.keys['origin']['kid']:self.keys['origin']['public']},
            'routes':{self.keys[d]['kid']:[self.keys[p]['kid'] for p in peers] for d,peers in routes.items()},
            'endpoints':endpoints}
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        self.children.append(child)
        child.stdin.write(json.dumps(config) + '\n')
        child.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            if not selector.select(TIMEOUT): raise RuntimeError('worker startup timed out')
        line = child.stdout.readline()
        if not line: raise RuntimeError('worker exited before readiness')
        ready = json.loads(line)
        ready['url'] = 'http://127.0.0.1:' + str(ready['port'])
        self.nodes[name] = ready
        return ready

    def token(self, request_id='process-demo'):
        now = int(time.time())
        payload = {'version':VERSION, 'type':'request', 'sender':self.keys['origin']['kid'],
            'id':request_id, 'audience':self.keys['c']['kid'], 'issued_at':now, 'expires_at':now+120,
            'body':{'goal':'synthetic multi-process discovery', 'units':1, 'routing':{'ingress':self.keys['a']['kid'],'hop_limit':8}}, 'proofs':[]}
        return sign(payload, decode(self.keys['origin']['private']))

    def run(self):
        token = self.token()
        result = post(self.nodes['a']['url'] + '/submit', {'original':token, 'destination':self.keys['c']['kid']})
        verified = verify(token, {self.keys['origin']['kid']:decode(self.keys['origin']['public'])}, self.keys['c']['kid'])
        if result['payload'] != verified: raise AssertionError('final original differs')
        if result['attempts'] != [self.keys['offline']['kid'], self.keys['b']['kid']]: raise AssertionError('failover not exercised')
        return {'processes':[self.nodes[n]['pid'] for n in ('a','b','c')],
            'verified_original_body':verified['body'], 'offline_peer_failover':True,
            'transport':'synthetic loopback HTTP', 'execution_authorized':False}

    def close(self):
        for child in self.children:
            if child.poll() is None: child.terminate()
        for child in self.children:
            try: child.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=TIMEOUT)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()
        self.offline_socket.close()

    def __exit__(self, *_): self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker()
    else:
        with tempfile.TemporaryDirectory(prefix='begin-routing-') as directory:
            with ProcessNetwork(directory) as network:
                print(json.dumps(network.run(), indent=2))


if __name__ == '__main__': main()
