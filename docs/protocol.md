# Begin protocol — draft 0.1

Status: proposed contract, not an implemented secure protocol. Normative words describe target requirements. Only discovery-index structural validation is executable today.

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

Use a reviewed signed-message standard; exact cryptographic profile and canonicalization are unresolved. The protected content MUST bind protocol version, message type, sender key, request ID, audience, issued/expiry times, ciphertext, and permission-proof references. Receivers independently check the signature, supported profile, audience, freshness, replay state, and permission chain. Reject unknown critical fields. Encryption and signing keys are distinct roles. Key discovery and rotation must resist substitution.

## Authorization target

Grants bind issuer, subject, audience, purpose, resources/actions, limits, validity, revocation source, and delegation depth. Child grants can only narrow scope. A match or valid signature alone MUST NOT release a key. Key release requires both matching and applicable authorization. Revocation stops future access according to a declared freshness bound; it cannot erase information already learned. Budget consumption needs atomic accounting, not a numeric field alone.

## Discovery target

The public index advertises public services and methods only. Participant intentions, vectors, private group membership, mailboxes, keys for sealed content, and request bodies are prohibited. Index metadata is not evidence of authority or honest operation. Clients select services independently and apply local policy. Index mirrors and alternate bootstrap sources must be supported.

## Private matching research boundary

Raw vectors are sensitive. TLS alone does not hide vectors from node operators. Each candidate method must state what requester, participant, node, and colluding parties learn; test inversion, probing, match-outcome leakage, and metadata exposure. No approved private matcher exists in this seed. Plaintext synthetic baselines are not P2 evidence.

## Asynchronous delivery target

Mailboxes store expiring encrypted messages scoped to recipients, with quotas, acknowledgements, deduplication, retry, and later retrieval. Request IDs and operation IDs provide idempotency. Expired or revoked work cannot be resumed as fresh work. Exactly-once external effects require application-specific transaction support. No mailbox service is implemented yet.

## Provenance and extensions

Results distinguish human responses, observations, and agent inference. Optional receipts record acknowledged contribution, not universal human worth. Voting, payments, studies, and remote computation have additional gates. Agent-originated goals create no new permissions. Executing arbitrary remote code requires isolation, output policy, and enforceable resource limits.
