# Independent experimental candidate audit

Audit date: 2026-10-14. Inspected commit: `cc2b30cf13d5d1bf4a357eecb7e06be8f3816f5c`, with subsequent packaging repair at `117afaf` explicitly inspected during the audit. This is a requirement audit, not an external security certification or authorization to publish. No implementation files were changed by this reviewer.

## Finding

The minimum **experimental source packet** in the founding brief is present, runnable and honestly labeled. An actual source-distribution failure was found during candidate validation: its omitted fixture/helper files prevented the advertised test packet from running. The repair was then independently inspected; no unresolved core runtime failure remains in the checked working tree. There are still candidate packaging/evidence closeout tasks and owner decisions before describing an exact artifact as ready for publication. This conclusion does not assert the full decentralized network, all rollout steps or P1–E4 are complete.

The brief explicitly allows methods, specifications and synthetic demonstrations to publish early. Its later private-discovery, independent-host and live-participation gates remain substantive requirements; permission to publish experiments must not turn those missing guarantees into passed gates.

## Independently observed checks

Executed against the current working tree with bytecode writes disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 .venv/bin/begin-network capabilities
PYTHONDONTWRITEBYTECODE=1 .venv/bin/begin-network validate-index discovery/index.json
```

Observed **121 core tests passing** in 2.656 seconds on Python 3.9.6/macOS. Capabilities reported local CLI/Python execution, synthetic-only data, bounded fixture operation, no granted authority, no personal-data support and no secure public transport. Index validation reported **five methods and zero nodes**. The core suite executes real loopback process scenarios and cross-language signature checks; it does not rerun learned-model inference or the optional MPC protocol.

Read live GitHub run state using `gh run view 38516451571 --repo Begin-AI/begin-network --json status,conclusion,jobs`. At audit completion, [run 38516451571](https://github.com/Begin-AI/begin-network/actions/runs/38516451571) at the audited commit had **success** for both jobs. The core job installed the locked dependencies/noneditable package, ran tests, index validation and the synthetic goal. The MPC job installed the pinned experiment, ran preflight tests and the actual three-party computation. This is current remote CI evidence rather than a forecast based on an older run.

## Minimum packet and explicit user tests

| Requirement | Inspected evidence and actual scope |
|---|---|
| README and agent manifest | Present; implemented/unsupported lists, synthetic data policy and no-authority declaration. Current local capability command independently checked. |
| Charter and versioned protocol/schema | Charter, protocol, signing profile and five published/packaged schemas. Schema tests generate actual bounded task, attenuated grants and signed result bodies. Normative full state-machine targets remain broader than the runtime. |
| Embedding methods/private-matching specification | Distinct lexical/concept baselines, pinned pretrained experiment and frozen results, owner-local encrypted method, signed-session MPyC experiment and leakage research plan. Five learned false positives and one false negative explicitly retained. Testing information retention has evidence; universal semantic correctness does not. |
| Validator and runner/adapter | Installed CLI plus Python APIs and capability reporting. Built-in interval operation accepts bounded synthetic data, not downloaded executable task code. |
| Synthetic demo and failure fixtures | Actual goal exchange and three-process goal tests pass. Formation/discovery, voluntary decline/no-match, authorization, sealed opening, useful interval output, signed provenance, retry, offline mailbox retrieval, expiry and negative paths are inspectable. |
| Bootstrap and mailbox | Signed exact-byte mirror selection under replaceable locally pinned publisher policy; persistent recipient mailbox and quotas. No central Begin root, no implicit network fetch and no live service claim. |
| Activity definition and contribution guide | Present; zero operating nodes, optional contextual contribution, explicit method adoption and no claimed population/reputation counts. |
| Agent acquires runtime and produces/verifies signatures | Earlier exact-commit GitHub acquisition plus fresh candidate installation evidence. Candidate agent fetched `db98de18...`, used locked dependencies/noneditable installed wheel, ran 120 tests and CLI tamper/audience/replay checks. This is a separate agent on the shared host, not two independently administered agent products. |
| Coordinators coordinate and goals complete | Current core tests cover independent OS processes/keys/state, signed routing, unavailable-peer failover and bounded worker result return. Output is genuinely computed by the fixture worker; PIDs/accounting are local instrumentation, not remote attestation. |
| Different mechanisms tested with honest limits | Actual plaintext/learned/local-owner/MPC experiments exist. MPyC opens a boolean only to selected recipients under passive honest-majority assumptions; it does not establish malicious security or private global candidate enumeration. |
| Publication hygiene | Secret/history and known-advisory records, separate model acquisition, dependency inventory, SECURITY and pending license decision are present. Scoped automated scans do not prove absence of secrets or establish legal clearance. |

The architecture consistently refers to the patent's local agents, coordinator routing, vector-method contracts and independently chosen verification. Semantic signatures remain separate from cryptographic authorship. No mandatory company signer was found in the examined fixtures or interfaces. This is architectural alignment evidence, not a legal patent-claim coverage analysis.

## Concrete technical closeout before freezing the experimental artifact

1. **Complete remote validation of the repaired source packet.** Candidate validation actually failed because `examples/matching_cases.json` was missing from the source distribution, alongside the earlier manifest/helper omissions. The repair now includes example JSON, test Python/Node helpers, agent manifest, contribution guide and discovery Markdown. This reviewer independently opened `/tmp/begin-release-final/begin_network-0.1.0.dev0.tar.gz`, verified SHA-256 `332601e35bf2f6356a756f376d7daf342a93998b04b1b667028869c602646d59`, counted 129 members and confirmed the previously missing files. Parent-produced `package-build-evidence.json` records 121 passing extracted-source tests and an installed-wheel real process goal; that execution was reported by the parent rather than rerun by this read-only reviewer. New CI now tests the unpacked archive. Its actual candidate run must pass before treating the packaging closeout as complete; older checkout-only green CI would not catch these omissions.
2. **Reconcile current candidate evidence.** The checklist was updated during this audit to record 121 tests, successful cc2b30c CI, the repaired source archive and the still-required new packaging CI. Preserve that named-commit distinction. The independently downloaded candidate is `db98de18...`; the diff to `cc2b30c` includes a new CLI capabilities implementation/test and documentation. Prior signature/goal evidence remains valid for its named commit, but do not imply that consumer installed every subsequent change. Either perform the narrow current capability acquisition check or explicitly state that the later capability command has current local/Linux installed-package evidence while prior full acquisition is at the named earlier commit.
3. **Use a precise release readiness statement.** Historical audits correctly preserve formerly incomplete steps, with subsequent reconciliation. Entry points should link the final requirement ledger/current candidate evidence, so a reader does not mistake historical “not implemented” statements for present state or green experiments for full network completion. The current README is appropriately cautious; keep it so.

These are artifact/evidence closeout tasks. They do not justify silently replacing the user's goal with documentation alone, and they do not require implementing every future production extension before experimental source can be published.

## Owner/operator decisions, separate from technical defects

Code/documentation licensing, patent treatment, contributor terms and final attribution/NOTICE remain unresolved. Public GitHub visibility was explicitly reserved for the founder. Those are required publication decisions, not bugs to bypass by inserting an inferred license.

`SECURITY.md` also explicitly requires choosing a public reporting contact and supported-version policy before publication. Set a real owner-selected channel and a narrowly accurate experimental support policy; do not invent a security address or response guarantee. This is an operational publication decision, distinct from proving production security.

## Remaining broader requirements — not passed

Two independent supported agent hosts with revocable bounded tasks; private candidate discovery without exposed membership; conditional authorized key release; inversion/probing/collusion evaluation; authenticated secure cross-host transport; independent complete-policy interoperability; robust crash/recovery behavior for external side effects; larger independently labeled semantic calibration and multilingual evaluation; and opt-in real human useful connections remain incomplete. Known-candidate owner-local matching and passive MPC are useful partial mechanisms, not substitutes for these requirements.

No P1–E4 gate or entire rollout is marked passed here. Native iPad execution, unrestricted remote-code execution, payments/voting/reputation and live node federation are not secretly supplied by the current CLI. Publishing an honest experimental seed and declaring the entire active network goal achieved are different claims; the present evidence supports the former only after the closeout and owner decisions above.

## Subsequent remote packaging closeout

The primary agent queried [run 38516650751](https://github.com/Begin-AI/begin-network/actions/runs/38516650751) at `117afaf39b06c96c656c3a454b8d3da85b430b29`: completed **success** for core/source-release validation and MPC. The source-release job builds wheel/source, inspects required packet files, runs all 121 tests from the extracted source archive against the noneditable installed runtime, and executes the three-process goal. This resolves closeout item 1. The separately acquired db98de1 trial remains tied to its exact commit; current capabilities have local installed-wheel and fresh Linux cc2b30c/117afaf evidence rather than a claim that the older consumer installed later changes. Owner decisions and unpassed broader gates remain unchanged.
