# Publishable discovery index

`index.json` is a static bootstrap artifact designed for eventual publication over HTTPS, repository mirrors, or another participant-chosen distribution channel. The repository itself remains private.

It publishes protocol/schema versions, experimental method descriptions, and optional public node advertisements. There are currently zero nodes. Relative artifact paths are resolved against the index's repository/distribution root, not the discovery directory. Public deployments must supply matching files at that root.

The strict schema rejects undeclared fields. Do not include personal intentions, raw vectors, private memberships, user activity, request contents, or mailbox addresses. Endpoint URLs have no query, fragment, or embedded credentials. Advertising an endpoint does not authorize clients to fetch it: operators must implement SSRF protection, local network restrictions, timeouts, and explicit fetch policy.

Methods declare implemented capabilities separately from experimental status. Semantic-baseline v0 is a planned synthetic-only method and MUST NOT be used for live private discovery. Public entries are unverified self-descriptions. Trust signatures, maintainer identity, freshness checks, and service certification are future work.

Validate with `begin-network validate-index discovery/index.json`. This verifies structure and duplicate identifiers only. It does not verify signatures, service availability, privacy, permissions, or malicious content disguised as a description. Human review is required before publication.
