# Publishable discovery index

`index.json` is a static bootstrap artifact designed for eventual publication over HTTPS, repository mirrors, or another participant-chosen distribution channel. The repository itself remains private.

It publishes protocol/schema versions, experimental method descriptions, and optional public node advertisements. There are currently zero nodes. Relative artifact paths are resolved against the index's repository/distribution root, not the discovery directory. Public deployments must supply matching files at that root.

The strict schema rejects undeclared fields. Do not include personal intentions, raw vectors, private memberships, user activity, request contents, or mailbox addresses. Endpoint URLs have no query, fragment, or embedded credentials. Advertising an endpoint does not authorize clients to fetch it: operators must implement SSRF protection, local network restrictions, timeouts, and explicit fetch policy.

Methods declare implemented capabilities separately from experimental status. The registered methods are implemented synthetic-only baselines or experiments and MUST NOT be used for live private discovery. Public entries are unverified self-descriptions. Trust signatures, maintainer identity, freshness checks, and service certification are future work.

Validate with `begin-network validate-index discovery/index.json`. This verifies structure and duplicate identifiers only. It does not verify signatures, service availability, privacy, permissions, or malicious content disguised as a description. Human review is required before publication.

Each method advertises an exact method version, model contract, dimensions (or an explicitly dynamic shape), normalization, implementation path and runtime/experiment availability. These public method descriptors are not participant representations. `per-session-pinned-model` is a wrapper constraint: both endpoints still must independently pin the same concrete encoder/model/dimension before comparing. The pretrained benchmark is an experiment, not an approved live encoder. Structural validation cannot verify advertised implementation truth.
