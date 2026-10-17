# Minimum private discovery experiment

Historical method proposal. The current implementation uses one balanced Mirror–Window–Social vector per intention, described in `balanced-representation.md`; the separate component calculations below are research alternatives, not independent intention categories.


Status: research plan with separate implemented owner-local, MPyC predicate and repeated-boolean probing experiments; not an approved private matcher. Only synthetic intentions may be used. See `local-discovery.md`, `mpc-evaluation.md` and `probing-evaluation.md` for actual measured mechanisms; the MASCOT/TenSEAL paths below remain proposals. This plan preserves the brief's sealed discovery and permission boundaries; it does not turn purpose-bound intentions into public vectors.

## Recommendation

Build two comparable paths: **owner-local matching behind encrypted mailboxes**, then **two-party private boolean matching using MP-SPDZ MASCOT**. Use TenSEAL encrypted dot products as an explicitly leaky performance comparator, not the final discovery protocol. Local matching is the shortest route to testing decentralized coordination today; the MPC path is the better minimum test of protecting both parties' representations before disclosure.

This follows [US11711348B2](https://patents.google.com/patent/US11711348B2/en), Figures 2, 5 and 9: agents retain their data, coordinators route requests, and versioned semantic methods determine relevance. The founding brief adds sealed requests, explicit mutual willingness and authorization. None of the experiments require a mandatory Begin coordinator or signing authority.

## Experimental topology and information contract

Run requester R, participant P, and forwarding/mailbox nodes N1/N2 as separate processes with separate keys and state directories. A same-machine run tests separation and transcript logic; a later two-host run tests transport and independent administration. Public index entries contain service/method metadata only. No participant vectors, private membership lists or plaintext requests go into the index.

Use a synthetic candidate roster pinned locally for this first experiment. Declare this bootstrap limitation: encrypted forwarding to already known recipients is not yet private global candidate discovery. Coarse public service capabilities must be volunteered and cannot silently encode a person's private interests. A publishable discovery method needs a separate account of how candidate enumeration avoids revealing protected group membership.

| Path | R learns | P learns | N1/N2 learn |
|---|---|---|---|
| Owner-local | Permitted boolean outcome, optional consensual introduction | Authorized query representation and explicitly disclosed coarse constraints; private request text remains sealed | Pseudonymous destination/session, timing, lengths, method ID if routed openly, delivery outcome |
| Two-party MPC | Agreed boolean predicate only | Agreed boolean predicate only | Rendezvous/session and traffic metadata if involved; no plaintext input from the intended transcript |
| TenSEAL comparator | Dot-product scores; these can reveal P's vector under probing | Ciphertext of R's vector and public evaluation context | Metadata and encrypted payloads; never the decryption secret |

“Node sees only sealed query” is a content statement. It does not claim hidden recipients, traffic, membership, timing or unlinkability. Collusion N+P in the local path exposes the authorized query to N. Collusion R+P exposes both inputs. No endpoint compromise protection is promised.

## Path A: owner-local execution

1. R encodes mirror/window/social representations locally under an exact method/model revision. Create an independent sealed description for later disclosure. Issue a signed, expiring match request binding the encrypted query digest, method ID, request/session ID, destination and permission evidence.
2. Encrypt the minimum query representation to P's pinned encryption key. It includes role and allowed matching fields, not the full description. R's policy must explicitly authorize this representation disclosure to P; matching has not yet happened.
3. N1 forwards to N2, which retains ciphertext while P is offline. P later verifies signature, audience, freshness, replay and direct grant before opening the authorized matching input. This pre-match authorization must not reuse the later task disclosure API's `matched=True` precondition; define a distinct bounded `match` action.
4. P compares against its locally held purpose-specific representation, enforces hard constraints, and signs a boolean proposal or no-match result. Return the result encrypted to R.
5. Positive similarity alone releases no full request. Both parties' existing delegations or explicit approval authorize the next disclosure, whose ciphertext digest is bound to the signed request. Decline, expiry and revocation remain terminal outcomes.

This path protects representations from forwarding operators under the stated endpoint assumptions. P necessarily learns the disclosed query; it therefore does not meet the brief's strongest interpretation of private matching against an untrusted potential counterpart. Record that limitation rather than marking full P2 passed.

## Path B: two-party secure boolean matching

Use [MP-SPDZ's maintained protocol framework](https://github.com/data61/MP-SPDZ) and [official getting-started/security-model documentation](https://mp-spdz.readthedocs.io/en/latest/readme.html). MASCOT supports malicious security with dishonest majority and has a documented two-party tutorial. The documentation explicitly says implemented protocols do not imply production software security review. Dependencies include a C++ toolchain, Python, GMP, libsodium, OpenSSL, Boost and patched libOTe; use a pinned release/commit and dependency hashes. Linux is the first reproducibility target; source builds and containers are documented. Do not use insecure preprocessing or `-DINSECURE` benchmark mode as security evidence.

Compile a fixed, reviewed circuit, not requester-supplied executable code. P0 inputs R's quantized vector and role/constraint fields; P1 inputs P's values. Compute three separately weighted mirror/window/social dot products, agreed complementary-role tests, hard constraint compatibility and the public threshold. Reveal only the final boolean to the agreed parties. For the minimum circuit, use signed integer coordinates bounded to ±1000, dimension 32 per representation and nonnegative public weights totaling at most 100; bound every intermediate below the chosen signed range. Validate secret coordinate ranges inside the circuit; host checks alone do not constrain malicious inputs. Quantization must be included in utility measurements. More dimensions and model-generated dense vectors follow after correctness.

Independent owners run their party processes with authenticated channels and locally approved circuit hash, method revision and session metadata. Begin signatures authenticate the agreed session outside MPC. Bind the signed result to the session/circuit/input commitments where supported; without such a binding, do not claim a transferable proof that a result came from the specified computation. A participant can choose deceptive but well-formed input or abort. Malicious-protocol security does not establish truthful intentions, fairness, guaranteed completion or resistance to many-key probing.

The minimum circuit handles a single candidate pair. Multi-owner search, private candidate selection and oblivious ranking remain explicit follow-up work. Avoid a central service collecting all plaintext vectors to simplify implementation.

## Optional encrypted-score comparator

[TenSEAL](https://github.com/OpenMined/TenSEAL) provides Python tensor operations over Microsoft SEAL, including encrypted vector dot products and serialization. [PyPI](https://pypi.org/project/tenseal/) currently reports `0.3.18`, Python ≥3.11, with Apple Silicon/macOS 14 and Linux wheels among its distributions; availability was checked 2026-10-14. Pin the wheel hash and dependency versions in a separate environment, not the core runtime requirements. An installation target is `python3.11 -m pip install tenseal==0.3.18`; record actual platform/wheel rather than assume installation succeeds everywhere. The package is Apache-2.0; inspect its bundled dependency notices too.

R retains the CKKS secret key and sends only a public evaluation context plus encrypted normalized query to P. P evaluates encrypted-query/plain-owner-vector dot product and returns ciphertext. R decrypts the score. Check that serialized public context has no secret key. Parameters and approximation error need explicit measurement; adopt the library example only as an initial experiment, not a reviewed security parameter selection. R must never offer an unrestricted ciphertext decryption oracle.

This does not hide P's vector against a probing R: basis-vector queries reveal coordinates through exact scores, and approximate scores can still reveal useful information. The experiment should demonstrate that attack deliberately. Restricting output to a boolean requires a further secure comparison protocol; discarding the score in an honest client is not cryptographic output restriction. Homomorphic encryption alone does not certify P performed honest evaluation.

## Exact test and reporting protocol

Use a versioned corpus of synthetic goals with gold complementary-role/constraint labels, separate facts/aspirations/inferences, optional social opportunity, refusal cases, multilingual paraphrases, negation, newcomer needs and no contribution history. Run each cryptographic path on the same representation fixture so utility and privacy changes are separable from encoder changes.

For every pair and path record plaintext baseline predicate, experimental predicate, elapsed cold/warm time, peak RSS, transmitted bytes, party count, dependencies, method/circuit hash and the observed per-role transcript. Include threshold boundary ±1 quantization unit, incompatible revision/dimension, wrong role, insufficient budget, expired grant, no human approval, no match, declined participation and negative resource constraints. Require zero predicate disagreement outside a declared approximation boundary; publish all inside-boundary failures.

Adversarial tests: tamper signed digest, replace ciphertext, wrong recipient, replay after restart, offline expiry, revoked matching permission, cyclic routing, quota exhaustion and node failover. For MPC, add malformed input/range, wrong circuit/session, altered party transcript and abort; record whether rejection occurs and what the other party learns. For TenSEAL, include basis-vector reconstruction and report its leakage as an expected failure of owner privacy. For owner-local, demonstrate a node cannot decrypt while P can; do not confuse this with hiding the input from P. Repeated boolean outcomes permit adaptive inference even in MPC; record query budgets per local principal and demonstrate their many-key limitations.

Acceptance is an honest experimental report and reproducible scripts with stated privacy scope, not P2 certification. Full P2 still requires a complete candidate-discovery transcript, consent/key-release enforcement, adaptive probing controls, collusion analysis and independent review. Full embedding quality also requires a real versioned encoder benchmark: success on a 32-dimensional synthetic circuit proves arithmetic and constraints, not semantic understanding.
