# Patent design map and deliberate adaptations

Architectural source: Rima Al Shikh's [US11711348B2, detailed description and Figures 1–9](https://patents.google.com/patent/US11711348B2/en). This is an engineering traceability map, not claim construction, legal coverage analysis, or a patent license. Figure summaries below are paraphrases; implementation assessments describe this repository.

| Patent reference | Design subject | Current implementation evidence | Gap or explicit adaptation |
| --- | --- | --- | --- |
| Figure 1 | Requesters, coordinators, agents and publishers cooperate | `routing.py`, `execution.py`, three-process goal demo | Synthetic roles only; no live enterprise or device fleet |
| Figure 2 | One person's devices form a local group with agents | Separately keyed local process fixtures | No device provisioning, agent election, group membership or resource pooling implementation |
| Figure 3 | Publishers offer data; agents decide whether to accept it | Fixture worker accepts only configured synthetic resource/revision and fixed action | No real publisher ingestion, dataset quality scoring or device resource negotiation |
| Figure 4 | Agents retain properties and time-varying streams | Editable purpose-specific intention records and timing constraints | No general time-series store or suppressed-property index; vectors do not reconstruct complete timelines |
| Figure 5 | Coordinators discover and direct requests | Signed hop chain, ingress/hop budget, failover and mailbox tests | Known synthetic candidate bootstrap; no complete private enumeration or secure cross-host transport |
| Figure 6 | Data journaling supports dataset quality and request registration | Local signed grants, explicit method contracts and fixture provenance | No publisher-ranking/data-journaling service; permission evidence does not prove data quality |
| Figure 7 | Coordinator standards, versions and credibility are maintained | Versioned envelope, installed runtime evidence, pinned local trust and signed index validation | No mandatory authority or automatic remotely requested updates; no certification of coordinator honesty |
| Figure 8 | Actors coordinate responses back to a requester | Encrypted signed bounded result, durable later retrieval and cached duplicate response | No multi-worker aggregation or federated model training; signatures do not prove truthful computation |
| Figure 9 | Registered methods produce semantic interest/intention vectors | Method index, editable contracts, lexical/concept/MiniLM comparison, MPC predicate experiment | Representation quality has measured failures; cryptographic signatures are separate from semantic vectors |

## Founder decisions applied explicitly

The founder's subsequent direction requires a completely decentralized human-and-agent world with no mandatory Begin gateway or request-approval signer. Patent authority roles therefore inform **functions**—request validity, compatible versions, method descriptions and inspectable provenance—rather than obligating a single company-operated service. Hosts pin trust and enforce permissions independently. The current implementation does not pretend to have implemented the patent's data-journaling and coordinator-credibility services simply by adding Ed25519 signatures.

Stable, versioned verification rules bind identity keys to bytes and constrain operations. Independent permission validation establishes the tested scope of compliance. Valid signatures do not establish willingness, human identity, reputation, truthful embeddings or honest results. New methods require explicit compatibility and adoption; incoming content cannot rewrite host permissions or verifier code. Key rotation, revocation and protocol migration are distinct from permanently freezing a signer.

Figures 2–4 identify important future local-device and data-management work. Figures 6–8 identify quality, operator credibility and aggregation work beyond this experimental seed. The present source can support early publication of its demonstrated components with these gaps visible; it cannot claim the full original network or live personal-data readiness.
