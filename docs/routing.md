# Independent coordinator routing experiment

The patent's independent coordinators can relay requests without a mandatory company registry. `begin_network.routing.Coordinator` demonstrates that boundary using locally configured peer keys, origin keys, destination routes, a per-node durable replay store, and an injected transport. Every coordinator generates its own Ed25519 identity. No shared signing key or Begin-operated authority participates.

This includes callable-transport tests and a three-process loopback experiment with real independently verified signatures and separate coordinator state. It is not a deployed network, private discovery mechanism, capability advertisement resolver, execution authorization service, or distributed consensus protocol.

## Routing contract

The origin signs a request whose audience is the final destination. The origin also signs `body.routing` with its chosen ingress key and hop limit. Ingress independently verifies that origin key against local origin policy and verifies the final audience and time window. Ingress wraps the original in a signed hop addressed to its selected peer. Each subsequent hop signs the original-token SHA-256 digest, destination, full ordered signer path, origin-selected hop limit, and previous signed-token digest. The transport packet contains the unchanged original token plus the signed hop list.

Every receiving node verifies the latest peer signer and its own audience, independently verifies the original origin signer and final audience, verifies every earlier hop against its local peer-key policy, checks adjacent hop audiences, and checks the hash and path chain. The first hop must be signed by the origin-selected ingress, and all hop limits must equal the signed origin policy. A transit peer cannot truncate the ingress or reset the budget. All hop expiries equal the original expiry; forwarding cannot extend it. Duplicate signers and revisiting the receiver are rejected. The sender also avoids already visited nodes. Both the configured maximum (at most 16) and the unchanged signed route limit constrain forwarding.

Nodes need explicit trusted keys for the full transit chain, not merely their immediate neighbor. Alternate trust discovery is future work. An index advertisement alone is insufficient to establish routing trust. Local peer revocation consists of removing its key from policy; there is no automatic revocation feed in this reference.

The final node returns the verified original payload to its host. **This confers no authority to execute it.** The host must independently verify permission evidence, local willingness, resource limits, and revocation before acting. Packet bodies are data and cannot change routes or peer trust maps.

## Voluntary participation and availability

A node selects only locally configured next hops. Missing routes, loops, and exhausted hop limits produce `Refused`. A transport `ConnectionError` or voluntary `Refused` permits trying the next locally configured peer. Signature, origin policy, replay, or malformed-binding errors fail closed and do not trigger a policy-bypassing fallback.

Each node durably admits the original `(sender, id)` once after route validation. This prevents duplicate local handling across multiple paths. It also means a lost downstream result or crash cannot be automatically retried through a previously visited node. Failover is best effort, not guaranteed eventual delivery or exactly-once external effects. A malicious trusted origin/peer can deny service or disclose metadata; the verifier does not prove honest operation.

Every relay sees the request and routing metadata. Encryption and selective metadata hiding need a separately specified protocol; this experiment must use synthetic data. A network transport would additionally need authentication, timeouts, bounded queues, traffic and storage quotas, and endpoint validation. The injected callable here performs no HTTP or arbitrary remote-code execution.

## Evidence

Run `.venv/bin/python -m unittest discover -s tests -p test_routing.py -v` from the repository root. Tests use distinct keys and SQLite replay stores for independent coordinators. They cover three-node routing, replay, offline/refusing peer failover, unknown signer refusal, original tampering, signed digest substitution, malformed earlier hops, loop refusal, hop exhaustion, and in-flight expiry. Passing demonstrates these local routing mechanisms, not internet-scale coordination.

## Independent OS processes over loopback HTTP

`examples/coordinator_process_demo.py` also launches three separate Python processes, each with its own private key and SQLite replay file. The ingress first attempts an offline peer, then routes through the second process to the final process. The parent compares the returned original payload against its independently verified origin token. This response comparison is local test evidence; the HTTP response itself is not a signed task receipt and proves no execution.

Run `PYTHONPATH=src .venv/bin/python examples/coordinator_process_demo.py`. The command prints the three distinct process IDs, verified synthetic original body, and offline-failover result. Temporary databases and keys are discarded after the subprocesses are terminated and reaped. Private worker configuration passes through a local pipe, not command-line arguments.

Run `.venv/bin/python -m unittest discover -s tests -p test_coordinator_processes.py -v` for process-level tests of routing, actual offline-peer failover, signature-tampered origin rejection, unsigned-hop rejection, and clean subprocess shutdown. These augment the callable-transport tests with real OS processes and TCP boundaries.

This HTTP implementation is a **local test transport, not a public server**. It binds ephemeral ports on numeric `127.0.0.1`, disables proxies and redirects, limits request/response bodies to 1 MiB, and applies bounded socket timeouts. It runs a single-request server per node. It has no TLS, caller authentication, public rate limits, process sandbox, remote deployment configuration, or production lifecycle manager. Local processes can submit packets, but every routed original/hop still requires the configured signatures and audience checks. Synthetic request metadata is visible to every relay. No firewall or socket isolation claim is made.
