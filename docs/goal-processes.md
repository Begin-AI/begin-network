# Goal execution across separate local processes

`examples/goal_process_demo.py` extends the bounded calendar-overlap goal exchange across three actual OS processes. It follows the patent's independent coordinator and device-local computation structure: an ingress and relay route the request to a final coordinator that owns the synthetic fixture worker and its budget ledger. Each process has its own signing identity and replay store. No Begin authority or shared network signing key participates.

Run `.venv/bin/python examples/goal_process_demo.py` from the repository root after installing the runtime into that environment. Child processes use the same Python interpreter and installed runtime; the harness explicitly removes `PYTHONPATH` rather than injecting source directories. An editable development install still points to local source and is not evidence of wheel portability; use the release installation smoke test for that separate guarantee.

## Verified exchange

The requester signs the original worker audience, bounded operation, sealed-input digest, chosen ingress, and hop limit. The ingress and relay verify the original and signed routing chain. An outer transport object carries the routing packet and an unchanged attachment containing the delegated grant tokens, sealed input, and owner-signed revocation snapshot. Transport attachments cannot grant authority merely by being present: the final worker independently verifies their signatures, delegation scope, freshness, budgets, and signed ciphertext binding.

The final process runs only the built-in deterministic overlap operation against its synthetic local fixture, reserves one unit against both grant budgets, and caches the completed result. It signs result metadata, including original-request and grant-chain digests and explicit synthetic-calculation provenance, and encrypts the output to the pinned requester key. Relays return that signed encrypted result. The parent stores it in a durable mailbox, closes and reopens the connection to model requester disconnection, then verifies the worker, original requester, expected grant chain, request binding, and ciphertext before decrypting and acknowledging the output.

A direct worker retry endpoint accepts only operations already present in the execution ledger. It independently rechecks current permissions and returns the exact cached signed result without another execution or unit reservation. Fresh work cannot use this endpoint to bypass routing. Retrying the original ingress is rejected by coordinator replay policy.

Expected output is `[[570,600],[800,840]]`. The report names three distinct process IDs, the actual worker PID observed by the local subprocess harness, exactly one completed execution, one unit spent against each grant, verified offline retrieval, and the deterministic fixture provenance. Process IDs and worker accounting in the HTTP response are unsigned local instrumentation; they are not remote attestation or cryptographic proof of honest computation.

## Evidence and limits

Run `.venv/bin/python -m unittest discover -s tests -p test_goal_processes.py -v`. Tests cover actual separate worker execution, cached direct retry, routing replay rejection, fresh direct admission refusal, tampered input with no successful outcome, wrong original-request binding, and subprocess cleanup.

All endpoints bind ephemeral numeric `127.0.0.1` ports. The reused test HTTP transport disables proxies and redirects, bounds bodies to 1 MiB, and applies socket timeouts. Private worker configuration travels through local pipes; private keys are not command-line arguments. The demonstration uses a fixed synthetic clock, synthetic fixture data, and one request at a time per process. It accepts no executable code, remote file path, user-controlled endpoint URL, or network tool from a request. The installed runtime is trusted by the host before launch.

This is a **local test transport, not a public server**. It has no TLS or transport caller authentication, process sandbox, real-device provisioning, public rate limiting, distributed budget consensus, or recovery from every crash point. Local processes can submit packets, while signed policy and permissions constrain accepted work. Relays see metadata and ciphertext; this is not private semantic matching. The owner retains a single authoritative local ledger, and cached retries require the still-valid grant chain and fresh revocation snapshot. A valid signature proves signer and integrity, not truthful computation or actual calendar consent.
