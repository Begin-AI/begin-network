# Independent bounded execution review

Executed adversarial probes with the repository `.venv/bin/python` on 2026-10-14. This is an internal independent-agent review, not security certification. Historical pre-binding-repair execution snapshot SHA-256: `5a6025b858159699bb92c7bb9cf01c5c6866be6fe8107095f1c8c1566bcdd0f7`. The runtime was being developed concurrently. Both binding findings below were subsequently repaired and independently retested; historical and current evidence are distinguished. No implementation edits were made by this reviewer.

## Independent repair verification

Retested current `execution.py` SHA-256: `64961058f74b316c9758b26009941233e5c57ae994df17f9f3d5b893864ede4e`.

The receiver now requires a locally pinned `requester_keys` map and `expected_grant_tokens`. It verifies the original request's signature, requires its audience to equal the response signer and its sender to equal the receiving audience, and compares exact grant-token hashes before replay admission/decryption.

Executed retest outcomes:

| Case | Current outcome |
| --- | --- |
| Intended worker, correct caller-known grant digest | Accepted `{'slots': [[1,2]]}` |
| Other trusted worker, otherwise valid result | `Rejected: sender/audience mismatch` |
| Intended worker with syntactically valid wrong all-zero grant hash | `Rejected: response does not reference expected grant chain` |
| Non-list grant hashes | `Rejected: invalid grant provenance` |
| Missing revision or list-valued provenance | `Rejected: unsupported result provenance` |

The hash-binding probe used a locally known fixture grant-token string for digest comparison, not a claim that receipt verification independently authorizes that grant. Real execution probes below used signed grants and the ledger. The result receiver verifies correspondence to caller-known token bytes; ledger verification remains responsible for whether those grants authorize execution. These repairs do not prove truthful computation by an intended malicious worker.

## Historical binding findings — resolved

`receive_result` authenticates a signer in the supplied `worker_keys` map and binds the response to the original request token's digest, but does not require that signer to be the worker named by the request audience. An unrelated locally trusted worker can therefore provide a valid signed, requester-encrypted result for that request. This is a result-authorship binding bug when the trust map contains multiple workers, not a break of Ed25519 or AES-GCM.

Executed reproduction constructed:

1. Requester R, intended worker W, and another worker X with independent signing keys.
2. A signed request with `audience=W`, and digest H of its exact token bytes.
3. An output box encrypted using R's public encryption key, associated with request ID H and audience R. Encryption uses only a public recipient key; it does not establish W's authority.
4. A response signed by X, addressed to R, with response ID and request digest H, correct profile/method, syntactically valid provenance, sealed-box digest, and `grant_digests=['0'*64]`.
5. `receive_result(..., worker_keys={W:W_public,X:X_public}, audience=R, request_token=original, ...)`.

Observed: accepted output `{'slots': [[1,2]]}` and returned `synthetic-calculation` provenance. Signing by X cannot alter the request digest, but the receiver never compares X to W. Corrective contract: derive or independently pin the expected worker from the caller's locally known request and enforce exact signer/audience binding before opening.

The syntactically valid all-zero grant hash was also accepted. Format validation is present, but actual grant tokens/hashes are not passed to the receiver for comparison. This means the returned grant-provenance list is a worker assertion, not evidence matching the caller's authorization chain. If the result claims the agreed grants, compare exact caller-known chain digests. Neither binding establishes truthful execution by a malicious intended worker; independent recomputation or stronger attestation would be separate evidence.

## Negative validation probes that passed

- `provenance=[]` rejected with `unsupported result provenance`.
- Missing `resource_revision` rejected with the same error.
- Dictionary-valued `grant_digests` rejected with `invalid grant provenance`.
- Input slots use exact integer times, reject Boolean values, out-of-range minutes, overlapping intervals, and more than 32 input slots.
- Two valid 32-slot schedules can produce **63** intersection fragments. Executed `left=[[2*i,2*i+2] for i in range(32)]`, `right=[[2*i+1,2*i+3] for i in range(32)]`; `intersections` produced 63 slots, and `_slots(output,max_count=63)` accepted them. The inspected receiver applies the 63-slot output bound, avoiding confusion with the smaller input bound.

The output cardinality check verifies format, not correctness: a signed worker could still return different valid intervals. A provenance label is an authenticated assertion, not proof of arithmetic or human input truth.

## Replay, budgets, and crash-state observations

Executed a real `PermissionLedger` and `FixtureWorker` with three independent keys, signed current-fixture revocation snapshot, one root grant, receiver-pinned encryption keys, and a synthetic calendar resource. Results:

| Probe | Observed outcome |
| --- | --- |
| Valid request then identical request | `completed`, duplicate flag true; returned token exactly matched first result |
| Invalid decrypted empty input slots | Rejected after reservation; execution state `failed` |
| Retry invalid admitted request | `failed`, duplicate true, no token or box |
| Ledger expenditure after one success plus one malformed input | 2 reserved units |
| Simulated crash by calling `ledger.reserve` before any execution record | Later execute returned `pending-or-interrupted`, duplicate true, no token or box |

These are conservative at-most-once admission semantics. Reservations persist, are not automatically refunded, and duplicates do not repeat work. The reserve/execution-record gap does not provide guaranteed completion or automatic recovery. An operator must resolve interrupted state with a separately defined policy rather than blindly rerun. Returning a cached completed result also still depends on successful current ledger authorization/revocation checks.

The worker rejects arbitrary resource paths and operations: only host-registered `fixture:` resources marked synthetic and the fixed interval operation are accepted. Optional signed task metadata (`sealed_digest`, `routing`) is validated separately from core purpose/action/resource/units scope. It does not widen permitted action or resource. The requester selects input data, not worker implementation, encryption pins, or resource registry.

## Remaining limits rather than additional proven bugs

The registered fixtures and signing/encryption pins are trusted host policy. Database or private-key compromise is outside this test. Requester encryption keys are pinned locally; possession of a signing key does not automatically establish an encryption identity. The owner must authenticate that mapping independently.

A completed response is a worker-signed statement plus encrypted output, not a transferable proof that the worker used the stated fixture or grant. Encryption hides output from parties without the recipient key, not from the sender or a compromised authorized recipient. Receiving result format and signature checks do not grant downstream action rights.

The bounded operation is deterministic synthetic scheduling, not arbitrary remote code execution, filesystem access, external calendar modification, payments, or sandboxed tooling. No claim of exactly-once external effects, rollback, distributed budget settlement, public transport security, or production crash recovery follows from it.
