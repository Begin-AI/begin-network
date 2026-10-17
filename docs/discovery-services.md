# Experimental discovery services

The original runtime now has an HTTPS interface for each of the three selected discovery nodes. Enrollment and query shares travel from the participant's runner to those services. Each node checks its own policy and signs its own approval; the requester never holds node signing keys. The older test harness is no longer needed to submit a search through the new MCP tools.

This remains a **synthetic, same-host tested pilot**. No independent production operators, live GPT/Claude connection, malicious-secure computation, anonymous membership or semantic quality result is established by these tests. The existing Sites application is separate.

## Flow and boundaries

1. An operator chooses three node keys, HTTPS origins, mutual-TLS committee certificates, static computation addresses, method source hashes and admitted caller keys. These come from local configuration, never tool arguments or discovery advertisements. Any operator can establish another pool; there is no Begin root signer.
2. `begin_publish_intention` obtains an invitation from the participant's existing consent machinery, splits the integrated three-perspective representation and opening key locally, and uploads one share to each node. A separate enrollment admission key avoids requiring the owner's persistent address at this interface. The node still sees the admission pseudonym, source connection, opaque record and timing; this is not anonymous enrollment.
3. `begin_search_network` retrieves consistent encrypted snapshots, creates query shares on the requester runner, and saves the job privately before submission. Each node receives only its own share. It verifies requester consent, its pinned method/topology and the current snapshot before issuing a signed approval. All three approvals must bind the same session before any node queues its worker.
4. Workers additionally compare session digests over the mutually authenticated computation channels before combining shares. This rejects accidentally overlapping, individually authorized searches using the same ports. It does not provide malicious-secure MPC.
5. Nodes keep durable job states and encrypted outputs. One job holds the node's computation ports at a time. A node process lock is inherited by its bounded worker, preventing an orphan and replacement service from running overlapping workers. Interrupted computations fail closed; completed outputs can be recovered without rerunning them.
6. `begin_check_search` verifies all three signed encrypted results and reconstructs matches on the requester runner. Only match handles and identities reach the model; saved private invitation cards remain on the runner. Closing and reopening either MCP client does not discard the saved search or stop a committed node job. Results still expire with their short session lifetime.
7. `begin_contact_network_match` uses a saved match through the existing introduction/acceptance/disclosure flow. A match does not authorize full-text disclosure. `begin_withdraw_enrollment` revokes local invitation permission before attempting all three remote withdrawals; the same call can retry a partial failure.

The runner retains idempotency records, query shares and enrollment update keys in its private participant database. These are not copied into a public index. Local retention is not forensic erasure; this pilot has no automatic database compaction or backup purge. Editing/retiring an intention blocks later contact/disclosure, but operators must also submit remote withdrawal to remove the old index shares promptly. Expiry is a fallback, not immediate distributed revocation.

## Operator interfaces

Install the core package and the hash-locked optional MPyC dependency in `experiments/mpc/requirements.txt` on a POSIX operator host. The service entry point is:

```sh
python -m begin_network.discovery_service --config /private/operator/node.json
```

The private configuration contains `data_policy: synthetic-only`, `state_directory`, the node's own `node_key`, `pool`, `party_index`, local `worker_path`, `pinned_sources`, `pinned_parties`, `pinned_keys`, `clients`, HTTPS `certificate` and `private_key`, plus `bind` and `port`. `clients` maps admitted signing-key IDs to public keys and roles (`enroll`, `query`). The node state directory also holds its MPyC `.config` certificate files. These are operator-provisioned files, not values accepted from a requester. Worker source and dependencies must be deployed and pinned by each operator.

POST `/rpc` accepts a signed protocol envelope with profile `begin-discovery-service-v1`, operation and payload. Operations are `upload`, `snapshot`, `prepare`, `commit`, `result`, and `cancel`. Both requests and responses bind the audience and a short expiry; responses also bind the exact signed request digest. Cached identical API requests return the original signed response; conflicting or interrupted request-ID reuse is rejected. Authentication is node-local signing-key admission, not OAuth or a network-wide identity service.

`RemotePool` is the participant-side client. Its configuration pins `pool`, `sources`, ordered `parties`, and three `nodes` containing `kid`, `public`, `endpoint`, and optional `ca_file`. HTTPS certificate verification is mandatory and redirects are rejected. `plan` returns a private resumable job, `start` prepares/commits it, and `poll` retrieves results. A caller must persist a planned job before starting it. The supplied `DiscoveryRunner` does this in the participant database.

For MCP, operator configuration adds a `discovery_services` mapping keyed by pool ID. Each value is the `RemotePool` configuration plus a private `enrollment_key`. The pool must also appear in `discovery_pools`. This enables five additional tools, bringing the configured adapter to twenty. Without this configuration the original fifteen tools remain available. The adapter's stdio boundary belongs on the selected operator runner; users are not being asked to install it on their phones. An authenticated remote client-to-runner bridge is still required for actual GPT/Claude products.

## Limits and validation

The existing passive-security assumptions remain: any two colluding index nodes can reconstruct inputs; node/requester metadata and repeated predicates leak information. There is no semantic usefulness evaluation, network-wide abuse budget or Sybil resistance. The pilot permits eight lifetime records, three lifetime queries per admitted key/pool, and one active job per node. Failed preparations/computations consume budget. These limits intentionally constrain this experiment and are not a scalable scheduler design.

The service is a bounded Python HTTPS pilot, not hardened public Internet infrastructure. It does not implement production connection limits, operator provisioning, certificate rotation, account OAuth, monitoring or availability guarantees. A configured runner operator holds its participant's keys and plaintext intentions.

Run the service integration suite with the optional MCP and MPyC dependencies installed:

```sh
python -m unittest discover -s experiments/shared_index -p test_service.py -v
```

Its three tests use real local HTTPS listeners and subprocess workers. They cover signed role admission, unknown callers, owner-bound result retrieval, node-service restart, missing approvals, changed query shares, withdrawn snapshots, cancellation, enrollment/search through two separate official-SDK MCP clients, client restart and withdrawal. The separate shared-index suite tests different validly authorized sessions on the same computation channels and the arithmetic/privacy predicates. These are synthetic local execution results, not evidence of independent administration.
