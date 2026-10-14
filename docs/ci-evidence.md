# Linux CI evidence

[GitHub run 38513280497](https://github.com/Begin-AI/begin-network/actions/runs/38513280497), source commit `464d775563d64f56454b011e8ac53419b9030945`, passed both core validation and the separate signed MPC experiment job.

Core validation: 85 tests, Python 3.11 plus Node 22, and five-method discovery-index validation. MPC: fresh noneditable core installation, hash-pinned MPyC 0.11 on Python 3.12, six experiment tests (including twelve rejecting subprocess preflights), and actual three-party protocol execution. Ten of ten predicates agreed with plaintext outputs; helper received no opened results. Three distinct Linux PIDs were recorded.

Downloaded artifact `mpc-experiment-evidence/mpc-results.json` is preserved as `experiments/mpc/results-ci-linux.json`. Its SHA-256 is `e25559c7a217e2a33a32a40410181f571c40022acd651eba1d3ce15b6ec98a18`. Measured wall time was 21.497 seconds on the hosted Linux x86_64 runner. The source and artifact binding is provided by the named GitHub run; this is not an independently signed release artifact.

This extends macOS evidence to a fresh Linux CI environment. Parties still share one host and loopback transport; it does not prove independent-host administration, TLS or production security. The core test count excludes optional experiment tests and model inference; embedding CI checks stored corpus/model provenance and result accounting without rerunning the model.

## Bounded goal candidate

[Run 38516183503](https://github.com/Begin-AI/begin-network/actions/runs/38516183503) succeeded at `db98de18a9d20b9e5bd859d07a950b17c954b97d`: 120 core tests, index validation, bounded goal demonstration and separate MPC job. [Run 38516451571](https://github.com/Begin-AI/begin-network/actions/runs/38516451571) succeeded at `cc2b30cf13d5d1bf4a357eecb7e06be8f3816f5c`, adding the capability-reporting command and its test (121 total). These are fresh Linux installations from the hashlocked core dependencies, not source-path test shortcuts.
