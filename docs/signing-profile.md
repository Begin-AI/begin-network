# Experimental signing profile v1

This reference implements compact JWS with Ed25519 (`alg=EdDSA`, `typ=begin+jws-v1`) using pyca/cryptography. It follows the compact signing-input construction in [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html) and Ed25519 JOSE use in [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037.html). It is not a security audit or full JOSE implementation.

All three segments use unpadded canonical base64url. Only protected headers `alg`, `typ`, `kid` are accepted. The signature covers the exact encoded header/payload bytes; JSON canonicalization is not required for verification. Duplicate JSON keys, nonfinite numbers, unsupported fields and profiles are rejected. The key ID is `ed25519:` plus base64url SHA-256 of the 32 raw public-key bytes; this is a local profile identifier, not a JWK thumbprint or human identity.

Payload fields: `version`, `type` (request/response/grant/revocation), `sender`, `id`, `audience`, integer Unix `issued_at` and `expires_at`, object `body`, and list-of-string `proofs`. Maximum encoded message size is 65536 characters. Maximum lifetime defaults to 3600 seconds; no future clock tolerance is accepted. Clients supply their own trusted key map; embedded keys or a company registry cannot appoint a signer as trusted. Hosts supply current revocation policy. Replay admission is atomic in a persistent SQLite store and occurs only after signature and envelope checks. Store lifecycle and capacity management are host responsibilities.

`verify` proves only the named envelope checks. Separate direct-grant checks bind issuer, subject, audience, purpose, resource, allowed actions, per-request units and expiry. The initial profile rejects subdelegation. Per-request unit ceilings are not cumulative budgets, money accounting, sandboxing or safe execution. Grant inputs must have passed envelope verification. No private data or remote code may be admitted solely because `verify` succeeds.

## Local CLI

`begin-network keygen key.json` creates a new private key file exclusively with mode 0600 on POSIX. It prints public information only. Do not commit generated keys. `begin-network sign --key key.json --payload payload.json` emits a compact token. `begin-network verify --keys trusted.json --token token.txt --audience receiver --replay-db seen.sqlite` performs envelope admission and prints named checks. Repeating admission fails as a replay. Key custody on non-POSIX platforms needs platform-specific protections.

Future work: delegation attenuation, signed revocation distribution and freshness, key rotation proof and policy, request/ciphertext/key-release binding, independent implementation coverage, and an externally reviewed cryptographic profile. Matching vectors are separate from signing keys.

Sealed-content requests additionally carry `body.sealed_digest`, binding the encrypted box to signed content. This field does not grant access or change allowed task scope. See `sealed-content.md`.
