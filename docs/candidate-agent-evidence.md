# Candidate acquisition and installed-runtime agent evidence

A collaborating agent independently fetched and tested private GitHub commit `db98de18a9d20b9e5bd859d07a950b17c954b97d` on 2026-10-14. This records an actual download, fresh hash-checked dependency installation, noneditable wheel installation, and runtime use. It is not an independent security audit or a claim of anonymous/public availability. The test agent shares the development host and previously contributed some components; acquisition and installation did not reuse the working checkout or its virtual environment.

## Source and installation identity

- GitHub API confirmed commit `db98de18a9d20b9e5bd859d07a950b17c954b97d`, tree `e0ecebe418527aacc8d5d641a30dab3e8c1b9333`.
- Downloaded archive SHA-256: `40cfb1e390cb47a52f74e935fd312a4e812cb4b4ed508807ace4d147d567a2fc`.
- Candidate `requirements.lock` SHA-256: `f8cba299480216ce8260e1a5b31f8e78d3e56f585701433787af336f5ffed567`.
- Built `begin_network-0.1.0.dev0-py3-none-any.whl` SHA-256: `5cf87cb20c64003ba3120b728f68e39ce8f87b1bbdbf9123dff4c5d52a986390`.
- Fresh runtime: CPython 3.9.6, macOS ARM64; uv 0.10.9; Node.js v25.8.1 for cross-language signature tests.
- Installed module: `/private/tmp/begin-candidate-agent-2vtO8upv/runtime/lib/python3.9/site-packages/begin_network/__init__.py`.

All 17 installed Python modules and packaged schema files compared byte-for-byte equal to their downloaded archive sources. Installation metadata identified a wheel archive, with no editable directory flag. `uv pip check` found all 24 installed packages compatible. The runtime dependencies were installed from the hash-locked candidate requirements, and the local wheel was installed with its separately recorded hash and `--no-deps`.

## Commands executed

The following shows the commands with `BASE` denoting the fresh temporary directory and `SOURCE` the extracted exact-commit archive. These names are explanatory placeholders; the actual directory was `/tmp/begin-candidate-agent-2vtO8upv`.

```sh
gh api repos/Begin-AI/begin-network/tarball/db98de18a9d20b9e5bd859d07a950b17c954b97d > "$BASE/candidate.tar.gz"
gh api repos/Begin-AI/begin-network/commits/db98de18a9d20b9e5bd859d07a950b17c954b97d --jq '{sha: .sha, tree: .commit.tree.sha}'
tar -xzf "$BASE/candidate.tar.gz" -C "$BASE"
uv venv "$BASE/runtime" --python /usr/bin/python3
cd "$SOURCE"
uv pip install --python "$BASE/runtime/bin/python" --require-hashes -r requirements.lock
uv build --wheel --out-dir "$BASE/dist"
uv pip install --python "$BASE/runtime/bin/python" --no-deps --require-hashes -r "$BASE/wheel.lock"
cd /tmp
"$BASE/runtime/bin/python" -I -c 'import begin_network; print(begin_network.__file__)'
"$BASE/runtime/bin/python" -I "$SOURCE/examples/goal_process_demo.py"
"$BASE/runtime/bin/python" -I -m unittest discover -s "$SOURCE/tests" -v
"$BASE/runtime/bin/begin-network" validate-index "$SOURCE/discovery/index.json"
uv pip check --python "$BASE/runtime/bin/python"
```

`wheel.lock` contained a local wheel requirement plus its observed SHA-256. The archive was extracted to an empty directory. The parent checks ran with Python isolated mode from `/tmp`; subprocess workers explicitly removed `PYTHONPATH` and used the same installed interpreter. Build isolation used the candidate's declared build-system requirements; build-tool resolution itself was not hash-locked. The observed wheel hash identifies this artifact, not a demonstrated reproducible-build guarantee.

## Observed results

| Check | Observed result |
|---|---|
| Complete candidate test suite | **120 tests passed**, 11.611 seconds, no skips reported |
| Python ↔ Node Ed25519 JWS interoperability | Passed as part of the candidate suite, including tampering and wrong-key rejection |
| Three-process routing and offline-peer failover | Passed against the installed runtime |
| Bounded goal in separate processes | Passed; ingress PID 48423, relay 48422, worker 48420 |
| Goal output | `{"slots":[[570,600],[800,840]]}` |
| Goal provenance | `synthetic-calculation`, `interval-intersection-v1`, fixture revision `fixture-v1` |
| Goal execution and accounting | One completed execution; one unit spent against root and leaf; direct duplicate returned cached result |
| Offline result retrieval | Durable mailbox reopened; worker signature, requester/request binding, grant chain and ciphertext verified; output decrypted |
| Signed bootstrap | Locally pinned synthetic-owner attestation verified; zero operating nodes and no authority granted |
| Synthetic selected-candidate discovery | Proposal found; full request not disclosed during matching; manual two-dimensional synthetic fixture representation |
| Public discovery-index structure | Five methods, zero nodes; structure valid, trust/privacy explicitly unverified |

Candidate suite output SHA-256: `03d363ea839f52ecdcf4155922edc97439a56c6d4aacc729f5bbf2fae84fddc4`. The raw local output remains at `/tmp/begin-candidate-agent-2vtO8upv/core-tests.log`; temporary paths are test-run evidence locations, not release artifacts.

A separate CLI subprocess check used only temporary synthetic keys and a request with a current 120-second validity window. It invoked `keygen`, `sign`, and `verify` from the installed entry point. First verification returned exit 0 and the original envelope. Signature-byte tampering, an audience mismatch, repeated verification against the same persistent replay database, and attempted key-file overwrite each returned exit 1. The generated private key file had mode `0600`. CLI output correctly stated `permission_checked: false`; CLI envelope verification was not treated as authorization.

Equivalent CLI invocation forms used were:

```sh
begin-network keygen key.json
begin-network sign --key key.json --payload payload.json
begin-network verify --keys trusted-public-keys.json --token token.jws --audience synthetic-receiver --replay-db replay.sqlite
```

Only test-generated private material exists in the temporary test directory; none was added to this repository or printed in this evidence.

## Scope and remaining limits

This establishes that a collaborating agent with authorized private GitHub access can download this candidate, install its locked dependencies and wheel into a clean runtime, generate and verify signatures, reject tested invalid envelopes, and run useful bounded synthetic work across actual process boundaries. Candidate source inspection confirms the goal worker runs the registered fixture intersection implementation, with a shared permission ledger, rather than arbitrary code supplied by a request.

All coordinator processes ran on one development host over loopback HTTP. Process IDs and HTTP accounting are unsigned local instrumentation, not hardware attestation. The test servers lack public transport authentication/TLS and production resource/lifecycle controls. Fixed synthetic clocks and fixture identities support inspectability, not real-device provisioning. The result signature establishes the worker signer and integrity, not honesty of its computation. Mailbox and budget transactions do not provide distributed consensus or recovery from every crash point.

The 120-test core suite does not rerun optional learned-embedding inference or MPC experiment benchmarks. The demonstrated discovery path uses a known synthetic candidate and manually constructed topic vectors; it does not prove semantic representation quality, full private matching, inversion resistance, adaptive-probing defenses, internet-scale discovery, or privacy for real personal data. No P1–E4 gate is declared fully passed.

This candidate still contains a pending code-license/patent decision, rather than an adopted open-source grant. Its private visibility was preserved. This evidence neither authorizes publication nor marks the broader network/repository goal complete.
