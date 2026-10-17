# One representation balancing Mirror, Window and Social

Founder correction, 17 October 2026: Mirror, Window and Social are complementary dimensions of **one representation**. The previous implementation incorrectly made them exclusive purpose categories. That interpretation is superseded.

An intention now contains all three named `perspectives`:

- `mirror`: present capabilities, interests, needs and circumstances.
- `window`: aspirations and openness to unfamiliar possibilities.
- `social`: relevance to other participants, including possible collaborators, contributors and beneficiaries. This is not a popularity or human-worth score.

Each view contains explicitly supplied, owner-approved text. Facts, aspirations and agent inferences remain labeled shared context; perspective text is not asserted to be a verified fact. No migration infers missing views from old data. Users or their authorized agents must provide them.

`balance` contains three finite, positive weights that sum to one. The default is an equal balance; MCP callers supply the balance explicitly. All three views must have content and a positive contribution. An owner can edit the balance and content together under the existing revision/consent controls.

The experimental fusion rule is:

```
v = normalize(w_mirror * normalize(encode(mirror, context))
            + w_window * normalize(encode(window, context))
            + w_social * normalize(encode(social, context)))
```

Only the resulting single vector is used for discovery. The three views do not become separate index records or matching partitions. Both participants' combined vectors determine relevance. Consent, complementary task roles, availability and each participant's relevance threshold remain separate gates. A near-zero combined vector is rejected rather than silently dropping a view. This weighted sum is a transparent first implementation, not a validated model of social relevance or a claim that semantic information is preserved perfectly.

The existing `purpose` field is retained as a compatibility slot with the sole accepted value `integrated`. It no longer selects Mirror, Window or Social. Private circuit rows likewise contain a fixed v2 marker in the former purpose slot; there is no same-perspective matching gate.

## Version and migration boundary

The synthetic encoder and pinned MiniLM preprocessing have new v2 method/model IDs. The shared-index envelope is `begin-shared-index-v2`; its parameters bind `balanced-mirror-window-social-v2`. Public method metadata uses `begin/shared-index-v2`. Existing source-pinned pools must explicitly adopt the new code and start a compatible pool.

Old single-purpose intentions fail validation. Recreate them explicitly with all three perspectives and an approved balance, under a new intention ID; do not reinterpret old vectors, grants or index shares. Existing records remain on disk, and retirement/revocation remains available. Withdraw old enrollments using their original compatible operator deployment, or let them expire. New code does not silently upgrade old remote records or authorities.

Edits to any view or balance increment the intention revision. Old vectors, introductions and search retries fail revision checks; a fresh authorized enrollment/search is required. Existing disclosure decisions are not broadened by adding these dimensions.

The historical `matching.py` lexical baseline and old embedding benchmark corpora remain frozen solely to reproduce their published v1 measurements. Their purpose-category model is not used by the current participant runtime and is not evidence for this corrected representation.

## Evidence

Regression tests check all three views contributing to one vector, changes in balance affecting relevance, missing/zero/nonfinite inputs being rejected, old purpose records being rejected, revision-bound permissions, and mixed-balance candidate selection through the three-node private computation. The local MiniLM experiment also runs the corrected fusion with pinned model files. This establishes implementation behavior; meaningful balance defaults and human relevance still require evaluation.
