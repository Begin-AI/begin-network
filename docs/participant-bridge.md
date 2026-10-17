# Original-runtime participant bridge

Originating vision: Rima Al Shikh · Begin AI. Experimental, synthetic-only, 15 October 2026.

This implementation corrects the separate hosted inbox pilot's architectural drift. MCP tool calls now invoke the original `intentions`, `discovery_index`, `envelope`, `local_discovery`, `sealed` and `coordination` modules. It does not replace those modules with exact-topic database routing. It does not complete the founding brief's P1–E4 gates.

The subsequent [shared candidate index](shared-candidate-index.md) adds an optional unfamiliar-counterpart path. Three separate MPyC nodes compare secret-shared records and release a one-use introduction only on a positive predicate. Fifteen MCP tools now include offering, revoking and contacting through these introductions. The six-process test connects this path to the existing disclosure/reply flow without a counterpart roster or an owner-local query disclosure. Its passive security, visible metadata, local harness scheduling and deployment limits are documented separately. The original path below remains supported.

## Executable path

```text
MCP client A ── participant runner A ── HTTPS ciphertext relay ── participant runner B ── MCP client B
                  private state A         no participant keys       private state B
                        │                                                │
                 independently chosen, signed public index/mirror inputs
```

1. Each runner creates its own signing/encryption identity in a private directory and recovers it after restart. The public address binds the signing key, not a company host or human identity. Key recovery and rotation are unfinished; loss of state loses the identity. A runner operator can read its participant's state and keys. No claim of hardware-backed or phone-local custody is made.
2. The participant creates or edits one integrated intention containing Mirror, Window and Social views, positive balance weights, facts, aspirations, inferences, role, consent, disclosure categories, timing and revision. An operator-selected encoder combines all three views into one matching vector. Complementary task roles remain separate constraints. See `balanced-representation.md`.
3. The runner verifies independently pinned signatures on exact index bytes, tries an alternate local mirror when needed, and chooses a mailbox service advertised there. Index contents confer no participant authority. Transport endpoints and participant keys are separately pinned by the operator; model/tool text cannot replace them. Public indexes contain no private intentions or membership lists.
4. An already pinned counterpart opts into a bounded matching grant. The requester approves sending its representation to that counterpart. The original runtime encrypts and signs the query. An additional encrypted packet hides the query's grant and matching metadata from the relay. The full description stays solely on the requester runner at this point.
5. The counterpart retrieves with signed mailbox authorization, verifies envelope and grant, checks current consent/revision and cumulative peer/intention query budget, decrypts and runs the original owner-local matcher. It returns an encrypted, signed proposal or no-match bound to the original request digest.
6. A positive match alone cannot disclose the request. The counterpart explicitly accepts and issues a separate signed disclosure grant; the requester then explicitly releases the description. The receiver rechecks the matching grant, revision and disclosure scope. Either side can decline. This enforces ordering in honest endpoint code; a compromised endpoint or malicious holder of already released keys remains outside the guarantee.
7. Authorized responses and related follow-ups are signed and sealed. A durable outbox retries identical packets; a transactional receive record prevents duplicate computation and budget charges. Participants acknowledge locally handled inbox messages. Transport acknowledgements follow durable local processing. Out-of-order deliveries are retried after their prerequisites. Expired request/inbox/outbox payloads are logically removed on access, while deduplication tombstones remain. There is no erasure promise for backups or previously learned information.

## Files and boundaries

| File | Responsibility |
| --- | --- |
| `src/begin_network/runtime_bridge.py` | Durable participant identity/state, runtime composition, explicit state transitions, cumulative query admission, encrypted outbox/inbox |
| `src/begin_network/mcp_adapter.py` | Fifteen official-SDK MCP tools bound to one participant; no caller-supplied account identity or state path |
| `src/begin_network/introductions.py` | One-use unfamiliar contact, identity-key binding, withdrawal and integration with existing disclosure grants |
| `src/begin_network/shared_index.py` | Optional private shares, update/admission ledger and verification of conditionally released introductions |
| `src/begin_network/relay_transport.py` | HTTPS blind-relay transport, certificate validation, redirects refused, signed retrieval/acknowledgement |
| `src/begin_network/encoders.py` | Explicit synthetic encoder plus local pinned MiniLM encoder; no model download or arbitrary code from tool arguments |
| `tests/test_runtime_bridge.py` | Integrated original-runtime behavior and rejection cases |
| `tests/test_runtime_mcp.py` | Two real MCP server subprocesses and a third HTTPS relay process, restart and later retrieval |

The protocol packet profile is `begin-participant-packet-v1`. An existing Begin Ed25519 `response` envelope binds profile, recipient, ID, expiry and sealed-box digest. Decrypted content has one strict kind-specific shape: query, proposal, accepted, description, reply or declined. The relay verifies the outer envelope and stores opaque ciphertext. Query and disclosure contents additionally carry the original runtime's independently verified signed requests and grants. This is a new experimental application profile, not a change to the existing JWS signing contract.

## Privacy and decentralization evidence

| Role/property | Current behavior and limit |
| --- | --- |
| Requester runner | Sees its own text, representations, keys and returned content. Must be participant-chosen and trusted. |
| Counterpart runner | Sees the authorized query representation before matching; receives full text only after the two disclosure steps. This is not private matching against that counterpart. |
| Relay | Sees signer/recipient identifiers, timing, sizes, expiry and traffic. Cannot decrypt using its transport key. Membership and unlinkability are not protected. |
| Index publisher | Advertises public methods/services; has no authority over participant keys or disclosure grants. Tests replace its pinned signer and recover from an unavailable mirror. |
| Query budget | Up to three evaluations per pinned peer/intention, persisted across restart and reissued grants. This bounds that oracle; it does not defeat many-key collusion or prove inversion resistance. |
| Candidate discovery | Original owner-local path uses a pinned peer roster. The optional shared-index experiment enumerates unfamiliar candidates through a bounded secret-shared scan; no scalable global nearest-neighbour service or complete protected membership is claimed. |
| Operator independence | Separate participant identities/state and relay process, no shared Begin signing root. Same-machine tests do not demonstrate independent operators, OS isolation or production deployment. |

## Run and measured evidence

Core Python remains 3.9+. The optional client adapter requires Python 3.11+ and the official MCP SDK 2.3.0:

```sh
python3.12 -m venv .venv-client
.venv-client/bin/python -m pip install --require-hashes -r requirements-client.lock
.venv-client/bin/python -m pip install --no-deps .
.venv-client/bin/python -m unittest discover -s tests -v
```

The original integration test generates only temporary synthetic identities, a loopback TLS certificate and explicitly trusted test CA, private participant directories, an attested synthetic index, and a relay database. It uses certificate validation, never `verify=False`. It starts/stops its own processes and deletes the temporary state. That original test transports the initial signed opt-in grant out of band between already pinned peers. A second test now starts with empty peer rosters and obtains its introduction through the three-node shared index; see the separate evidence account above.

Observed on 15 October 2026: the official SDK client successfully discovered tools and invoked identity recovery, intention formation, matching grant, query submission, inbox retrieval, explicit acceptance, disclosure, reply, follow-up and acknowledgement across separate subprocesses. Both participant processes then exited; fresh processes recovered the same identities and pending responses. Six signed encrypted protocol packets traversed the separate HTTPS relay. Early disclosure attempts were rejected.

The same process test also passed with a locally cached MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, all 11 model files checked against the existing benchmark manifest, and local-only loading. The balanced three-perspective preprocessing is identified as `begin/minilm-balanced-intention-v2` / `...;balanced-perspectives-v2`; its semantic quality has not been evaluated. This run proves actual model execution through the bridge, not useful semantic discovery. The older untagged benchmark's measured false matches remain relevant cautions, not accuracy measurements for the new preprocessing.

The default test uses declared two-coordinate fixtures. Optional model testing sets `BEGIN_TEST_ENCODER` to an operator-selected JSON object with `kind=local-minilm`, a local `directory`, and the exact `file_hashes` map before running `test_runtime_mcp.py` in an environment with the pinned embedding dependencies. It does not download models at tool-call time.

## What must come next

1. Move the implemented bounded shared-index scan from local enrollment/query harnesses to authenticated services on independently operated hosts. Add scalable candidate grouping/search and stronger membership protection. A bootstrap service directory is not itself a decentralized semantic index.
2. Evaluate the integrated matching/key-release composition against stronger adversaries, probing, collusion and metadata. The new method uses MPyC passive security and has not passed external security review; the older standalone pairwise predicate remains a separate historical experiment.
3. Bind authenticated remote ChatGPT/Claude principals to their approved participant runners using a maintained authentication stack, then repeat the real-client acceptance test. The current entry point is operator-side stdio and is not remotely accessible. End users must not need a Python installation.
4. Verify separate operators/hosts, alternate relays and index sources, recovery/revocation, representation fidelity, exploration settings and per-application constraints. The current matcher checks role, timing, method/model, vector contract and consent, not every founding-brief constraint.

The old Sites plugin remains a separate connection experiment. These source changes have not migrated that deployment or established live ChatGPT/Claude use of the original protocol. No production node advertisements or real participant data were published.
