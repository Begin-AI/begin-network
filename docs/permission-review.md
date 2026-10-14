# Delegation and permission ledger review

Reviewed 2026-10-14: `permissions.py` and `tests/test_permissions.py`. This is a targeted adversarial review, not a security audit. Ten permission tests pass in the declared `.venv` environment.

## P1 — persisted authority/audience binding (original defect fixed)

`PermissionLedger.__init__` stores audience, authority and freshness only in the Python object. The SQLite database stores one global freshness row and unnamespaced grant/operation/revocation records. Reopening the same database under a different authority or audience silently reuses the old domain's revocation freshness.

Exact dynamic reproduction on current source:

1. Generate authority keys A/B and worker W; configure locally trusted public keys for all three.
2. Open database D with `audience='owner'`, `authority=A`, `freshness=30`.
3. Apply A's signed empty revocation snapshot issued at 100, expiring at 200, at time 110; close D.
4. Reopen D with `audience='other-owner'`, `authority=B`, `freshness=30`.
5. Submit B's valid signed root grant to W and W's signed one-unit request, both addressed to `other-owner`, at 110. Do not provide any B revocation snapshot.
6. `reserve` returns **`accepted`** using A's freshness row.

This is a local configuration/domain-confusion flaw, not remote authority forgery: the host must reopen a database with changed policy. Nonetheless persistent state should fail closed on a misconfigured root/audience, and the required B snapshot is demonstrably bypassed. Shared grant identifiers can also collide across reopened domains, mixing accounting or revocation state.

Required fix: atomically establish immutable database metadata containing the authority, audience and applicable freshness contract; reject mismatched subsequent opens. Make authority rotation or policy changes explicit audited migrations, including revocation state refresh. Alternatively isolate every table and freshness snapshot by an authenticated persistent domain identifier. Add restart tests changing authority alone, audience alone and freshness; include concurrent initializers with conflicting settings. Do not simply clear freshness and reuse unnamespaced budget state automatically.

## Confirmed strengths and bounded claims

The chain checks require root signatures from the configured local authority, a child issuer matching the parent subject, an exact parent proof, equal purpose/resource, action subsets, decreasing exact-integer depth, nonincreasing per-grant budget, and child validity within parent validity. Leaf subject/proof/scope and request lifetime are checked. Malformed action sets and boolean budgets/depths are rejected. No remote authority-expansion bypass was found in these checks.

Reservation runs under SQLite `BEGIN IMMEDIATE`; each ancestor's cumulative spent counter updates in the same transaction as the operation digest. The existing sibling-budget test demonstrates rollback of a newly inserted sibling on exhaustion. Concurrent separate connections cannot both spend beyond a shared ancestor ceiling in the tested case. Duplicate operations return `duplicate` without spending again; changed digest under the same sender/ID is rejected. Admission does not establish completed work or exactly-once external effects.

Revocation snapshots require the local authority's valid signature and audience. Older timestamps and conflicting snapshots at the same timestamp are rejected. Revoked IDs accumulate rather than disappear when a later snapshot omits them. Every reservation, including duplicate retries, checks snapshot freshness and ancestor revocation. Freshness is bounded by the earlier of signed expiry and locally configured issued-plus-freshness; these checks are meaningful once the persistent-domain flaw is fixed.

## Integration requirements, not demonstrated exploits

One ledger must control each budget across replicas, as the docstring correctly states. Separate databases cannot prevent the same grant being spent independently. Reopening a backup with rolled-back spent/revocation state is outside SQLite transaction durability; deployments need an explicit recovery/backup policy.

`reserve` accepts a caller-supplied clock and reserves admission. A worker that delays execution must recheck current authorization/revocation before accessing data or spending external resources; this API alone cannot stop already running work. Accepted work is never automatically refunded, preventing retry refunds from multiplying budget, but crash recovery needs an operation outcome protocol. A granted numeric unit ceiling is not CPU/network sandbox enforcement.

Request units are now explicitly bounded to one billion before database conversion; the huge-integer regression rejects them as invalid bounded tasks. This hardening closes the noted malformed-number exception path. Input size is already bounded by envelope size. Local clock, trusted keys and configured root are host policy inputs and cannot be delegated to an incoming request.

## Current disposition

The current implementation atomically stores audience, authority and freshness in a policy row and rejects mismatched reopen settings. Ten permission tests pass, including all three mismatch regressions. The original P1 reproduction is resolved for freshly created and already-bound ledgers. Historical reproduction above describes pre-fix behavior. The populated legacy-database edge is also resolved: initialization rejects an absent policy row if any grant, operation, revocation or freshness data already exists. `test_legacy_unbound_populated_ledger_requires_migration` passes. All concrete findings from this scoped review are resolved; the integration limits remain applicable. Existing passing tests support chain attenuation and single-database budget atomicity at their tested scope; they also cover persistent root/audience binding, but not independent replicas, stop-running-work semantics, or operational revocation distribution.
