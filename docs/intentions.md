# Editable intentions and representation contracts

The patent's semantic vector signatures support discovery among independently operated participants. They do not establish a universal measure of a person's worth. This local reference module tests participant control over distinct intentions and compatible vector contracts. Its vectors are manually supplied synthetic numbers, not trained embeddings or evidence that semantic information has been learned.

The founding meanings remain broader than these fixtures: Mirror concerns reflection/current self, Window concerns aspirations and exploration, and Social concerns chosen connections. An intention's purpose remains fixed; participants create another intention to use a different purpose. A participant can maintain several intentions per purpose. Matching role constraints are supplied by a particular task and are not inferred from purpose. A Window intention may seek teaching, offer a contribution, or involve peers.

`Store` separates declared facts, aspirations, and explicitly labeled inferences. None is asserted to be independently verified. Each record has explicit participation consent, allowed disclosure categories, availability bounds, expiry, and a monotonically increasing revision. Creation defaults to no consent. `disclose` returns only categories selected by the participant and rejects retired, declined, or expired records. Disclosure categories are a deliberately coarse baseline; this is not encryption or a complete authorization implementation.

Edits require the expected current revision and invalidate every earlier representation, including when only consent or disclosure changes. Retirement withdraws consent and prevents further editing. Expiry prevents disclosure and comparison. Local immutable dataclasses prevent ordinary accidental field mutation, but this in-memory store is not persistent, access-controlled, signed, or a protection against a malicious host. Participants who already received information cannot be forced to forget it by local retirement.

Each `Vector` binds intention ID, revision, purpose, method, model, dimension, L2 normalization, and language. `vector` validates finite nonzero inputs and normalizes them. Comparison verifies the current revision and vector contract, exact metadata compatibility, consent, expiry, a remaining shared availability interval, and the task's role relation before cosine similarity. A forged caller-created vector may still contain arbitrary normalized numbers: provenance and authentic encoder execution need separate signed evidence. Identical numbers in this fixture mean only identical geometry, not proven human compatibility.

`examples/intentions.json` presents one fictional participant with three independently editable intentions. A guitar-learning Window goal illustrates a discovery request without ranking the person's overall identity. Facts and inferences are withheld when only aspirations are selected for disclosure. The teacher role complements this particular goal; it does not define all Window discovery.

Reproduce the seven lifecycle/contract tests:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_intentions.py -v
```

Coverage includes multiple purpose records, category-specific disclosure, edit/revision invalidation, stale-write rejection, consent withdrawal, retirement, expiry, malformed vectors, incompatible metadata, task roles, and nonoverlapping availability. Future semantic evaluation must independently test whether each encoder preserves the intended facts/aspirations/inferences and avoids unsupported conclusions. This reference module does not satisfy private matching, persistent user control across peers, trained-embedding accuracy, or universal protocol adoption.
