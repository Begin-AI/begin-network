# Shared candidate discovery experiment

This is the executable unfamiliar-candidate path described in [the protocol and leakage account](../../docs/shared-candidate-index.md). It connects secret-shared candidate search to the original participant runtime, using synthetic inputs only.

- `party.py`: one fixed MPyC worker, pinned session consent, mutual TLS, private arithmetic and encrypted result shares.
- `harness.py`: synthetic owner/operator setup, private per-node imports and separate process launching. The controller knows all fixtures; it is not a production coordinator.
- `test_shared_index.py`: candidate enumeration, purpose/role/time/exploration gates, withdrawal, failures, independent pool replacement, budgets and full encrypted exchange.
- `run.py`: run the checks and save input-free evidence with source hashes.
- `run_model.py`: compare a local pinned MiniLM calculation with the protected quantized predicate.
- `results.json`, `model-results.json`: measured local evidence, not live client/deployment certification.

Install the existing hash-locked `../mpc/requirements.txt` in an isolated environment with the core package. Then run `python experiments/shared_index/run.py --report /tmp/begin-shared-index-results.json` from the repository root. The end-to-end MCP test additionally needs `requirements-client.lock` on Python 3.12. GitHub CI is configured to run both; local evidence does not imply remote CI has run.

No production node advertisements, credentials, private inputs or live participant records belong in this directory.
