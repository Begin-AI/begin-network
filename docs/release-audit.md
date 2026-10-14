# Experimental repository release audit

Assessment on 2026-10-14 at checked-out commit `2e7e9b986ce5e86a22ee5bb38d087dd5ac7b50af`. This audit distinguishes a publishable experimental repository from a live personal-data network. It does **not** declare either ready, authorize publication, or close the user's broader active goal.

## Required scope and release distinction

The founder requested a complete publishable repository with the protocol and publishable discovery index, comparative mechanisms, independent-agent and goal tests, downloadable runtime acquisition, signatures and incoming verification, coordinator coordination, and representation-information evaluation. The patent remains the architecture reference; independent operation and local authority must survive changing methods.

The founding brief's “minimum release packet” requires README/agent manifest, charter/versioned protocol schema, embedding methods/private-matching specification, reference validator/runner or adapter, synthetic demo/positive and negative fixtures, bootstrap discovery/mailbox reference, activity definition, and contribution guide. Its explicit release distinction permits **methods, specifications, and synthetic demonstrations to publish early**. Live personal-data participation requires demonstrated privacy and authorization; wider deployment additionally requires useful operation and sustainability.

Consequently, unresolved production private discovery does not by itself forbid publication of honestly labeled research code. Conversely, a repository with a license and green tests is not sufficient to claim the complete discovery network or to finish every requested goal. Experimental scope must be explicit and must not hide missing core research.

## Current reproducible evidence

Independent audit commands on the checked-out tree:

```sh
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/begin-network validate-index discovery/index.json
```

Observed: **85 core tests passed**; index structurally valid with **5 methods and 0 nodes**. Core tests exclude model inference and optional MPC execution. The index is an inspectable publication candidate, not an endorsement of advertisements or evidence of live activity.

| Required deliverable/test | Inspected authoritative evidence | Assessment and scope |
| --- | --- | --- |
| Founder/patent direction | `AGENTS.md`, founding brief, `charter.md`, `protocol.md` | Present; no mandatory company signer/gateway; semantic signatures distinguished from cryptographic authenticity. Full patent implementation is not claimed. |
| Stable experimental protocol | Envelope schema; `signing-profile.md`, permissions/routing specs; negative tests | Implemented profile and target protocol distinguished. Entire message-family/state-machine target is not implemented. |
| Public discovery index | `discovery/index.json`, schema, validator, `discovery/README.md` | Five experimental methods, no private intentions, zero node advertisements, alternate distribution described. Signatures/freshness/certification are not implemented. |
| Agent-accessible release packet | README, manifest, charter, CONTRIBUTING, activity definition | Present; manifest grants no authority. Source and patent licensing remain pending. |
| Runtime remote acquisition | `remote-agent-evidence.md` | Agent actually downloaded GitHub commit `464d775...`, built noneditable runtime in fresh Python 3.12, recorded archive/wheel hashes, checked installed files. Authorized private acquisition, not anonymous public availability. |
| Produce/verify signatures | Remote agent CLI evidence; `test_envelope.py`, `test_interop.py` | Current-time signing/pinned-key acceptance, tamper/replay rejection; Python/Node cryptographic interoperability. Not two complete independent policy implementations. |
| Independent agent scrutiny | Install evidence, signing/permission/discovery reviews | Separately delegated agents executed probes and found repaired flaws. Shared physical host and common runtime remain explicit limits. |
| Coordinators coordinate | `examples/coordinator_process_demo.py`, process/routing tests, remote installed-only rerun | Three processes route signed goals with separate state, offline-peer failover, expiry/loop/path-budget negatives. Loopback only; not independently administered host deployment. |
| Goals and bounded authority | Direct grants, delegated permissions, SQLite budget tests, local discovery request fixture | Scoped synthetic requests and matching predicates are executable. No unified useful goal completion/receipt/retrieval demonstration yet inspected. Routing a goal text does not prove completing that goal. |
| Different mechanisms | Two lexical/concept baselines, MiniLM benchmark, owner-local matching, MPyC experiment | Actual runs with honest distinct guarantees. MPC result uses synthetic predicates, not learned embeddings or full candidate discovery. |
| Information retained by representations | Editable intention tests, 24-case model corpus/results, `embedding-evaluation.md` | Categories and revisions enforced; learned model improves recall but has five false positives, including negation/refusal/aspiration confusion. A small agent-labeled corpus does not prove faithful general representation. |
| Private-matching specification | `private-discovery-experiment.md`, `local-discovery.md`, `mpc-evaluation.md` | Threat assumptions and candidate paths documented; bounded cryptographic predicate measured. Proposed MASCOT/TenSEAL alternatives are not implemented results. |
| Mailbox and asynchronous reference | `coordination.py`, mailbox tests, owner-local offline-delivery test | Local durability, expiry, claiming/deduplication references exist. Not authenticated internet mail service or end-to-end exactly-once external effects. |
| Linux reproducibility | `ci-evidence.md`, workflow, recorded MPC Linux artifact | Named source commit/run: 85 core tests plus separate MPC tests/protocol execution. Model inference not rerun in core CI. |

## Concrete remaining experimental-release deliverables

These are completion tasks, not reasons to conflate experimental publication with a finished live network:

1. **Resolve publication rights with the founder.** There is no inspected code LICENSE or patent permission grant. Select code licensing and explicit patent treatment, retain authorship, and inventory dependency/model/experiment notices. Apache-licensed model weights do not grant rights to the Begin protocol patent. This audit cannot choose or infer those permissions.
2. **Complete one coherent bounded synthetic goal walkthrough.** Starting from the downloaded installed runtime, show formation/representation, selected-candidate discovery, voluntary proposal/authorization, permitted full-request opening, bounded useful computation or human/agent response, signed acknowledgment/receipt, disconnection/later retrieval, and expiry. Preserve no-match, decline/revocation, replay, resource-limit and wrong-recipient failures. This may honestly use known synthetic candidates and experimental matching; it must not claim full P2. Existing component tests are useful evidence but not a substitute for this requested exchange.
3. **Reconcile current-state release documentation.** Historical completion audit entries and dated evidence must remain history, while entrypoint docs accurately identify implemented versus proposed mechanisms. For example, `signing-profile.md` still lists delegation/revocation distribution as future work despite a newer opt-in implementation; private-discovery planning describes proposed paths beside actual MPyC results. Make the implemented profiles and unimplemented targets easy to distinguish. The roadmap's remote-acquisition item now has evidence and should be updated without rewriting old snapshots.
4. **Prepare a concrete, reviewable release candidate.** Build and inspect package contents, document the supported clean install and one-command synthetic walkthrough, run current CI at the actual candidate commit, collect artifact hashes/dependency notices, validate all linked/index artifacts, and perform a scoped secret/private-source/private-data audit including history. Existing read-only legacy references must not be copied into publication. No completed secret/history audit was inspected here.
5. **Attach a requirement-level experimental release checklist.** Map every minimum packet item and user-requested test to exact commands/artifacts and named limits; mark P1–E4 partial rather than uniformly passed. An external security assessment can be listed as pending for an experimental release; it must precede stronger security claims, not be silently implied by internal agent review.

The founder explicitly requested private development first; public visibility remains a separate founder decision after a concrete candidate is ready. Resolving a license does not itself authorize changing visibility.

## Required before stronger network claims or personal data

These remain real design requirements, even if the founder chooses to publish early experiments: complete candidate discovery without leaking protected membership; reviewed conditional key release; adaptive probing/inversion/collusion analysis and controls; freshness/stop-access enforcement across delayed work; secure authenticated cross-host transport; independent full-policy interoperability; crash/retry recovery with external side effects; larger independently labeled and calibrated semantic evaluation; consent integration across the intention and discovery layers; honest operational monitoring and sustainability. Current local demos and passive honest-majority MPC cannot prove these.

## Optional extensions rather than minimum experimental packet blockers

Native iPad/mobile packaging, MCP or other agent-host adapters beyond the current Python runner, additional embeddings, MASCOT/TenSEAL comparison, high-scale nearest-neighbor search, federation of live operators, distributed financial settlement, reputation/rewards, voting, and arbitrary remote-code execution can follow explicit scope and additional gates. They are not silently promised by the current runner. The early repository should expose interfaces and unsupported status rather than introduce a mandatory central service to simulate completeness.

The current repository has substantial measurable experimental foundations. Rights, a coherent useful goal walkthrough, documentation reconciliation, and candidate packaging/audit evidence remain before this audit could support a complete publishable experimental release. Full live deployment remains a separate, larger verification scope.

## Subsequent candidate reconciliation

The baseline audit above is historical. Subsequent work adds exact-byte signed index bootstrap with pinned publisher keys, freshness and contract checks; a coherent synthetic goal exchange; three-process bounded execution and delayed mailbox result verification; task, grant and result schemas; hash-locked core dependencies; SECURITY and licensing-decision documents; and source/wheel packaging. The core suite now has 120 tests. Source distribution includes the protocol documents, index, demonstrations and experiment sources; the wheel includes runtime and all five schemas. Build hashes are in `package-build-evidence.json`. These local artifacts are not published releases.

Gitleaks 8.30.1 scanned all six existing commits and the candidate staged changes with redaction. Three historical generic-key findings were independently verified as SHA256 values of pinned public MiniLM tokenizer files. `.gitleaksignore` permits only those exact historical fingerprints; rescans reported no remaining findings. This automated scope is evidence, not proof of absence of secrets or a legal review. Core dependency audit reports no known advisories in the updated lock.

Licensing and patent grants remain undecided. Full private discovery, malicious-secure computation, independently administered transport and live personal-data safety remain unsupported. The repository stays private pending founder decisions.

### Source-release repair

Testing the built source archive exposed omitted files: the agent manifest, contribution/discovery documents, Node interoperability helper and matching JSON fixture were not all included by the original manifest. The manifest now includes them. An extracted repaired source archive, using a noneditable installed wheel on Python 3.12.13, passed all 121 tests, capability reporting and the actual three-process goal. CI now repeats the unpacked-source check to catch missing fixtures even when checkout tests pass. This is source-package completeness evidence, not bit-for-bit build reproducibility.
