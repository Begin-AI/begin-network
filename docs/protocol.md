# Begin protocol — draft 0.1

Status: proposed contract, not an implemented secure protocol. Normative words describe target requirements. Index validation, the experimental signing profile, direct grants, sealed content, local mailboxes, and synthetic matching are executable. Delegation, single-owner budgets, signed relay routing, owner-local encrypted queries and editable intention contracts now have experiments. Full protocol enforcement and private semantic discovery remain incomplete.

## Design authority and decentralization

When design choices are uncertain, consult [US11711348B2](https://patents.google.com/patent/US11711348B2/en), especially Figures 1–9 and its detailed description, together with the founding brief and explicit founder decisions. The network serves a decentralized human-and-agent world. Independent services and device-local agents can discover, coordinate, and improve methods without a required Begin-operated service. Agent-proposed improvements require explicit adoption and cannot alter existing delegations.

The stable foundation is a versioned signing and validation contract. Each receiver checks both cryptographic authenticity and applicable protocol/permission rules. A signed but noncompliant request MUST be rejected. There is no universal Begin signing key, shared secret, or company-issued approval required for each request. Key rotation and protocol evolution remain possible through explicit migration rules. Patent vector “signatures” describe semantic fit; they are not cryptographic proofs of compliance. The experimental signing profile is specified in `signing-profile.md`; independent security review remains outstanding.

## Roles and boundaries

Participants express intentions; agents act within delegation; discovery nodes identify potential counterparts; coordinators manage scoped exchanges; mailbox nodes retain expiring ciphertext. Services are replaceable. Begin is not a mandatory authority. A key identifies a key holder, not a unique human or authorized representative.

## Intention model

An intention has an ID, purpose, issuer, expiry, and editable mirror/window/social representations. Every representation declares method ID, model revision, dimensions, normalization, language support, and provenance (expressed fact, aspiration, or inference). Structured constraints carry roles, timing, location, disclosure, and resource limits. Similarity never overrides a hard constraint, grants access, or constitutes consent. Complementary roles require explicit evaluation. Unsupported representation comparisons MUST fail.

## Exchange state machine

FORMED → REPRESENTED → DISCOVERING → PROPOSED → AUTHORIZED → DISCLOSED → EXECUTING → COMPLETED → EXPIRED.

DECLINED, NO_MATCH, FAILED, and REVOKED are explicit outcomes. Authorization may be required at multiple stages and by multiple parties. Transitions are enforced by receiver code, not by instructions embedded in requests. A private matching implementation must define its own transcript and leakage before discovery can run with real intentions.

## Message families

CapabilityAdvertisement, DiscoveryQuery, MatchProposal, AuthorizationGrant, SealedRequest, TaskResponse, ContributionReceipt, Revocation, and MailboxAcknowledgement.

## Authentic envelope target

The experimental profile uses compact JWS/Ed25519 with exact transmitted bytes as signing input; see `signing-profile.md`. External review remains outstanding. The protected content MUST bind protocol version, message type, sender key, request ID, audience, issued/expiry times, ciphertext, and permission-proof references. Receivers independently check the signature, supported profile, audience, freshness, replay state, and permission chain. Reject unknown critical fields. Encryption and signing keys are distinct roles. Key discovery and rotation must resist substitution.

## Authorization target

Grants bind issuer, subject, audience, purpose, resources/actions, limits, validity, revocation source, and delegation depth. Child grants can only narrow scope. A match or valid signature alone MUST NOT release a key. Key release requires both matching and applicable authorization. Revocation stops future access according to a declared freshness bound; it cannot erase information already learned. The opt-in `begin-delegation-v1` profile adds atomic single-owner accounting and fresh signed revocation snapshots; see `permissions.md`. This is not distributed settlement or external sandboxing.

## Discovery target

The public index advertises public services and methods only. Participant intentions, vectors, private group membership, mailboxes, keys for sealed content, and request bodies are prohibited. Index metadata is not evidence of authority or honest operation. Clients select services independently and apply local policy. Index mirrors and alternate bootstrap sources must be supported.

## Private matching research boundary

Raw vectors are sensitive. TLS alone does not hide vectors from node operators. Each candidate method must state what requester, participant, node, and colluding parties learn; test inversion, probing, match-outcome leakage, and metadata exposure. No approved private matcher exists in this seed. Plaintext synthetic baselines are not P2 evidence.

## Asynchronous delivery target

Mailboxes store expiring encrypted messages scoped to recipients, with quotas, acknowledgements, deduplication, retry, and later retrieval. Request IDs and operation IDs provide idempotency. Expired or revoked work cannot be resumed as fresh work. Exactly-once external effects require application-specific transaction support. A durable local mailbox reference exists; authenticated multi-node networking remains unfinished.

## Provenance and extensions

Results distinguish human responses, observations, and agent inference. Optional receipts record acknowledged contribution, not universal human worth. Voting, payments, studies, and remote computation have additional gates. Agent-originated goals create no new permissions. Executing arbitrary remote code requires isolation, output policy, and enforceable resource limits.
