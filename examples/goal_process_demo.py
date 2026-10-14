"""Actual synthetic goal execution in separate loopback-only processes."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

from begin_network.coordination import Mailbox
from begin_network.envelope import Rejected, ReplayStore, decode, strict_json, verify
from begin_network.execution import FixtureWorker
from begin_network.permissions import PermissionLedger
from begin_network.routing import Coordinator, Refused


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GOAL = sibling('goal_exchange_demo')
HTTP = sibling('coordinator_process_demo')
MAX_BODY, TIMEOUT = HTTP.MAX_BODY, HTTP.TIMEOUT
post = HTTP.post


def serve():
    config = strict_json(sys.stdin.buffer.readline(MAX_BODY + 1))
    replay = ReplayStore(config['replay'])
    ledger = None
    executor = None
    current_attachment = None
    def transport(peer, packet):
        return post(config['endpoints'][peer] + '/route', {'packet':packet,'attachment':current_attachment})
    coordinator = Coordinator(decode(config['key']['private']),
        {kid:decode(value) for kid,value in config['peers'].items()},
        {kid:decode(value) for kid,value in config['origins'].items()},
        config['routes'],replay,transport,clock=lambda:GOAL.NOW)
    if config['role'] == 'worker':
        ledger = PermissionLedger(config['ledger'],audience=coordinator.id,
            authority=config['authority'],trusted_keys={kid:decode(value) for kid,value in config['trusted'].items()})
        executor = FixtureWorker(private=decode(config['key']['private']),
            encryption_private=decode(config['encryption_private']),
            requester_encryption_keys={kid:decode(value) for kid,value in config['requester_encryption_keys'].items()},
            ledger=ledger,resources={'fixture:mentor':{'kind':'synthetic','revision':'fixture-v1','slots':[[540,600],[780,840]]}})

    def stats():
        if ledger is None: raise Rejected('worker endpoint only')
        return {'worker_pid':os.getpid(),
            'completed_executions':ledger.db.execute("SELECT COUNT(*) FROM executions WHERE state='completed'").fetchone()[0],
            'budget_spent':dict(ledger.db.execute('SELECT id,spent FROM grants'))}

    def execute(original, attachment, *, retry_only=False):
        if executor is None: raise Rejected('worker endpoint only')
        if retry_only:
            # Local retry endpoint cannot admit fresh work that bypassed routing.
            payload = verify(original,ledger.keys,coordinator.id,now=GOAL.NOW)
            operation = payload['sender'] + ':' + payload['id']
            if not ledger.db.execute('SELECT 1 FROM executions WHERE operation=?',(operation,)).fetchone():
                raise Rejected('direct endpoint accepts admitted retries only')
        ledger.apply_revocations(attachment['revocation_snapshot'],GOAL.NOW)
        result = executor.execute(original,attachment['grant_tokens'],attachment['sealed_input'],now=GOAL.NOW)
        return {'result':result, **stats()}

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(TIMEOUT)
        def log_message(self,*_): pass
        def do_POST(self):
            nonlocal current_attachment
            try:
                lengths = self.headers.get_all('Content-Length',[])
                if self.headers.get('Transfer-Encoding') or len(lengths)!=1 or not lengths[0].isdigit():
                    raise Rejected('one content length required')
                length = int(lengths[0])
                if not 0 < length <= MAX_BODY: raise Rejected('test body too large')
                raw = self.rfile.read(length)
                if len(raw)!=length: raise Rejected('truncated body')
                data = strict_json(raw)
                if self.path == '/stats':
                    if data != {}: raise Rejected('invalid stats request')
                    response = stats()
                else:
                    if not isinstance(data,dict) or set(data) != {'packet','attachment'}: raise Rejected('invalid transport object')
                    attachment = data['attachment']
                    if not isinstance(attachment,dict) or set(attachment) != {'grant_tokens','sealed_input','revocation_snapshot'}:
                        raise Rejected('invalid attachment')
                    current_attachment = attachment
                    packet = data['packet']
                    if not isinstance(packet,dict): raise Rejected('invalid packet')
                    if self.path == '/submit':
                        if set(packet) != {'original','destination'}: raise Rejected('invalid submit')
                        response = coordinator.submit(packet['original'],packet['destination'])
                    elif self.path == '/route':
                        response = coordinator.receive(packet)
                        if executor is not None:
                            response = execute(packet['original'],attachment)
                    elif self.path == '/retry':
                        if set(packet) != {'original'}: raise Rejected('invalid retry')
                        response = execute(packet['original'],attachment,retry_only=True)
                    else: raise Rejected('unknown endpoint')
                status = 200
            except Refused:
                status,response = 409,{'error':'refused'}
            except (Rejected,ValueError,KeyError,TypeError,TimeoutError):
                status,response = 400,{'error':'rejected'}
            finally:
                current_attachment = None
            encoded = json.dumps(response).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(encoded)))
            self.send_header('Connection','close')
            self.end_headers()
            self.wfile.write(encoded)

    server = HTTPServer(('127.0.0.1',0),Handler)
    print(json.dumps({'port':server.server_port,'pid':os.getpid(),'kid':coordinator.id}),flush=True)
    try: server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        replay.close()
        if ledger is not None: ledger.close()


class GoalProcessNetwork:
    def __init__(self,directory):
        self.scenario = GOAL.prepare(directory)
        self.children,self.nodes = [],{}

    def __enter__(self):
        try:
            self.start('worker',None)
            self.start('relay','worker')
            self.start('ingress','relay')
            return self
        except BaseException:
            self.close()
            raise

    def start(self,name,next_name):
        scenario,keys = self.scenario,self.scenario['keys']
        config = {'role':name,'key':keys[name],
            'replay':str(scenario['directory'] / (name+'-route.sqlite')),
            'peers':{keys[n]['kid']:keys[n]['public'] for n in ('worker','relay','ingress')},
            'origins':{keys['requester']['kid']:keys['requester']['public']},
            'routes':{keys['worker']['kid']:[keys[next_name]['kid']]} if next_name else {},
            'endpoints':{keys[n]['kid']:node['url'] for n,node in self.nodes.items()}}
        if name == 'worker':
            config.update({'ledger':str(scenario['directory']/'worker-budget.sqlite'),
                'authority':keys['owner']['kid'], 'trusted':{key['kid']:key['public'] for key in keys.values()},
                'encryption_private':scenario['worker_encryption']['private'],
                'requester_encryption_keys':{keys['requester']['kid']:scenario['requester_encryption']['public']}})
        env = os.environ.copy()
        env.pop('PYTHONPATH',None)  # Worker imports the installed runtime, not injected source.
        child = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        self.children.append(child)
        child.stdin.write(json.dumps(config)+'\n')
        child.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ)
            if not selector.select(TIMEOUT): raise RuntimeError('worker startup timeout')
        line = child.stdout.readline()
        if not line: raise RuntimeError('worker failed before readiness: '+child.stderr.read(4096))
        ready = json.loads(line)
        if ready['pid']!=child.pid or ready['kid']!=keys[name]['kid']: raise RuntimeError('unexpected worker identity')
        ready['url'] = 'http://127.0.0.1:'+str(ready['port'])
        self.nodes[name] = ready

    def attachment(self):
        return {'grant_tokens':self.scenario['grant_tokens'],'sealed_input':self.scenario['sealed_input'],
            'revocation_snapshot':self.scenario['snapshot']}

    def submit(self,attachment=None):
        return post(self.nodes['ingress']['url']+'/submit',
            {'packet':{'original':self.scenario['request_token'],'destination':self.scenario['keys']['worker']['kid']},
             'attachment':self.attachment() if attachment is None else attachment})

    def retry(self):
        return post(self.nodes['worker']['url']+'/retry',
            {'packet':{'original':self.scenario['request_token']},'attachment':self.attachment()})

    def run(self):
        bootstrap = GOAL.bootstrap(self.scenario)
        proposal = GOAL.discover(self.scenario)
        if proposal['outcome'] != 'proposed':
            raise AssertionError('fixture discovery did not propose participation')
        response = self.submit()
        result = response['result']
        retry = self.retry()
        if result['duplicate'] or not retry['result']['duplicate'] or retry['result']['token']!=result['token'] or retry['result']['box']!=result['box']:
            raise AssertionError('duplicate not cached')
        if response['worker_pid']!=self.nodes['worker']['pid'] or response['completed_executions']!=1 or retry['completed_executions']!=1:
            raise AssertionError('work did not complete once in worker process')
        if retry['budget_spent']!={'mentor-root':1,'mentor-requester':1}: raise AssertionError('budget changed')
        scenario = self.scenario
        mailbox_path = scenario['directory']/'result-mailbox.sqlite'
        recipient = scenario['keys']['requester']['kid']
        operation = hashlib.sha256(scenario['request_token'].encode('ascii')).hexdigest()
        mailbox = Mailbox(mailbox_path,clock=lambda:GOAL.NOW)
        try:
            # Only signed metadata and encrypted output persist in the mailbox.
            mailbox.submit(operation,recipient,json.dumps({'token':result['token'],'box':result['box']}).encode(),200)
            mailbox.close()
            mailbox = Mailbox(mailbox_path,clock=lambda:GOAL.NOW)
            deliveries = mailbox.retrieve(recipient)
            if len(deliveries)!=1: raise AssertionError('offline result missing')
            replay = ReplayStore(scenario['directory']/'result-replay.sqlite')
            try: received = GOAL.receive(scenario,deliveries[0],replay)
            finally: replay.close()
            if received['output']['slots']!=GOAL.EXPECTED_OVERLAPS: raise AssertionError('incorrect result')
            if not mailbox.claim(recipient,operation) or not mailbox.acknowledge(recipient,operation): raise AssertionError('ack failed')
        finally: mailbox.close()
        return {'bootstrap':bootstrap,'discovery':proposal,'processes':{name:node['pid'] for name,node in self.nodes.items()},
            'worker_pid':response['worker_pid'],'verified_output':received['output'],
            'provenance':received['provenance'],'completed_executions':retry['completed_executions'],
            'budget_spent':retry['budget_spent'],'duplicate_reexecuted':False,
            'offline_retrieval_verified':True,'transport':'synthetic loopback HTTP'}

    def close(self):
        for child in self.children:
            if child.poll() is None: child.terminate()
        for child in self.children:
            try: child.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=TIMEOUT)
            for stream in (child.stdin,child.stdout,child.stderr): stream.close()

    def __exit__(self,*_): self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    if parser.parse_args().worker: serve()
    else:
        with tempfile.TemporaryDirectory(prefix='begin-goal-process-') as directory:
            with GoalProcessNetwork(directory) as network:
                print(json.dumps(network.run(),indent=2))


if __name__ == '__main__': main()
