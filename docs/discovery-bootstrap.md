# Replaceable signed discovery bootstrap

The runtime can load an independently selected local index or mirror set, verify its attestation against host-pinned public keys, and select compatible method/node advertisements. No Begin root key or company service is required. This implements bootstrap validation and selection, not live node discovery or service certification.

`begin_network.discovery_index.verify_index` accepts exact index bytes and a compact Begin JWS attestation. `load_mirrors` accepts ordered `(index_path, attestation_path)` pairs and returns the first pair satisfying the same local policy. Invalid/unavailable mirrors do not relax policy. Paths and signer pins are host-selected configuration; never accept trust anchors from the index being verified. Files may be obtained through any separately authorized distribution channel. This module makes no URL requests and never connects to advertised endpoints, avoiding an implicit SSRF fetch path.

## Attestation contract

The envelope uses the existing `begin+jws-v1` Ed25519 profile and `0.1-draft` protocol version. Its `type` is `response`, `proofs` is empty, and its audience is the exact locally expected bootstrap audience. Issued/expiry times are independently checked under the host's maximum age; an expired/future or revoked signer attestation is rejected. The protected body has exactly these fields:

```json
{
  "profile": "begin-index-attestation-v1",
  "index_sha256": "SHA-256 hexadecimal digest of exact distributed bytes",
  "protocol_version": "0.1-draft",
  "generated_at": "exact timestamp string from index"
}
```

Whitespace changes to the index change its digest and require a new attestation. Verification does not canonicalize the distributed index before hashing. It strictly parses JSON and applies the existing public index schema/validator, including prohibited extra fields, duplicate identifiers and endpoint structure checks. The index's version and generation string must match signed metadata. Generation cannot be in the future relative to signature issuance and must fall within the locally selected age bound. Every advertised node must remain unexpired; an expired node rejects that mirror as a whole.

Attestations authenticate the pinned publisher's statement about those bytes. They do not prove a node is available, honest, safe, independently certified, owned by a particular human, or authorized to perform work. Schema-valid descriptions remain untrusted text. An attestation is intentionally reusable during validity; it is not a task execution token. For protection against rollback to an older still-valid index, persist the highest accepted generation time and supply `minimum_generated_at`. The library does not maintain this host state automatically or guarantee a globally latest index.

## Method and node selection

A requested method contract contains exactly `id`, `method_version`, `model`, `dimensions` and `normalization`. Values and primitive types must match the advertised method exactly. The method must be implemented and not merely proposed. Experiment-only methods require explicit `require_runtime=False`; the default accepts runtime methods only. A dynamic or per-session declaration is not permission to compare arbitrary vectors: actual per-session model/shape checks remain mandatory in the matching runtime.

A requested node capability list selects advertisements whose capabilities include all requested values (`discovery`, `mailbox`, `coordination`). No match is a rejection. With no requested method contracts the returned methods are all validated metadata, including experimental/proposed descriptions; callers must not treat this listing as approval to execute them. Returned nodes retain `unverified-advertisement` trust and `authority_granted` is always false. Signing/grant policy for subsequent work is separate.

Example using host-selected files and previously pinned public-key bytes:

```python
from begin_network.discovery_index import load_mirrors

result = load_mirrors(
    [("/chosen/mirror-a/index.json", "/chosen/mirror-a/index.jws"),
     ("/chosen/mirror-b/index.json", "/chosen/mirror-b/index.jws")],
    trusted_keys=host_pinned_public_keys,
    audience="my-client-bootstrap",
    requested_contracts=[{
        "id": "begin/lexical-v1", "method_version": "1",
        "model": "synthetic-v1", "dimensions": "dynamic",
        "normalization": "binary-cosine"
    }],
    minimum_generated_at=host_last_accepted_generation,
)
```

Changing bootstrap providers requires a deliberate host configuration change to paths and accepted publisher keys. The same validation rules then apply to an independent publisher. Key rotation/revocation sources are local policy inputs, not services imposed by this module. Endpoint use still needs separate explicit fetch policy, HTTPS verification, address restrictions, timeouts and size limits.

## Evidence and limits

`tests/test_discovery_bootstrap.py` uses newly generated synthetic signers, synthetic `.example.org` advertisements and local temporary files; it publishes no operating node or static signing key. Eleven tests cover exact-byte binding, pinned/forged/expired/wrong-audience attestations, generation freshness/rollback floor, node expiry, incompatible method/model/dimension/version/normalization, explicit experiment opt-in, schema/private-field failures, mirror failover, independent replacement signer, signer revocation and refusal of URL sources. Run with `.venv/bin/python -m unittest discover -s tests -p test_discovery_bootstrap.py -v`.

The repository's actual seed index still contains zero operating nodes and no attestation from a designated production publisher. Preparing or publishing a real index/signing key is a separate owner-authorized operational step. This feature does not pass private discovery, transport independence or real-world coordination gates by itself.
