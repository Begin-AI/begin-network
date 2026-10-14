# Independent agent runtime installation evidence

A separately delegated consumer agent installed and exercised the current local repository on 2026-10-14. This is actual local artifact installation and CLI execution, not a source-import demonstration or an external-agent endorsement. No private key or participant data is included here.

## Environment and artifact

- macOS 26.6.2, arm64; Python 3.9.6; pip 21.2.4.
- New virtual environment: `/tmp/begin-agent-consumer-20261014`.
- Noneditable PEP 517 wheel: `begin_network-0.1.0.dev0-py3-none-any.whl`.
- Wheel SHA-256 reported by pip: `8159c673371a7fbc5e55726fe11bbfb82d4b88932d14957a609c40eba32f2568`.
- Installed module resolved to `/private/tmp/begin-agent-consumer-20261014/lib/python3.9/site-packages/begin_network/__init__.py` while execution directory was `/tmp`.
- Dependencies included cryptography 46.0.7 and jsonschema 4.25.1; pip obtained dependencies from cache/network. No source `PYTHONPATH` was used.

Commands from the project parent directory:

```sh
python3 -m venv /tmp/begin-agent-consumer-20261014
/tmp/begin-agent-consumer-20261014/bin/python -m pip install ./begin-network
mkdir -p /tmp/begin-agent-consumer-evidence
/tmp/begin-agent-consumer-20261014/bin/begin-network keygen /tmp/begin-agent-consumer-evidence/key.json
```

The consumer read the locally generated public key, pinned its kid-to-public-key mapping in `trusted.json`, and generated a request with `issued_at=int(time.time())`, a 300-second expiry, recipient `independent-coordinator`, and synthetic task body. It invoked CLI `sign --key key.json --payload payload.json`, then `verify --keys trusted.json --token token.txt --audience independent-coordinator --replay-db replay.sqlite`. Absolute paths were used for each argument. Each verification ran in a separate process.

## Observed outcomes

| Case | Exit | Evidence |
| --- | ---: | --- |
| Original current-time request | 0 | Signature/profile/fields/audience/expiry/replay checks listed; `permission_checked: false` |
| Identical token, same persisted replay database | 1 | `Rejected: replayed request` |
| Altered payload segment retaining original signature | 1 | `Rejected: invalid signature` |

Generated request issuance timestamp was `1791951995`. The token had no permission proofs, and acceptance established envelope validity only. The experiment did not execute a task or establish authorization. Local working evidence was retained in `/tmp/begin-agent-consumer-evidence/results.json` and its consumer scripts; generated private keys remain outside this repository.

## Adversarial source review and executed probes

The consumer reviewed `envelope.py` and probed the installed artifact:

1. A correctly signed payload containing `type: []` raises raw `TypeError: unhashable type: 'list'` at type membership validation. The CLI catches it and exits; direct API consumers expecting `Rejected` could crash their handler. Recommended repair: validate the field's string type before membership testing and add a malformed-type regression test.
2. A correctly signed direct grant with `delegation_depth: false` passes `authorize`: Python treats Boolean false as equal to integer zero. This does not grant positive delegation, but violates a strict integer contract and can cause cross-runtime disagreements. Recommended repair: require exact integer type and zero.
3. A nested arbitrary dictionary body passes envelope verification. This is expected structural behavior, not authorization. Hosts must validate application-specific body schemas and call authorization before side effects.
4. Replay storage grows without expiry pruning; retention and admission quotas need an operational policy. This is a source-review observation, not a measured exhaustion attack.
5. `verify` permits callers to omit replay storage; the CLI supplies durable storage. Direct integrations must preserve replay checks. Permission verification, revocation-source freshness, key distribution, and budget reservation remain host responsibilities.

The installed wheel is a snapshot; later source changes require rebuilding and repeating the consumer test. This does not prove remote installation from a release URL, cross-language interoperability, malicious-key safety under every input, dependency reproducibility, private discovery, multi-device operation, or production hardening. No such claims follow from these three successful/rejected CLI cases.
