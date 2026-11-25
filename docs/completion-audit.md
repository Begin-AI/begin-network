# Completion audit

**Later founder correction:** a separate hosted runner receiving plaintext intentions or complete embeddings is not an acceptable final privacy boundary. This document records experimental implementation/history. Follow [the current handoff](../HANDOFF.md) for the required client-environment execution investigation and unresolved privacy requirements.


## Integrated representation correction — 17 October 2026

The founder clarified that Mirror, Window and Social must be balanced in one representation. The prior implementation and architecture explanation wrongly treated them as mutually exclusive purposes. The participant runtime now requires all three views with editable positive weights; both synthetic and pinned MiniLM encoders produce one normalized weighted vector. The private matcher uses a fixed integrated-v2 marker instead of a same-purpose category gate. Roles, availability, consent and relevance thresholds remain separate constraints.

New encoder/model and shared-index versions reject old single-purpose records; migration requires explicit recreation and re-enrollment. Tests exercise each view's contribution, balance effects, invalid/missing views, legacy rejection, revision invalidation and the private computation's combined-balance predicate. Historical v1 lexical benchmark inputs/results remain explicitly labeled archival; they are not used by the corrected runtime. This corrects the representation structure, not the still-unfinished semantic quality or privacy guarantees.

Validation: 157 core tests, 11 private-index tests and three HTTPS/MCP service tests passed locally. The pinned 384-dimensional model predicate comparison also passed, with refreshed source-bound evidence. Source/wheel builds and public-index structural validation passed; no live deployment or remote CI run is claimed.

## HTTPS discovery services — 15 October 2026

Three HTTPS node services now accept separately authorized enrollment and query callers, issue their own session approvals, schedule bounded workers and retain encrypted results across service restart. The requester runner persists jobs before submission. Five optional MCP tools cover enrollment, withdrawal, search, polling and saved-match contact. The official SDK test closes and reopens two MCP adapters while the node services retain the search. Nodes also compare session digests over their computation connections before using shares.

All three service integration tests, nine shared-index tests and the 151-test core suite passed locally. The pinned 384-dimensional embedding comparison was rerun and its source-bound report refreshed. Source and wheel builds succeeded; packaged service modules, documentation and experiment files were inspected. Updated CI has not run remotely. They cover authorization/role rejection, result-owner isolation, persisted results, missing consents, query mutation, snapshot withdrawal, cancellation and the two-client MCP path. The original shared-index suite now adds a mismatched-session regression. See `discovery-services.md` for operator configuration and precise limits. Tests remain on one host with synthetic inputs; actual GPT/Claude products, independent operators, production scheduling, stronger privacy and semantic evaluation remain unfinished. No deployment or public node advertisement was made.

## Unfamiliar candidate discovery — 15 October 2026

The shared-index experiment now connects private arithmetic to candidate enumeration and the original runtime. Three independently keyed processes hold Shamir shares of purpose-bound embeddings/constraints and a sealed introduction's opening key. A fixed MPyC circuit compares records without opening vectors or match bits at the nodes, converts conditional results to three-of-three masked output shares, and encrypts them to the requester. Unfamiliar self-certified keys enter the bridge only through a one-use owner invitation; acceptance and explicit disclosure remain separate.

Eight shared-index acceptance tests pass, including multi-candidate/purpose/role/time/exploration gates, replay/budget persistence, signed withdrawal and snapshot rejection, invalid secret inputs, node loss, an independently keyed replacement pool, and the full encrypted participant exchange. `experiments/shared_index/results.json` binds measured processes/traffic to source hashes. The pinned 384-dimensional MiniLM test also passes its quantized predicate comparison on two synthetic candidates (`model-results.json`); this establishes actual embedding execution, not semantic usefulness.

The final local Python 3.12 suite passed **151 tests** with both optional MCP and MPC dependencies installed, including ten introduction-boundary tests and source-bound evidence checks. Source and wheel builds succeeded and their new modules, experiment files and evidence were verified in the archives. The updated CI jobs have not been run remotely for this local change.

The official SDK now exercises the unfamiliar path across six subprocesses: two MCP participants, three discovery nodes and an HTTPS relay. The same complete exchange also passed with the pinned MiniLM encoder in the participant servers. No counterpart roster or direct matching grant is supplied. The harness still performs private enrollment/query submission and session scheduling. Nodes are separate processes on one machine under one controller, not independently administered hosts. Passive honest-majority assumptions, exposed metadata, weak aggregate abuse controls and unreviewed conditional release remain material limitations. The existing Sites deployment and live GPT/Claude products have not been migrated. See `shared-candidate-index.md` for the exact boundary; the original objective and P1–E4 remain incomplete.

## Client architecture correction — 15 October 2026

The separate Sites inbox pilot did not use this runtime and is not evidence for the founding network architecture. The new participant bridge in this repository composes its actual signing, grants, intention contracts, bootstrap, encrypted owner-local matching and mailbox implementations. See `participant-bridge.md` for the complete scope, custody/leakage contract and remaining work.

Local Python 3.12 execution passed 138 tests, including the new separate-process official-MCP/HTTPS exchange and negative, restart, duplicate, expiry, decline, revocation and out-of-order cases. The same MCP process test also passed with the pinned local MiniLM model and all 11 model-file hashes checked. The new tagged-intention encoder has no measured semantic quality claim. Source and wheel builds succeeded with the new adapter entry points. A new optional CI job is configured; no remote CI result is claimed yet.

At that snapshot, peer selection still used a pinned roster and out-of-band matching grants and MPC was separate. The subsequent shared-index milestone above supersedes those two limitations at experimental scope. No actual GPT/Claude product has called this bridge and P1–E4 remain incomplete. All new exchanges use synthetic data on one machine. The older live Sites exchange remains separately documented.

Baseline assessment: 2026-10-14, before runtime implementation. This matrix is a living evidence ledger. Missing evidence means unfinished, even if a design is documented. Public publication remains a separate explicit founder decision; work may make the private repository publishable without making it public.

## Original objective and required deliverables

Build a complete publishable repository anchored in the patent and founding brief, including the protocol and publishable discovery index. Test different mechanisms, independent agents, agent goals, runtime acquisition and signing, incoming verification, coordinating coordinators, and information retained by representations. Do not replace this with a schema-only seed or label synthetic plaintext as private discovery.

| Requirement | Authoritative proof required | Baseline evidence / state |
|---|---|---|
| Patent-aligned independent operation | Documented mapping of Figures 1–9 and founder decisions; runnable network without company approval | `AGENTS.md`, `docs/protocol.md` document direction. Runtime proof missing. |
| Stable protocol contract | Exact wire format, canonicalization/profile, version rejection, deterministic vectors and normative state transitions | `docs/protocol.md` draft leaves signing profile unresolved. Unfinished. |
| Runtime download and agent use | Clean isolated install from built artifact, agent generates key/signature, independent verifier accepts | Python package exists for index validator only. No runtime acquisition proof. |
| Authentic incoming requests | Cross-implementation signature, altered bytes, wrong audience, expiry, replay and forged-authority failures | P1 not demonstrated. |
| Bounded grants and goals | Scope attenuation, human/agent initiative, decline/pause/exit, no implicit rights, atomic budgets and revocation | P3 and D2 not demonstrated. |
| Coordinator coordination | Multiple processes with separate keys/state, inter-node route, loop/refusal handling, failover and expiry | P4 not demonstrated. |
| Offline continuity | Disconnect/reconnect, encrypted retained response, retries/deduplication, TTL, revoked resumption rejected | No mailbox implemented at baseline. |
| Sealed disclosure | Receiver-specific encryption; key release requires match and authority; tamper/wrong recipient failures | Missing. |
| Private semantic discovery | Named mechanism, adversaries/collusion, measured transcript/leakage, probing/inversion and authorization evidence | P2 missing. Research plan in `docs/threat-model.md` is not implementation evidence. |
| Faithful useful representations | Versioned labeled corpus with facts/aspirations/inferences distinct, complementary roles, hard constraints, multilingual error metrics, incompatible-model rejection | E1–E4 missing. |
| Need and fair opportunity | Cases with no public profile/contribution, newcomer participation, no authority from compute/extra keys | D1/D4 missing. |
| Personal control | Inspect/edit/retire purpose-bound mirror/window/social data; outputs obey edits and expiry | D3 missing. |
| Independent agent tests | Different agents follow documented install/use without hidden intervention; recorded commands/results and failures | Missing. Agent review alone is not runtime interoperability. |
| Publishable discovery index | Public schema + validator + usable methods/node metadata + offline mirror/bootstrap instructions, no private content | `discovery/index.json`, schema and seven test definitions exist. No live nodes advertised. Structural evidence only. |
| Reproducible release | Clean environment install, tests, demo, packaged schemas/examples, CI, dependency review and honest status | Baseline package/test files exist; fresh installed-run evidence pending. |
| Publication rights | Founder-approved code/patent license, attribution/dependency inventory, no private source or secrets | Explicit licensing decision unresolved. No patent grant inferred. |

## Baseline commands observed

`python3 -m unittest discover -s tests -v` in an uninstalled system environment fails to import `begin_network`. `PYTHONPATH=src python3 -m unittest discover -s tests -v` runs seven tests, with six passing and `test_invalid_timestamp` failing in that system environment. This is not the declared clean installation path; install declared extras in an isolated environment and repeat before attributing the failure to source. Never replace this record with an unqualified claim that tests passed.

## Evidence update rules

Record commit/artifact hash, command, environment, expected result, observed result and scope for each completed row. Independent processes in one machine prove process separation, not arbitrary network/platform interoperability. An independent verifier must implement the wire contract separately; two callers of the same verifier do not prove independent implementation. A toy fixed vocabulary or hash embedding provides a useful baseline but does not establish real-world semantic quality. Preserve failed experiments and current limitations.

P1–E4 remain individually gated by `docs/release-gates.md`; publishing an experimental repository and enabling personal-data participation have different evidence requirements. A release must accurately state which gates passed, which are experimental, and what remains unsupported. The objective is unfinished until every requested deliverable is supported at its actual scope.

## Runtime milestone evidence (2026-10-14)

Implemented experiments now supersede the baseline-only implementation state above; the full objective remains unfinished. The dedicated `.venv` has declared dependencies and all current tests pass. Independent noneditable install is documented in `agent-install-evidence.md`. Node/Python interoperability is exercised by `test_interop.py`; it proves crypto wire compatibility, not full independent policy implementation. Direct grants, persistent replay, recipient-bound experimental encryption and mailbox durability/concurrency have dedicated adversarial tests. Sealed ciphertext substitution found in review was repaired by signing the box digest. `signing-review.md` tracks findings.

Matching evidence: two plaintext synthetic baselines on 13 fixed cases. Both retain two false positives; vocabulary generalization, multilingual semantic quality and P2 remain unproved. No live network, complete protocol state machine, cumulative budgets, grant chains, secure conditional key-release service, agent-host adapters or complete multi-node routing exists. Licensing remains unresolved. The milestone must not be described as publishable completion.

## Delegation, routing and representation milestone (2026-10-14)

Current evidence extends the previous snapshot: signed grant chains attenuate scope/depth/lifetime; single-owner SQLite accounting prevents sibling and concurrent overspend and survives restart; fresh signed revocation snapshots and immutable owner policy are checked. `test_permissions.py` records adversarial and migration regressions. `permissions.md` states replica/crash/stop-work limits.

`test_routing.py` verifies every signed hop and original binding. `test_coordinator_processes.py` and `examples/coordinator_process_demo.py` demonstrate three independent OS processes over bounded loopback HTTP, signed request routing, offline-peer failover and negative cases. No secure cross-host transport, signed execution receipt or eventual-delivery guarantee is implied.

`test_intentions.py` covers separate facts/aspirations/inferences, consent/disclosure boundaries, multi-purpose records, revision invalidation, retire/expiry, compatibility and timing. The 24-case frozen pretrained benchmark (`embedding-evaluation.md`, `experiments/embeddings/results.json`) measures actual model behavior with pinned weights: MiniLM improves recall but retains five false positives, including negation and aspiration/capability confusion. Core CI validates artifact provenance/counts; rerunning inference is an isolated optional experiment.

`test_local_discovery.py` integrates signed matching permission, encrypted query, recipient-local comparison and offline mailbox delivery. Relays lack the decryption key; the authorized counterpart learns the query. The full description stays undisclosed. This is a bounded experiment with known candidate bootstrap and no full P2 claim. Complete peer discovery, cryptographic conditional key release, multi-owner search, stronger adversary treatment, real host adapters and release licensing remain unverified. Goal remains active.

## Additional private-predicate evidence

`experiments/mpc` contains a separately installed MPyC 0.11 experiment: three independently launched party processes, split synthetic private input files, secret vector/constraint predicate and boolean output limited to requester/owner. Ten predicates matched the plaintext baseline; helper receives no opened output. `docs/mpc-evaluation.md` states passive honest-majority, same-host/no-TLS limits. This is actual cryptographic computation evidence, not a learned encoder or full private discovery claim. Session authentication work is tracked separately as it lands.

### Signed MPC and adversarial repair evidence

All three MPC parties now verify unanimous signatures binding the same circuit/preflight hashes, model, parameters, topology, receiver policy and expiry before connecting. Ten-case measured execution succeeds; twelve negative subprocess preflights reject changed code, missing signatures, validly signed mismatched consent and expiry. This is local pinned-key consent, not full resource authority or authenticated transport. CI runs this experiment separately and records a fresh report.

Review also found and repaired NaN time acceptance, Boolean vector contracts, transit-peer path truncation/hop-limit reset, and replay admission after expensive query computation. The origin now signs ingress and hop budget; matching admission precedes decryption after scope/digest checks. Regression tests and `discovery-review.md` preserve findings and repair verification. Full release is still not established.

## Remote acquisition and fresh Linux execution

`remote-agent-evidence.md` records another agent fetching exact commit `464d775563d64f56454b011e8ac53419b9030945` from private GitHub, archive/wheel hashes, a noneditable isolated installation, signing/verification/tamper/replay tests, index validation and three-process routing. That archived demo injected a source path into children; an external wrapper separately proved installed-site-packages-only consumption. The current demo removes that source-path injection. The distinction is preserved rather than claiming the old stock demo used the wheel exclusively.

`ci-evidence.md` binds a passing Linux run to the same commit and preserves its MPC report hash. 85 core tests and six separate experiment tests passed; ten real MPC predicates matched. This supports fresh environment execution, not secure multi-admin deployment or full publication completion. Charter and activity definitions now complete those seed-document artifacts. Next required integration is a useful bounded goal exchange with signed outcome/provenance, deliberate failure/recovery handling, reviewed discovery/bootstrap selection, host adapter behavior, and a requirement-by-requirement release audit. Code/patent licensing remains a founder decision.

## Bounded goal and candidate release milestone

Commit `db98de18a9d20b9e5bd859d07a950b17c954b97d` adds signed exact-byte discovery bootstrap, scoped fixed interval-overlap execution and encrypted signed outcome/provenance. Goal examples cover local formation/known-candidate discovery, voluntary proposal, delegated permission, three-process delivery, atomic one-unit accounting, encrypted result, mailbox reopen, verification and duplicate caching. Negative tests cover no-match, decline, malformed ciphertext, wrong worker, unbound grant digests, expiry, failure after reservation and interrupted reservations. They do not prove external exactly-once effects or live private discovery.

120 core tests passed under local Python 3.9.6 and a fresh noneditable wheel installation on Python 3.12.13. Linux CI run `38516183503` succeeded for that commit, including the separate real MPyC experiment. Source/wheel packaging was inspected and dependency/history scan evidence recorded. `release-checklist.md` maps the minimum packet and original objective to precise evidence and unresolved work; earlier snapshots remain historical. Licensing is unresolved and the repository remains private. The goal is not marked complete.

## Repeated-outcome privacy measurement

`experiments/probing/run.py` now measures an actual signed/encrypted owner-local query oracle with twelve distinct authorized request IDs and one reusable direct per-request grant. Adaptive boolean results narrow a synthetic first-quadrant 2D vector angle to width 0.0003834952 radians; midpoint error is 0.0001188825 radians. A second agent reproduced the transcript-only recovery and additional synthetic angles. This is observed leakage, not a signature/encryption break or a claim of arbitrary learned-embedding inversion. Matching has no cumulative query ledger; the bounded task ledger does not automatically apply. `probing-evaluation.md` preserves the assumptions, failure and missing controls. The core suite now includes this live API experiment (122 tests). P2 and broader private discovery remain unpassed.
