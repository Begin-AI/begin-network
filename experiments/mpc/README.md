# Synthetic three-party private predicate experiment

Optional experiment, separate from the core runtime. MPyC 0.11 implements a passive honest-majority protocol; this is not malicious-secure discovery or a P2 pass. See [evaluation and leakage](../../docs/mpc-evaluation.md).

```sh
uv venv --python 3.12 /tmp/begin-mpc-env
uv pip install --python /tmp/begin-mpc-env/bin/python --require-hashes -r experiments/mpc/requirements.txt
uv pip install --python /tmp/begin-mpc-env/bin/python .
/tmp/begin-mpc-env/bin/python -m unittest discover -s experiments/mpc -p 'test_*.py' -v
/tmp/begin-mpc-env/bin/python experiments/mpc/run.py > /tmp/begin-mpc-results.json
```

`run.py` launches three subprocesses independently with explicit party indices/addresses. No `-M` auto-spawn is used. Each process opens only its own temporary `input.json`; the helper receives no private fixture values. The controller constructs all synthetic fixtures and verifies outputs. Same-user file permissions are not an OS security boundary: this tests per-party protocol inputs, not isolation from a compromised host/controller. Inputs and logs are temporary and deleted after completion. Public `results.json` records the measured run, source hash, distinct PIDs, outcomes, bytes and time, with no private values.

`party.py` has the fixed circuit; the controller's fixture corpus is absent from that file. The three public vector slots stand for mirror/window/social, each with 32 quantized dimensions. This experiment tests private arithmetic and constraints, not the semantic quality of a trained encoder. Re-run after circuit changes; don't reuse old measurements as current evidence.

Before connecting, each party verifies unanimous signed session consent against public keys pinned in its local input configuration. The identical session digest binds circuit/preflight hashes, model, exact parameters, topology, receiver policy and expiry. Fixture signing keys exist only in controller memory; private input configs carry public keys/signatures only. The controller simulates independently selected fixture identities; do not accept peer-supplied replacement keys as local trust policy. Consent is not a full resource grant, replay ledger, transport authentication or computation proof. Negative tests launch each party independently and verify abort before `mpc.start`.
