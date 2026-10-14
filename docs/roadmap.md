# Implementation roadmap

1. Seed (implemented): founding brief, protocol draft, public-index schema and validator, synthetic index, CI. No privacy claims.
2. Experimental signing profile, threat model, envelope verifier, direct grants, persistent replay store, sealed content and adversarial tests implemented. Next: chain attenuation, fresh revocation distribution, atomic budgets, key-release service and review.
3. Two synthetic baselines and a fixed 13-case corpus implemented, including documented failures. Next: build held-out complementary-fit corpus and versioned method interfaces; benchmark private-matching candidates separately from utility baselines.
4. Implement independent discovery/mailbox nodes and agent CLI adapter. Prove offline retrieval, retries, deduplication, quotas, and failover.
5. Demonstrate a synthetic help-seeker/helper connection with disclosure after authorization; include decline, no-match, revoked and failed outcomes. A plaintext demo cannot satisfy P2.
6. Independent implementation interoperability and published P1–E4 evidence; then opt-in personal-data pilots.

Legacy reference: historical coordinator for execution cycles; scientist-lib for local encoders and remote worker concepts; ml-api for timeline/interest features. No legacy source has been ported. Preserve new purpose-specific representations rather than deriving authority from behavioral inference. Optional computation/economy modules follow core discovery and permission work.
