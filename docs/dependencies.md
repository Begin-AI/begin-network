# Dependency and attribution inventory

This is a dependency inventory, not a legal clearance certificate or a license grant. The final release must reconcile its chosen project license with these upstream terms. Packages and weights are downloaded separately; this repository does not vendor their implementations or model weights.

| Component | Use | Upstream terms/source |
|---|---|---|
| Python | Runtime, tests and experiment drivers | Python Software Foundation license; python.org |
| jsonschema 4.x | Public artifact schema validation | MIT; python-jsonschema/jsonschema |
| jsonschema format-nongpl extras and transitive packages | URI/date-time validation | Each installed distribution's own notices; the nongpl extra avoids selecting GPL format packages |
| cryptography 50.0.2+ (below 51) | Ed25519, X25519, HKDF and AES-GCM | Dual Apache-2.0/BSD-3-Clause; pyca/cryptography. Binary wheels also carry bundled dependency notices |
| Node.js built-in crypto | Independent signature interoperability harness | Node.js and bundled OpenSSL notices; no npm package dependency |
| MPyC 0.11 | Optional three-party private predicate experiment | MIT; lschoe/mpyc. Exact wheel hash in experiments/mpc/requirements.txt |
| Sentence Transformers / Transformers / Hugging Face Hub | Optional learned-embedding benchmark | Upstream Apache-2.0 packages; exact installed versions in experiments/embeddings/requirements.lock |
| all-MiniLM-L6-v2 weights | Optional pinned 384-dimensional encoder | Model card lists Apache-2.0; revision and downloaded-file hashes are recorded. No weights redistributed |
| PyTorch / NumPy and experiment transitive dependencies | Optional CPU inference | Upstream distribution notices apply; version freeze records actual environment, not a full supply-chain hash lock |
| GitHub Actions | CI services and action scripts | Upstream action repositories' licenses; not vendored into the runtime |

Core dependencies are declared in pyproject.toml and a universal Python-version-aware hash lock is recorded in requirements.lock; the experiment dependency sets are separate so installing the signing/verification runtime does not download a model or MPC package. Exact version ranges are development constraints, not a promise every future allowed wheel is audited. A release candidate needs a reproducible dependency snapshot, vulnerability review and artifact inventory for its supported platforms.

The repository's architectural references include Rima Al Shikh's patent, the supplied founding brief and prior Begin systems. No private legacy source was ported. Preserve attribution when publishing methods, documentation or derived examples. Contribution credit does not imply a universal reputation or ownership score.
