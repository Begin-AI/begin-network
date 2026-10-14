# Threat model and private discovery experiments

Status: design and test plan, not a security certification. Scope is the public seed and synthetic reference runtime. No real intentions or private legacy source belong in fixtures. This model must be updated when implementations change.

## Design lineage

[US11711348B2](https://patents.google.com/patent/US11711348B2/en) is the architectural reference: Figure 2 describes device-local agents and gateway nomination; Figure 5 describes coordinator routing, refusal, and retained requests; Figures 6–7 describe request verification and coordinator discovery; Figure 9 describes registered semantic signature methods. The founder's subsequent instruction makes operation fully decentralized: policy and verification remain independent, without a mandatory Begin signer or online approval service. The patent's semantic signatures represent interests/objectives; cryptographic signatures authenticate bytes. Neither similarity nor authenticated bytes alone establishes permission.

## Assets, adversaries, and boundaries

Protect intention text, embeddings, group membership, disclosure keys, signing keys, scoped grants, compute budgets, mailbox content, and honest result provenance. A local owner controls their data and policy. Signing keys identify their holders, not unique humans. Discovery and mailbox operators are separate trust domains; an operator may inspect stored content, lie, censor, replay, or collude. A validly signed requester can still probe, exceed authority, or issue malicious goals. Network observers learn timing and endpoint metadata unless a method explicitly addresses it. A compromised owner device can expose its local plaintext and keys; this runtime cannot promise protection from its own host.

Runtime packages, models, bootstrap indices, peer advertisements, and agent suggestions are untrusted until checked under local policy. Do not install code, fetch arbitrary URLs, grant privileges, or follow instructions solely because a peer signs them. Agent-originated improvements require explicit version adoption.

## Required negative cases

| Threat | Receiver enforcement and evidence |
|---|---|
| Signature substitution or parser disagreement | Versioned protected bytes, explicit algorithm, bounded canonical JSON profile, strict field/types checks, independent verification fixtures; reject modified type, payload, audience, keys, and permission references. |
| Forged authority or confused deputy | Locally trusted grant roots; authenticated subject/audience/purpose/action/resource; parent-child scope attenuation. Test a genuine signature with no authority and substituted grant. |
| Replay, restart, race | Persistent atomic replay/operation state. Race concurrent identical deliveries, restart processes, test duplicates at alternate nodes. Distinguish accepted delivery from completed external effects. |
| Expiry/revocation bypass | Explicit clock semantics and freshness bound; check at key release and execution, not only receipt. Test queued work, offline resumption, child grant and rotated key after revocation. |
| Budget multiplication | Atomic owner-side accounting across concurrent tasks. A signed number is not a resource limiter. Test simultaneous requests and child allocations. |
| Routing loop/amplification | Bound hops, fan-out, bytes, and deadlines; sign immutable request identity; track visited routing scope. Test cyclic and unavailable peer graphs. |
| Mailbox disclosure or exhaustion | Recipient-bound ciphertext, authenticated retrieval, TTL, message/byte quotas, idempotent acknowledgement. Test wrong recipient, oversize payload, quota races, restart and eviction. |
| Index poisoning or SSRF | Public-only strict schema; no automatic fetch from descriptions; explicit local fetch policy, DNS/address checks, HTTPS, redirects/timeouts/size limits. An index is an advertisement, not authority. |
| Private-vector inference | No raw vectors in public indices/logs. Measure per-role transcript, adaptive queries, membership and inversion attacks; encrypting transport alone does not protect from operator. |
| Poisoned representations or deceptive result | Provenance labels, method/model IDs, explicit constraints and willing counterparties; treat a signed result as an attributed claim. Reject incompatible dimensions/revisions and non-finite numbers. |
| Sybil/reputation capture | Extra keys do not prove more humans or contribution. Discovery must preserve newcomer paths; receipts remain contextual, optional, and cannot create debt. |
| Prompt injection or remote-code execution | Goals and responses are data. Reference tasks use a bounded local allowlist; arbitrary execution requires a separately reviewed sandbox and output/resource policy. |

Transport confidentiality is required for remote deployment but does not remove endpoint, timing, or authorized-output leakage. Revocation cannot erase plaintext already disclosed. A mailbox expiry guarantee concerns serving/deleting local retained objects; it cannot guarantee third-party backups were erased. No exactly-once claim covers arbitrary external effects.

## Private matching candidates

These are experiments to compare, not approved network methods. Protecting a query from a server and protecting every owner's vector from every other party are different requirements.

| Candidate | Assumptions and learning | Useful experiment / limit |
|---|---|---|
| Owner-local matching of a deliberately disclosed coarse query | Private owner vector stays local; owner learns query; requester learns permitted outcome; routing reveals coarse scope | Practical decentralized baseline. Explicit consent to query disclosure required. Does not satisfy sealed-query P2. |
| Two-party secure nearest-neighbour search | SANNS gives semi-honest two-party security with defined nearest-neighbour output | Benchmark quantization/recall/latency and transcript volume. Server-held database does not directly model independent owners; malicious inputs, consent and outcome probing remain separate. |
| Homomorphic inner-product evaluation | Operator computes on ciphertext; decryption/key holder sees approved output; parameter and key ownership choices matter | Compare BFV fixed-point vs CKKS approximation on threshold boundaries. A primitive/library does not supply private ranking, consent, or authorized key release. |
| Function-secret-sharing threshold comparison | Requires protocol-specific sharing/preprocessing assumptions and stated collusion model | Test only boolean complementary-fit predicates rather than expose exact scores. Threshold outcomes still support adaptive probing. |
| Single-server private ANN | PANTHER combines PIR, HE, sharing and circuits under its stated model | Evaluate later for large collections. Database ownership, consent and mobile cost require separate treatment. |

Primary sources: [SANNS paper and implementation discussion](https://www.usenix.org/conference/usenixsecurity20/presentation/chen-hao), [Microsoft SEAL source/documentation](https://github.com/microsoft/SEAL), [Funshade authors' paper](https://eprint.iacr.org/2022/1688), [PANTHER authors' paper](https://eprint.iacr.org/2024/1774). No code or security claim is inherited merely by citing these works; inspect implementation licenses independently before reuse.

Dense vectors are sensitive: the [embedding inversion study](https://arxiv.org/abs/2310.06816) demonstrates reconstruction on particular studied models/data. This motivates attack evaluation; it does not predict an identical reconstruction rate for every Begin method.

## Benchmark admission contract

Every candidate must publish method ID/revision, actual implementation dependency versions, input ranges, key/decryption ownership, preprocessing assumptions, adversary and collusion model, and exactly which party learns each output. Capture correctness against plaintext synthetic ground truth, threshold errors, recall/precision, CPU/memory, bytes, latency and offline behavior. Include malformed inputs, repeated/adaptive probes, colluding roles, and unauthorized key-release attempts. Publish residual leakage and failure results. A passing arithmetic benchmark cannot alone pass P2; independent protocol review and key-release enforcement are also required.
