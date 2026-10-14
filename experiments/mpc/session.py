"""Experimental unanimous local MPC consent, not resource authorization."""
import hashlib
import json
from pathlib import Path
import time
from begin_network.envelope import decode, key_id, verify, Rejected

PARAMETERS = {'model': 'synthetic-quantized-mirror-window-social-v1', 'dimensions_per_slot': 32,
              'slots': 3, 'coordinate_bound': 1000, 'mpyc_version': '0.11', 'statistical_security_parameter': 30, 'prss': True, 'score_threshold': 1500000,
              'secure_integer_bits': 48, 'passive_corruption_threshold': 1,
              'output_receivers': [0, 1], 'transport': 'loopback-no-tls'}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def source_hash(name):
    return hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()

def preflight(config, runtime, row_count):
    session=config['session']; keys=config['pinned_keys']; consent=config['consents']
    expected_fields={'profile','id','issued_at','expires_at','party_source_sha256','session_source_sha256','parameters','parties','case_count'}
    if not isinstance(session,dict) or set(session)!=expected_fields or session['profile']!='begin-mpc-consent-v1':
        raise Rejected('invalid session shape/profile')
    from importlib.metadata import version
    if runtime.options.sec_param != 30 or runtime.options.no_prss or version('mpyc') != '0.11':
        raise Rejected('unsupported runtime security profile')
    if session['parameters']!=PARAMETERS or session['case_count']!=row_count:
        raise Rejected('session parameters/count mismatch')
    if session['party_source_sha256']!=source_hash('party.py') or session['session_source_sha256']!=source_hash('session.py'):
        raise Rejected('session circuit hash mismatch')
    now=int(time.time())
    if type(session['issued_at']) is not int or type(session['expires_at']) is not int or not session['issued_at']<=now<session['expires_at'] or not 0<session['expires_at']-session['issued_at']<=300:
        raise Rejected('expired/future session')
    parties=session['parties']
    if not isinstance(parties,list) or len(parties)!=3 or len(runtime.parties)!=3 or runtime.threshold!=1:
        raise Rejected('unsupported party topology')
    kids=[]
    for i,(declared,actual) in enumerate(zip(parties,runtime.parties)):
        if not isinstance(declared,dict) or set(declared)!={'index','host','port','kid'} or declared['index']!=i or declared['host']!='127.0.0.1' or type(declared['port']) is not int or not 1024<=declared['port']<=65535 or (actual.host,actual.port)!=(declared['host'],declared['port']):
            raise Rejected('runtime topology mismatch')
        kids.append(declared['kid'])
    if len(set(kids))!=3 or set(keys)!=set(kids) or runtime.options.ssl:
        raise Rejected('pinned keys or transport mismatch')
    public={kid:decode(value) for kid,value in keys.items()}
    if any(key_id(value)!=kid for kid,value in public.items()):raise Rejected('pinned key mismatch')
    if not isinstance(consent,list) or len(consent)!=3:
        raise Rejected('unanimous consent required')
    agreed=digest(session); seen=set()
    for token in consent:
        envelope=verify(token,public,'mpc-session:'+session['id'],now=now,max_lifetime=300)
        if envelope['type']!='request' or envelope['proofs'] or envelope['issued_at']!=session['issued_at'] or envelope['expires_at']!=session['expires_at'] or envelope['body']!={'profile':'begin-mpc-consent-v1','session_digest':agreed}:
            raise Rejected('mismatched session consent')
        if envelope['sender'] in seen:raise Rejected('duplicate consent signer')
        seen.add(envelope['sender'])
    if seen!=set(kids):raise Rejected('missing participant consent')
    return agreed
