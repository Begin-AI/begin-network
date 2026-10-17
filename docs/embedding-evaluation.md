# Measured pretrained embedding evaluation

Historical v1 benchmark: its corpus predates the integrated Mirror–Window–Social correction and is retained for reproducibility, not as the current representation contract. See `balanced-representation.md`.


An isolated Python 3.12.13 CPU experiment downloaded and ran `sentence-transformers/all-MiniLM-L6-v2` on 24 frozen synthetic goal pairs. Learned similarity improves paraphrase recall in this fixture, but **does not reliably preserve negation, willingness, temporal skill claims, or the distinction between aspiration and capability**. It is unsuitable as the sole decision rule for Begin discovery.

The patent's semantic signatures motivate relevant discovery, distinct from cryptographic signatures. This experiment tests relevance geometry; it does not test the entire patent design, private discovery, identity, trust, permission, or goal completion. Mirror, Window, and Social retain the founding meanings. Fixture roles are task-specific. A person's guitar-learning aspiration can be relevant to a teacher without ranking the person overall.

## Reproduction and provenance

Primary references read before execution: [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [Sentence Transformers similarity documentation](https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html). The card describes an English 384-dimensional sentence encoder, Apache 2.0 license, and default truncation at 256 word pieces. Its training objective is semantic similarity, not compliance, truthful skill verification, or intent entailment.

- Execution: macOS arm64, CPU, Python 3.12.13 in `/tmp/begin-embedding-eval`.
- Model revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- `model.safetensors` SHA-256: `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
- Corpus SHA-256: `b91f96f6bcf27f71e34e99c9e91440996b167f67804cb99971242fc9c0fbf6d8`.
- Output: L2-normalized 384-dimensional vectors; pairwise dot product equals cosine.
- Dependencies, all downloaded-file hashes, per-case scores and gates: `experiments/embeddings/results.json`. Exact installed versions: `requirements.lock` in the same directory.

See the experiment README and `run.py` for executable reproduction. Network downloads occurred during setup; inference used local CPU weights with remote code disabled. Models were not trained or fine-tuned here. Corpus, labels, and thresholds were fixed before inference; thresholds were .3 for existing token baselines and .5 for MiniLM. They were not calibrated or selected using these results. Different thresholds limit direct method comparisons.

## Results

All mechanisms apply the same explicit consent, purpose, language, location, role, and overlapping-availability gates before accepting a match. Relevance thresholds never override these gates. An aspiration/fact category label is recorded but deliberately not a hard gate: the experiment asks whether text similarity alone makes that distinction. Self-declared role and availability metadata are not independently verified.

| Mechanism | True positive | False positive | True negative | False negative | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing lexical cosine | 3 | 6 | 8 | 7 | .333 | .300 |
| Existing curated concepts | 5 | 5 | 9 | 5 | .500 | .500 |
| Pretrained MiniLM cosine | 9 | 5 | 9 | 1 | .643 | .900 |

All seven structurally ineligible cases were blocked, including a fact-only teacher advertisement without an offer role. MiniLM matched nine of ten labeled positive pairs, including the French and Spanish examples; those two examples do not establish multilingual quality for an English-tagged model. It missed the vegetable-growing / kitchen-garden paraphrase (cosine .386).

Five MiniLM false positives remain despite otherwise eligible metadata:

| Candidate against the corresponding request | Cosine | Failure |
| --- | ---: | --- |
| “I do not teach guitar” | .745 | Negation |
| Python knowledge but explicit refusal to help | .827 | Willingness |
| Former teacher who no longer teaches | .675 | Temporal capability |
| Wants to become a teacher but cannot yet play | .752 | Aspiration treated as capability |
| Sells vegetable photographs versus growing vegetables | .516 | Topic similarity versus useful contribution |

This is direct evidence that cosine relevance cannot establish readiness or mutual fit. Consent metadata alone also cannot repair contradictory natural-language willingness. A verifier must keep protocol compliance separate from semantic matching, and the voluntary response/acceptance workflow must resolve participant willingness. Explicit capability statements, time-aware constraints, and independently evaluated entailment or reranking mechanisms are candidates for further experiments, not implemented guarantees.

## Limits and next gates

The corpus has 10 positive and 14 negative labels chosen by one agent, is small and synthetic, and is not founder-reviewed or population representative. Labels encode usefulness judgments that humans may disagree with. The curated vocabulary was created earlier and may fit some examples; model training overlap with generic phrases cannot be ruled out. There is no confidence interval claim, held-out threshold calibration, production selection, or cross-model generalization claim.

No real intentions or vectors were uploaded. This is not private matching: representations and text are plaintext in the experiment process, and embeddings can reveal information. Before adopting a method, use founder-reviewed scenarios, an independently frozen larger test set, calibration separated from evaluation, explicit information-retention and misleading-inference tests, and interoperability tests tied to exact method/model contracts. Goal completion still requires independent task outcome evidence.
