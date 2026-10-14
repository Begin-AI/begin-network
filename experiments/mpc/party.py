"""Fixed synthetic circuit. Each process reads only cwd/input.json, its own input."""
import json
import os
from pathlib import Path
import time
from mpyc.runtime import mpc
import mpyc
from session import preflight

DIM = 32
WIDTH = 3 * DIM + 4
THRESHOLD = 1500000

async def main():
    source = json.loads(Path('input.json').read_text())
    if source['party'] != mpc.pid or not isinstance(source['rows'], list):
        raise ValueError('wrong per-party input file')
    if mpc.pid == 2 and any(row is not None for row in source['rows']):
        raise ValueError('helper must have no private input')
    for row in source['rows']:
        if mpc.pid != 2 and (not isinstance(row, list) or len(row) != WIDTH or any(type(v) is not int for v in row)):
            raise ValueError('invalid private input shape')
    session_digest = preflight(source, mpc, len(source["rows"]))
    print("PREFLIGHT_OK " + session_digest, flush=True)
    secint = mpc.SecInt(48)
    await mpc.start()
    started = time.perf_counter()
    outcomes = []
    for row in source['rows']:
        # Non-senders supply zeros, never another party's private values.
        own = row if mpc.pid in (0, 1) else [0] * WIDTH
        left = mpc.input([secint(v) for v in (own if mpc.pid == 0 else [0] * WIDTH)], senders=0)
        right = mpc.input([secint(v) for v in (own if mpc.pid == 1 else [0] * WIDTH)], senders=1)
        score = mpc.in_prod(left[:3*DIM], right[:3*DIM])
        valid = secint(1)
        # Range checks are part of the circuit; output only combined boolean.
        for vector in (left, right):
            for v in vector[:3*DIM]:
                valid *= (v >= -1000) * (v <= 1000)
            for index in (96, 98):  # role, willingness
                valid *= (vector[index] >= 0) * (vector[index] <= 1)
            valid *= (vector[97] >= 0) * (vector[97] <= 15)
            valid *= (vector[99] >= 0) * (vector[99] <= 1000)
        fit = valid * (score >= THRESHOLD) * (left[96] == 0) * (right[96] == 1)
        fit *= (left[97] == right[97]) * left[98] * right[98] * (left[99] >= right[99])
        result = await mpc.output(fit, receivers=[0, 1])
        outcomes.append(None if mpc.pid == 2 else bool(result))
    bytes_sent = sum(p.protocol.nbytes_sent for p in mpc.parties if p.pid != mpc.pid)
    report = {'party': mpc.pid, 'pid': os.getpid(), 'mpyc': mpyc.__version__,
              'input_file': 'input.json', 'session_digest': session_digest, 'consent_signers': 3, 'private_rows': 0 if mpc.pid == 2 else len(source['rows']),
              'outcomes': outcomes, 'elapsed_seconds': time.perf_counter()-started,
              'protocol_bytes_sent_before_shutdown': bytes_sent, 'tls': False, 'threshold_corrupt': 1}
    await mpc.shutdown()
    print('RESULT ' + json.dumps(report, sort_keys=True), flush=True)

mpc.run(main())
