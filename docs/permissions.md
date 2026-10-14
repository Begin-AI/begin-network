# Experimental delegation and resource ledger

`permissions.py` is an opt-in grant profile (`begin-delegation-v1`) inside the signed envelope contract. It supplements, rather than silently changes, the earlier direct-grant profile. Hosts select a root authority and pinned key map; Begin approval is not required.

A grant body binds profile, subject, purpose, permitted actions, resource, cumulative `max_units`, remaining `depth`, and parent grant ID. Root grants have no parent or proofs. Every child is signed by its parent's subject and references that parent. Purpose/resource stay fixed; actions, units, depth and validity can only narrow. The request references the leaf, is signed by its subject, and stays within its lifetime and scope. IDs cannot be reused for changed signed content.

The durable SQLite ledger atomically reserves the request's units against every ancestor. Sibling delegations cannot independently spend the same parent budget. Identical retries return `duplicate`, and hosts must not execute them. Conflicting operation IDs are rejected. Accepted reservations are not automatically refunded after failures; this deliberately favors a hard bound over optimistic recovery. Hosts need separate execution-state and transaction recovery designs.

Signed root-authority revocation snapshots must be fresh within a local bound and unexpired before every reservation. Revocations are monotonic: later snapshots cannot un-revoke a grant; an ancestor revocation blocks descendants. Snapshot rollback and conflicting same-time snapshots fail. A local ledger is permanently bound to root authority, audience and freshness policy; changing them requires explicit migration. Populated legacy ledgers without a binding are rejected.

This is a single-owner consistency boundary. Independent ledger replicas cannot reserve the same scarce budget safely without a further consistency protocol. Units are abstract resource accounting, not money settlement, truthful human identity, arbitrary-code isolation, or a guarantee that work finishes. Revocation cannot undo previously learned information or already completed effects. Clock correctness, key custody and authenticated policy updates remain host responsibilities. No live personal-data approval is implied.

Tests cover signed multi-level authority, widened child scope, wrong subjects, sibling spending, concurrent overspend, rollback after failed reservation, restart idempotency, revoked ancestors, stale snapshots, snapshot rollback, conflicting operation content, persistent owner binding and legacy rejection.
