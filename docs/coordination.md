# Local durable coordination reference

`begin_network.coordination.Mailbox` is an executable storage and claim reference for the asynchronous exchange described in the founding brief. It supports the patent's independently operated coordinator model: every node chooses its own local database and recipient adapter. It requires no Begin service or universal key.

The host verifies the signed envelope, recipient identity, delegation, current revocation state, purpose, and resource authorization **before** calling this module. The API deliberately accepts opaque bytes and does not claim to perform cryptographic verification or encryption. The `recipient` argument must come from authenticated host context, never from an unchecked request field. Anyone with direct database access can read or modify its metadata and bytes.

```python
from begin_network.coordination import Mailbox

node = Mailbox('local-node.sqlite')
# Only after independent verification and local policy acceptance:
node.submit('unique-operation-id', 'recipient-key-id', b'opaque-ciphertext', 2000000000)
for delivery in node.retrieve('recipient-key-id'):
    if node.claim('recipient-key-id', delivery.operation_id):
        # Perform only host-authorized bounded work; this module runs no code.
        node.acknowledge('recipient-key-id', delivery.operation_id)
node.close()
```

## State and delivery semantics

Submission creates `pending` work. A recipient can retrieve it later after disconnecting or reopening the database. An atomic SQLite claim changes `pending` to `claimed`. Only the recipient can claim or acknowledge the operation through these methods; the host must establish the caller's identity. Acknowledgement moves claimed work to `acknowledged` and clears the payload. Expiry changes pending/claimed work to `expired`; validated revocation changes it to `revoked`. Both clear payloads. Expiry is enforced when accessing the mailbox; this is not a background erasure service. SQLite journals, backups, and storage media may retain earlier bytes.

An operation ID uniquely names one recipient, ciphertext digest, and expiry. Exact retries return the stored state; conflicting retries fail. Terminal records retain digests and IDs as tombstones. Claiming uses an atomic conditional update so two coordinator instances sharing a database cannot both claim an operation. Quota admission uses an immediate transaction, with per-recipient active message-count and byte limits. Pending and claimed work consume quota; terminal states release active capacity.

**At-most-once claiming trades recovery for avoiding automatic repeat work.** A process that crashes after claiming leaves the operation claimed until expiry; it is not automatically retried. An acknowledgement lost after an external effect cannot establish whether that effect occurred. Exactly-once external effects, recovery leases, durable result storage, and cross-node deduplication need application-specific transactions or an additional protocol. Coordinators must recheck authorization immediately before executing and before committing results; revoking a database record cannot interrupt an already-running computation.

## Node replacement

`snapshot(destination)` uses SQLite's backup API and preserves pending work, claims, and tombstones. The host must quiesce the source, copy it, retire the source, and open the destination as the replacement. A snapshot is sensitive operational state, never a public discovery-index entry. Keeping both copies active can execute duplicate work: this reference has no distributed leader election, live failover, consensus, or atomic ownership handoff.

## Scope and limits

Tests demonstrate offline retrieval, recipient scoping, cross-connection atomic claim, replay/conflict handling, expiry, revocation, quota enforcement, and snapshot migration. They do not establish private matching, network transport, authenticated callers, encrypted-at-rest storage, secure deletion, arbitrary-code isolation, or multi-machine consensus. Per-recipient quotas do not prevent attackers from creating many recipient identities. Tombstones are retained indefinitely to protect deduplication and need an explicitly designed retention policy plus global storage bounds before an untrusted public deployment. One connection should be used per worker; this reference does not share a connection across threads.

Run the checks with `PYTHONPATH=src python3 -m unittest discover -s tests -p test_coordination.py -v` from the repository root.
