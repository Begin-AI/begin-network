# Independent agent remote acquisition evidence

On 2026-10-14 a separately delegated consumer agent downloaded the private GitHub repository at exact commit **`464d775563d64f56454b011e8ac53419b9030945`**, installed its runtime in a new Python environment, and exercised signatures, index validation, and three coordinator processes. This extends the earlier local-install evidence: acquisition actually traversed GitHub, using the account's existing authorized `gh` credentials. It is not anonymous public installation or a test from another physical host.

## Acquisition and installed artifact

Executed:

```sh
mkdir -p /tmp/begin-remote-consumer-464d775
gh api repos/Begin-AI/begin-network/tarball/464d775563d64f56454b011e8ac53419b9030945 > /tmp/begin-remote-consumer-464d775/source.tar.gz
cd /tmp/begin-remote-consumer-464d775
tar -xzf source.tar.gz
shasum -a 256 source.tar.gz
uv venv --python 3.12 /tmp/begin-remote-consumer-464d775/venv
uv pip install --python /tmp/begin-remote-consumer-464d775/venv/bin/python /tmp/begin-remote-consumer-464d775/Begin-AI-begin-network-464d775563d64f56454b011e8ac53419b9030945
```

GitHub's commit API independently returned the same full commit SHA. The downloaded `agent-manifest.json` points to README and the discovery index, declares synthetic-only data, and grants no authority. The consumer read those files before exercising the CLI. Installation was deliberately noneditable; the README's editable development command was not used.

| Evidence | Value |
| --- | --- |
| Downloaded archive SHA-256 | `cf540eb16f0e598e82e267d9f339199dd220328487eee28fe613d52ac62285b3` |
| Built wheel | `begin_network-0.1.0.dev0-py3-none-any.whl` |
| Built wheel SHA-256 | `b0c81979ca3242489448d31fab5f3f9363da6e70bc2e52bedfbecc67169c19a3` |
| Python | CPython 3.12.13 |
| Platform | macOS 26.6.2 arm64 |
| Installed module directory | `/tmp/begin-remote-consumer-464d775/venv/lib/python3.12/site-packages/begin_network` |
| Installed dependencies checked | cryptography 46.0.7, jsonschema 4.26.0 |

The reviewer located the actual wheel built by uv and compared every `begin_network/` file in that wheel byte-for-byte with the installed module; all matched. Installed `direct_url.json` points to the downloaded source directory with empty `dir_info`, not an editable installation. Signature checks ran from `/tmp` without a source `PYTHONPATH`. The original workspace was never imported.

The archive hash identifies this acquisition; archive container metadata can vary even for an unchanged commit. The wheel hash identifies this build, not a reproducible-build guarantee. No wheel or private key was committed to this repository.

## Signature and index acceptance

Executed `venv/bin/begin-network keygen key.json`. The consumer generated a synthetic request with protocol version `0.1-draft`, sender equal to its new key ID, request ID `remote-agent-goal-1`, recipient `synthetic-owner`, `issued_at = int(time.time())`, expiry 300 seconds later, synthetic task body, and empty proofs. Observed issuance timestamp: `1791953365`.

It wrote a local trust map containing only that public key, then executed:

```sh
venv/bin/begin-network sign --key key.json --payload payload.json
venv/bin/begin-network verify --keys trusted.json --token token.txt --audience synthetic-owner --replay-db replay.sqlite
```

Each verification was a separate CLI process. Absolute paths under the temporary directory were used in the actual calls.

| Case | Exit | Observed result |
| --- | ---: | --- |
| Original current-time signed request | 0 | Signature/profile/fields/audience/expiry/replay checks listed; `permission_checked: false` |
| Identical request, same persisted replay database | 1 | `Rejected: replayed request` |
| Changed body resource, original signature retained | 1 | `Rejected: invalid signature` |

From downloaded source, `venv/bin/begin-network validate-index discovery/index.json` returned exit 0: **5 methods, 0 nodes; trust and privacy not verified**. Envelope acceptance did not authorize execution, and no real participant information was used.

## Coordinator process acceptance with installed runtime

The unchanged downloaded `examples/coordinator_process_demo.py` first passed normally, launching three processes and reporting offline-peer failover. Inspection showed its worker launcher injects downloaded-source `PYTHONPATH`. That normal run proves downloaded-source execution, but alone does not prove all workers use the installed wheel.

The consumer therefore reran the **unchanged downloaded demo** through a temporary external wrapper. The wrapper removed `PYTHONPATH` from each child environment and asserted that both parent and child `begin_network.__file__` contained `/site-packages/` before running the downloaded example. The only launch alteration was import-path control and the import-location assertion; routing logic remained the downloaded code. Reproduction wrapper:

```python
import os, runpy, subprocess
import begin_network
assert '/site-packages/' in begin_network.__file__
original = subprocess.Popen
class InstalledOnlyPopen(original):
    def __init__(self, args, *pos, **kw):
        env = dict(kw.get('env', os.environ))
        env.pop('PYTHONPATH', None)
        kw['env'] = env
        script, worker_args = args[1], args[2:]
        proof = (
            "import begin_network,runpy,sys; "
            "assert '/site-packages/' in begin_network.__file__, begin_network.__file__; "
            "sys.argv=" + repr([script] + worker_args) + "; "
            "runpy.run_path(" + repr(script) + ",run_name='__main__')"
        )
        super().__init__([args[0], '-c', proof], *pos, **kw)
subprocess.Popen = InstalledOnlyPopen
runpy.run_path('/tmp/begin-remote-consumer-464d775/Begin-AI-begin-network-464d775563d64f56454b011e8ac53419b9030945/examples/coordinator_process_demo.py', run_name='__main__')
```

Executed from `/tmp` with the fresh environment's Python. Exit 0; child PIDs were 43865, 43864, and 43863. Output verified the original synthetic goal and origin-bound routing policy, reported `offline_peer_failover: true`, `transport: synthetic loopback HTTP`, and `execution_authorized: false`. All children satisfied the installed-module assertion.

## Limits

This proves an authorized independent agent can remotely acquire this exact private commit, build/install its runtime, generate a signing key, verify incoming envelopes under pinned local trust, reject tamper/replay, validate the index, and coordinate separate local processes using installed code. It does not prove cross-host networking, secure public transport, mobile native execution, anonymous adoption, authorization of arbitrary goals, complete private matching, semantic correctness, or production security. Dependency versions were resolved during installation rather than from a hash-locked release; publication and licensing decisions remain separate.
