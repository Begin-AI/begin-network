"""HTTPS transport for the runtime's blind relay, using operator-pinned endpoints.

No discovery-advertised URL is fetched automatically. TLS verification remains
enabled, including in loopback tests with an explicitly supplied test CA.
"""
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from .coordination import CoordinationError, Delivery
from .envelope import Rejected, decode, encode, strict_json
from .runtime_bridge import BlindRelay, canonical, require

MAX_BODY = 100000
MAX_RESPONSE = 1500000


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Rejected('relay redirects forbidden')


class HTTPSRelay:
    def __init__(self, service_id, endpoint, *, ca_file=None):
        url = urlsplit(endpoint)
        require(url.scheme == 'https' and url.hostname and not url.username and not url.password and
                not url.query and not url.fragment and url.path in ('', '/'), 'operator-pinned HTTPS origin required')
        self.id, self.endpoint = service_id, endpoint.rstrip('/')
        self.opener = build_opener(NoRedirects(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))

    def call(self, operation, value):
        data = canonical(value).encode()
        require(len(data) <= MAX_BODY, 'relay payload too large')
        request = Request(self.endpoint + '/' + operation, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with self.opener.open(request, timeout=10) as response:
            require(response.headers.get_content_type() == 'application/json', 'invalid relay content type')
            raw = response.read(MAX_RESPONSE + 1)
        require(len(raw) <= MAX_RESPONSE, 'relay response too large')
        result = strict_json(raw)
        require(isinstance(result, dict) and set(result) == {'result'}, 'invalid relay response')
        return result['result']

    def submit(self, packet):
        return self.call('submit', packet)

    def retrieve(self, token):
        result = self.call('retrieve', {'token': token})
        require(isinstance(result, list) and len(result) <= 100, 'invalid relay deliveries')
        return [Delivery(**dict(row, ciphertext=decode(row['ciphertext']))) for row in result]

    def acknowledge(self, token):
        return self.call('acknowledge', {'token': token})


def handler_factory(path, service_id, keys):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No request content, credentials or participant tokens in logs.

        def do_POST(self):
            relay = None
            self.connection.settimeout(10)
            try:
                require(self.path in ('/submit', '/retrieve', '/acknowledge'), 'unknown operation')
                require(not self.headers.get('Transfer-Encoding') and len(self.headers.get_all('Content-Length', [])) == 1,
                        'one bounded Content-Length required')
                length = int(self.headers['Content-Length'])
                require(0 < length <= MAX_BODY and self.headers.get_content_type() == 'application/json', 'invalid request size/type')
                raw = self.rfile.read(length)
                require(len(raw) == length, 'truncated request')
                value = strict_json(raw)
                relay = BlindRelay(path, service_id, keys)
                if self.path == '/submit':
                    result = relay.submit(value)
                else:
                    require(isinstance(value, dict) and set(value) == {'token'}, 'signed authorization required')
                    if self.path == '/retrieve':
                        result = [dict(asdict(d), ciphertext=encode(d.ciphertext)) for d in relay.retrieve(value['token'])]
                    else:
                        result = relay.acknowledge(value['token'])
                body, status = canonical({'result': result}).encode(), 200
            except (Rejected, CoordinationError, ValueError, TypeError, KeyError, IndexError, OSError):
                body, status = b'{"error":"rejected relay request"}', 400
            finally:
                if relay:
                    relay.close()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Experimental synthetic-only blind Begin relay')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    with open(args.config) as stream:
        config = strict_json(stream.read())
    require(config.get('data_policy') == 'synthetic-only', 'synthetic policy required')
    keys = {key: decode(value) for key, value in config['participant_keys'].items()}
    server = ThreadingHTTPServer((config.get('bind', '127.0.0.1'), config.get('port', 0)),
                                handler_factory(config['database'], config['service_id'], keys))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(config['certificate'], config['private_key'])
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(canonical({'port': server.server_address[1], 'service_id': config['service_id']}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
