"""Synthetic fixture harness; this controller knows fixtures, party runners do not."""
import copy
import hashlib
from importlib.metadata import version
import begin_network.envelope as envelope_implementation
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
from begin_network.envelope import VERSION, generate_key, sign, decode
from session import PARAMETERS, digest, source_hash

HERE = Path(__file__).resolve().parent

def fixture(value=500, role=1, language=1, willing=1, units=1):
    vector = [value] + [0]*31
    return vector*3 + [role, language, willing, units]

def corpus():
    left = fixture(1000, role=0, units=2)
    right = fixture()
    cases = []
    def add(name, r=None, l=None): cases.append((name, copy.deepcopy(l or left), copy.deepcopy(r or right)))
    add('threshold_equal')
    r=right.copy();r[0]=501;add('threshold_above_one_coordinate',r)
    r=right.copy();r[0]=499;add('threshold_below_one_coordinate',r)
    add('wrong_role',fixture(role=0))
    add('language_mismatch',fixture(language=2))
    add('owner_declines',fixture(willing=0))
    add('budget_exceeded',fixture(units=3))
    add('requester_declines',l=fixture(1000,role=0,willing=0,units=2))
    add('out_of_range',fixture(1001))
    add('negative_similarity',fixture(-1000))
    return cases

def plain(a,b):
    valid=all(-1000<=v<=1000 for row in (a,b) for v in row[:96])
    valid &= all(row[96] in (0,1) and row[98] in (0,1) and 0<=row[97]<=15 and 0<=row[99]<=1000 for row in (a,b))
    return bool(valid and sum(x*y for x,y in zip(a[:96],b[:96]))>=1500000 and a[96]==0 and b[96]==1 and a[97]==b[97] and a[98] and b[98] and a[99]>=b[99])

def agreement(ports, case_count, *, expired=False, consent_digest_overrides=None):
    keys=[generate_key() for _ in range(3)]
    now=int(time.time())
    issued=now-60 if expired else now-1
    expiry=now-1 if expired else now+180
    session={'profile':'begin-mpc-consent-v1','id':os.urandom(16).hex(),
             'issued_at':issued,'expires_at':expiry,'party_source_sha256':source_hash('party.py'),
             'session_source_sha256':source_hash('session.py'),'parameters':PARAMETERS,
             'parties':[{'index':i,'host':'127.0.0.1','port':ports[i],'kid':key['kid']} for i,key in enumerate(keys)],
             'case_count':case_count}
    consents=[]
    for index,key in enumerate(keys):
        envelope={'version':VERSION,'type':'request','sender':key['kid'],'id':os.urandom(16).hex(),
                  'audience':'mpc-session:'+session['id'],'issued_at':issued,'expires_at':expiry,
                  'body':{'profile':'begin-mpc-consent-v1','session_digest':(consent_digest_overrides or {}).get(index,digest(session))},'proofs':[]}
        consents.append(sign(envelope,decode(key['private'])))
    # Keys are local fixture identities; only public keys and signatures leave controller.
    return {'session':session,'pinned_keys':{key['kid']:key['public'] for key in keys},'consents':consents}

def main():
    cases=corpus(); expected=[plain(a,b) for _,a,b in cases]
    processes=[]; handles=[]; reports=[]
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='begin-mpc-inputs-') as scratch:
        sockets=[];ports=[]
        for _ in range(3):
            s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s);ports.append(s.getsockname()[1])
        for s in sockets:s.close()
        consent_config=agreement(ports,len(cases))
        try:
            for party in range(3):
                directory=Path(scratch)/str(party);directory.mkdir(mode=0o700)
                rows=[a if party==0 else b if party==1 else None for _,a,b in cases]
                input_file=directory/'input.json';input_file.write_text(json.dumps(dict(consent_config,party=party,rows=rows)));input_file.chmod(0o600)
                command=[sys.executable,str(HERE/'party.py'),'-I',str(party),'-T','1']
                for port in ports: command+=['-P','127.0.0.1:'+str(port)]
                log=open(directory/'stdout.txt','w+');handles.append(log)
                processes.append(subprocess.Popen(command,cwd=directory,stdout=log,stderr=subprocess.STDOUT))
            for p in processes:
                p.wait(timeout=90)
            for p,log in zip(processes,handles):
                log.seek(0);text=log.read()
                if p.returncode: raise RuntimeError(text)
                lines=[s[7:] for s in text.splitlines() if s.startswith('RESULT ')]
                if len(lines)!=1:raise RuntimeError(text)
                reports.append(json.loads(lines[0]))
            assert len({r['pid'] for r in reports})==3
            assert reports[0]['outcomes']==expected==reports[1]['outcomes']
            assert reports[2]['outcomes']==[None]*len(cases)
            result={'experiment':'mpyc-signed-consent-boolean-v2','python':platform.python_version(),'platform':platform.platform(),
                    'party_source_sha256':source_hash('party.py'),'session_source_sha256':source_hash('session.py'),
                    'session_digest':digest(consent_config['session']),'signed_participant_consents':3,
                    'consent_verifier_sha256':hashlib.sha256(Path(envelope_implementation.__file__).read_bytes()).hexdigest(),
                    'begin_network_version':version('begin-network'),'cryptography_version':version('cryptography'),
                    'cases':[{'id':name,'expected':expected[i],'requester':reports[0]['outcomes'][i],'owner':reports[1]['outcomes'][i],'helper':reports[2]['outcomes'][i]} for i,(name,_,_) in enumerate(cases)],
                    'parties':reports,'wall_seconds':time.perf_counter()-started,'all_predicates_equal':True,
                    'transport':'loopback TCP without TLS','scope':'passive honest-majority experiment; same-host controller knows synthetic fixtures; no OS isolation'}
            print(json.dumps(result,indent=2,sort_keys=True))
        finally:
            for p in processes:
                if p.poll() is None:p.terminate()
            for p in processes:
                if p.poll() is None:p.wait(timeout=10)
            for log in handles:log.close()

if __name__=='__main__':main()
