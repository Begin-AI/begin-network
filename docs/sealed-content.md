# Experimental sealed content

`sealed.py` encrypts a payload for a pinned recipient encryption key using ephemeral X25519 agreement, HKDF-SHA256 and AES-256-GCM. Associated data binds request ID and audience. A SHA-256 digest of the exact restricted box representation is carried in the signed request and checked before decryption; substitution of another valid ciphertext is rejected. Tests cover tampering, wrong key/context, missing match, revoked permission and expiry. The direct-grant API requires already-verified envelope inputs.

This composition is experimental and needs independent cryptographic review. It is not HPKE, not a private matching protocol, and provides no forward secrecy against later compromise of the recipient static private key. The recipient already holds the decryption key; checks in `open_authorized` are application enforcement, not cryptographic prevention against a malicious recipient who bypasses the API. Do not confuse this with the brief's unresolved conditional key-release requirement. There is no approved live personal-data mode.

Before live use, bind encrypted content digests and method-specific match transcripts into signed authorization, specify a reviewed key-release mechanism and collusion model, protect key custody, and verify revocation freshness. Encryption does not hide endpoints, sizes, timing, or existence of matches.
