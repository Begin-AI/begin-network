# Signing and permission review

Current disposition: all four concrete findings S1–S4 below were resolved and revalidated on 2026-10-14. Historical reproductions are retained as the review trail; they are not claims about current behavior. Application integration limits remain applicable.

Review date: 2026-10-14. Scope: `src/begin_network/envelope.py` and CLI callers as initially implemented. Dynamic reproductions used the declared `.venv` runtime. This is an adversarial code review, not a cryptographic audit. Findings refer to this reviewed snapshot; fixes require regression evidence and this record must then be annotated rather than treated as current defects forever.

## Concrete findings

### S1: Malformed inputs escape the rejection contract

`decode` does not translate base64 decoder errors; `verify('A.A.A', {}, 'receiver')` raises `binascii.Error`. A validly signed payload with `type: []` raises `TypeError` at set membership. A signed payload containing approximately 1100 nested arrays raises `RecursionError` in `strict_json`; a deeply nested protected header can trigger the parser before authentication. The CLI catches broad exceptions and exits, so these examples do not bypass its verification. A service catching only `Rejected`, however, can return an internal error or terminate its request path.

Fix: normalize decoder/parser/type errors to `Rejected`, check exact primitive types before membership, bound nesting and input bytes, and add regression cases for unauthenticated malformed headers and authenticated malformed bodies. Do not broadly swallow operational/database failures as if they were successful rejection or successful processing.

### S2: JSON profile admits non-finite overflow and incompatible encodings

`strict_json(b'{"v":1e999}')` produces `{'v': inf}` because `parse_constant` handles `NaN`/`Infinity` spellings, not numeric overflow. A payload encoded as UTF-16 with a genuine Ed25519 signature passes `verify`; Python's byte JSON parser autodetects the encoding. This violates a strict interoperable UTF-8 JSON contract and admits values a signer using `allow_nan=False` cannot reproduce.

Fix: explicitly decode UTF-8, reject non-finite floats recursively or use a parse-float hook, bound numeric ranges/precision in the profile, and decide whether floats are permitted at all. Test UTF-16/32, byte-order marks, lone surrogates, overflow exponents and deeply nested objects. This finding concerns parser agreement, not a demonstrated signature forgery: signatures bind the exact encoded segments.

### S3: Grant field types are incomplete

A cryptographically verified grant with `purpose: {}`, `resource: []`, and `delegation_depth: false`, paired with matching malformed request fields, is accepted by `authorize`. Boolean `false` compares equal to integer zero. `purpose`, `resource`, subject and action semantics lack explicit bounded type validation. The string action check in allowed actions prevents some malformed action values, but does not establish the complete contract.

Fix: validate exact grant/task schemas at the authorization boundary (nonempty bounded strings, exact integer depth/max units, bounded actions); reject malformed legitimate signatures. Define whether zero-unit operations are permissible and document purpose/resource identifier semantics. Correct signatures from a trusted issuer must not normalize malformed scope into authority.

## Authority and replay integration constraints

No immediate signature forgery was found. The protected header's fixed algorithm and key-ID binding, duplicate-key rejection, exact top-level field set, signer match, audience and lifetime checks are useful foundations.

`verify` intentionally returns an authenticated envelope even when no grant exists. `authorize` assumes dictionaries already passed verification; it cannot detect forged caller-created dictionaries. The CLI accurately emits `permission_checked: false`. Keep this distinction explicit. Add a safe application entry point that verifies both signed request and signed grant against locally chosen authority, rechecks current time/revocation, performs replay admission, and only then dispatches a bounded action. The request must never choose its own trusted authority. Tests calling `authorize` on already verified dictionaries do not prove a remote service enforces that sequence.

Replay protection is optional in the library, mandatory in the CLI. The SQLite uniqueness constraint provides atomic sender/ID admission and persisted rejection. It does not provide completion/idempotent result retrieval, a global distributed replay ledger, authorization, quotas, or external effect transactions. The store has no expiry/cleanup and a trusted signer can submit distinct IDs indefinitely. Reusing the same grant through replay verification can also reject a valid recurring grant unless grant validation and operation admission are separated. Different recipient databases cannot promise global exactly-once behavior.

Currently replay admission occurs inside `verify`, before separate authorization. An unauthorized but correctly signed operation can consume its own ID, then fail permission checks; retries with repaired proof under that ID remain rejected. This can be a valid immutable-ID policy, but it must be documented. For asynchronous systems, distinguish delivery deduplication from operation execution, persist outcome/state, and define recovery after a crash between admission and action. Test independent SQLite connections racing the same ID, process restart, database contention, quota exhaustion, and failure after admission.

Key revocation is a caller-supplied set and grant revocation another set. Neither is a freshness protocol. Do not claim automatic rotation, network revocation propagation, or stop-access until callers provide an explicit local policy and measured bound. A valid signed `revocation` message has no application effect by itself.

## Claims and evidence boundaries

The module describes verification as fail-closed. The examined malformed inputs are not accepted as valid, but unexpected exception behavior needs fixing before service use. Supported behavior is direct, nondelegable grant scope checking, not atomic budget enforcement, sealed-content release, safe remote execution, or full patent protocol compliance. `docs/protocol.md` still says the signing profile is unresolved and only the index validator executes; update it to describe the exact experimental implementation after contract decisions land.

Next evidence should include an independently implemented verifier consuming a fixed fixture, fresh runtime acquisition by another agent, full application authorization-negative cases, and persistent multi-process replay tests. Two callers of the same `verify` function establish usage, not independent interoperability.

## Follow-up verification

The implementation changed during review. Revalidation confirms base64 decoder errors and signed `type: []` now produce `Rejected`. Source now explicitly decodes UTF-8 and catches JSON recursion, resolving those reported paths; delegation depth now requires exact integer zero, resolving boolean depth acceptance. Numeric overflow (`strict_json(b'{"v":1e999}')`) still returns infinity. Purpose/resource exact type validation remains unfinished. Replay/application integration limits above remain design requirements, not signature forgeries.

### S4: Sealed attachment substitution — confirmed

New `sealed.py` binds AEAD to request ID and audience, but `open_authorized` receives the box separately from the signed request and does not verify any signed digest of that box. An attacker who knows the recipient encryption public key and request context can create a fresh box containing arbitrary replacement plaintext, reuse an unchanged genuine signed/authorized request and grant, and have `open_authorized(..., matched=True)` return the replacement. Dynamic reproduction returned `b'attacker replacement'` after both request and grant had passed signature verification.

This is content-authorship substitution, not AES-GCM breakage: public-key encryption lets anyone create ciphertext for the recipient. AEAD integrity authenticates the encryption context/key, not the authorized requester's signing key. Fix by binding the entire box or a canonical cryptographic box digest into the signed request, and checking it before decryption. Include all box profile/ephemeral/nonce/ciphertext fields in that binding. Add substitution regression tests with identical ID/audience, a second encryptor, and unchanged signed request. Update the request schema deliberately rather than accepting an unsigned external attachment by convention.

The module correctly states that key holders can bypass application match/permission checks and that this composition is experimental. Preserve those limits after fixing substitution.


## Final revalidation — S1–S4 resolved

After the latest fixes, `.venv/bin/python -m unittest discover -s tests -v` passed all 42 tests (2026-10-14). The current parser normalizes the reported malformed inputs to `Rejected`, explicitly requires UTF-8, and rejects non-finite numeric overflow using a finite `parse_float` hook. A separate direct reproduction of `strict_json(b'{"v":1e999}')` now raises `Rejected`. Grant purpose/resource/subject and request action/purpose/resource now require nonempty strings, with exact integer delegation depth.

The request body now carries `sealed_digest` inside signed content. `open_authorized` compares that digest against the complete canonical box before decryption. `test_attacker_cannot_substitute_ciphertext` passes, along with authorized round-trip, tamper, wrong-key/context, match and revocation tests. The S4 attack path is resolved under the existing precondition that the request and grant were independently authenticated; an attacker cannot alter the signed digest.

All concrete defects found in this scoped review are resolved. This evidence does not establish production cryptographic assurance, private semantic matching, automatic network revocation, atomic budgets, or arbitrary remote-execution safety. The replay and authority integration constraints documented above remain release/application requirements.
