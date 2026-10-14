# Synthetic matching experiment

The patent's vector signatures describe relevance for discovery, separate from cryptographic message signatures. This experiment exercises that boundary with two transparent, local representations. It does **not** implement private matching, train a model, prove real-world semantic quality, or establish permission to disclose data or execute work. Use the verifier and authorization contract separately.

`src/begin_network/matching.py` implements three purpose partitions:

- **Mirror:** peer intentions for reflection and affinity.
- **Window:** aspirations and exploration in the founding vision. This narrow experiment uses complementary seek/offer cases within that broader purpose.
- **Social:** peer intentions for voluntary social discovery.

Purpose, role, language, exact location, and mutual required tags constrain eligibility before relevance scoring. Participation can be declined. Missing relevance returns `no-match`. Explicit exploration can expose a nonzero, below-threshold result, labeled `exploration`; it never overrides constraints or decline. Discovery grants no authority. Purpose-specific behavior here is a baseline partition and role policy, not three separately trained representation models or a complete definition of the founding concepts. In particular, Window is not restricted to help-seeking or complementary roles; future methods must represent aspirations and exploration beyond this fixture.

Each representation records method and model version, purpose through its source intention, a deterministic SHA-256 of the exact source text, and synthetic provenance. The digest is an audit aid, not proof that the text or self-declared tags are true. Raw text and token representations are visible in memory. A low-entropy text digest can also reveal content through guessing. Do not publish real intentions, representations, or their hashes to a discovery index.

## Mechanisms and evidence

`lexical-v1` uses lowercase alphabetic token sets and binary cosine similarity. `concept-v1` additionally maps a small, explicit vocabulary of gardening, coding, food, and music synonyms to concepts. Both use the `synthetic-v1` model identifier, and cross-method/model comparison returns `incompatible`. Independent coordinators must negotiate an exact compatible representation contract before comparison; a shared label alone does not prove correct implementation.

The fixed, hand-authored corpus is `examples/matching_cases.json`. At threshold 0.3 it yields:

| Mechanism | True positive | False positive | True negative | False negative |
| --- | ---: | ---: | ---: | ---: |
| Lexical | 1 | 2 | 7 | 3 |
| Curated concepts | 4 | 2 | 7 | 0 |

Seven unit tests verify purpose handling, determinism/provenance, incompatible representations, constraint precedence, explicit exploration, unsupported methods, and the complete corpus confusion counts. Reproduce from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_matching.py -v
```

The corpus deliberately includes two unresolved false positives: `no python` matches a request for Python help, and a candidate stuffing four topic words passes the threshold. Lexical matching also misses three synonym pairs. The concept vocabulary was written with these examples in mind; its apparent improvement is a demonstration, not a held-out evaluation or evidence of generalization. Neither baseline understands negation, qualifications, actual availability, willingness beyond a Boolean, time windows, multilingual meaning, deception, or whether an offered contribution solves a goal.

## Next evaluation gates

Before choosing an embedding method, collect a larger consented or synthetic held-out corpus with founder-reviewed labels, multiple simultaneous intentions per person, changing intentions, complementarity, negation, scarce qualifications, and constraints. Freeze method/model versions and compare against these baselines. Measure false matches and missed matches separately, calibration by purpose, adversarial resilience, and usefulness after voluntary acceptance. Test interoperability with independently implemented encoders. Private discovery requires a separately specified and evaluated method; these plaintext experiments cannot satisfy that requirement.
