# Requirement-level experimental release checklist

This ledger preserves the full founder objective and the founding brief's distinction between early experimental publication and live participation. It does not claim completion or authorize public visibility. Historical evidence remains in the completion and release audits.

| Required outcome | Current inspectable evidence | Result and remaining limits |
| --- | --- | --- |
| Patent-guided decentralized design | AGENTS.md, protocol.md, charter.md; no common signing root in fixtures | Architectural alignment documented; no claim of implementing every patent embodiment |
| README and agent manifest | README.md, agent-manifest.json | Present, explicitly experimental/synthetic; capability reporting is local only |
| Charter and versioned protocol schema | charter.md, protocol.md, signing-profile.md; five schemas in schemas/ and installed package | Present; full target state machine is not universally enforced |
| Methods and private-matching specification | matching.md, local-discovery.md, private-discovery-experiment.md, mpc-evaluation.md | Distinct lexical/concept/MiniLM/local-owner/MPC mechanisms tested; complete private discovery remains incomplete |
| Validator and runner/adapter | CLI, runtime-adapter.md, execution.py, goal_process_demo.py | Installed local CLI/Python reference; no arbitrary code execution or mobile-host claim |
| Synthetic positive and negative fixtures | tests/, embedding cases, MPC cases | Tamper, expiry, wrong audience/key, replay, revocation, budget, no-match, decline, failed/interrupted task evidence; external effects not tested |
| Bootstrap and mailbox | discovery-bootstrap.md, coordination.md; corresponding tests | Signed exact-byte local mirror selection and durable recipient mailbox; no public operator availability claim |
| Activity and contributions | activity.md, CONTRIBUTING.md | Definitions and method adoption rules present; zero advertised live nodes |
| Runtime acquisition by agents | remote-agent-evidence.md; candidate-agent-evidence.md when completed | Prior exact-commit download and installed runtime trial proved; current candidate trial tracked separately |
| Produce and verify incoming signatures | test_envelope.py, test_interop.py, remote-agent evidence | Ed25519 Python/Node wire interoperability, CLI verification and rejection cases; no independent complete policy stack |
| Coordinators coordinate | coordinator_process_demo.py, goal_process_demo.py; process tests | Independent OS processes route signed requests, fail over, execute bounded fixture and return encrypted signed result; same-host HTTP only |
| Goals produce useful bounded outcomes | goal-exchange.md, execution.md, goal-processes.md | Synthetic mentor proposal and interval-overlap calculation with one-unit spend, delayed result and cached retry; no real human encounter or external calendar |
| Embeddings retain correct information | embedding-evaluation.md, frozen 24-case corpus/results, intention tests | Actual pinned pretrained model measured; five false positives and one false negative prevent semantic reliability claims; manual demo vectors labeled separately |
| Reproducible package and CI | requirements.lock, package-build-evidence.json, CI run 38516183503 at db98de18a9d20b9e5bd859d07a950b17c954b97d | Candidate wheel/source built and inspected; 120 tests pass locally and Linux candidate CI succeeded; subsequent changes require their own evidence |
| Private-source/secret/dependency review | release-audit.md, dependency-audit.json, exact historical gitleaks fingerprints | Scoped automatic history/staged scan and known-advisory audit; not security certification or legal clearance |
| Publication rights | LICENSE-DECISION.md, dependencies.md | UNRESOLVED owner choice: code license and patent treatment; no license grant inferred |
| Actual public release | GitHub visibility and founder authorization | Not authorized yet; repo must remain private |

The brief's rollout additionally names independent supported agent hosts, private discovery including probing/inversion/key release, opt-in real intentions, and independently operated services. Those remain incomplete and must not be silently relabeled as passed because local synthetic fixtures succeed. They are prerequisites for stronger network/live participation claims. Early publication of specifications, methods and honest synthetic demonstrations is permitted by the brief, but still needs resolved rights and the founder's visibility decision.
