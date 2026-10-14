# Optional learned-embedding experiment

This directory is outside the core runtime dependencies. It contains a frozen synthetic corpus, a pretrained CPU benchmark, pinned model revision and installed dependency versions, and measured per-case results.

```sh
uv venv --python 3.12 /tmp/begin-embedding-reproduction
uv pip install --python /tmp/begin-embedding-reproduction/bin/python -r experiments/embeddings/requirements.lock
/tmp/begin-embedding-reproduction/bin/python experiments/embeddings/run.py
```

Run from repository root. Initial model download requires internet; cached files can be reused. Results can differ slightly across numerical-library versions/hardware. Model SHA-256 values in `results.json` identify downloaded files. The dependency freeze pins versions, not wheel hashes; it is an experiment record, not a fully reproducible supply-chain lock.

Thresholds and corpus were frozen before inference; no training or threshold selection used evaluation scores. Data is fictional. The corpus is small and intentionally adversarial, not a representative benchmark or founder-approved gold standard. Matching quality does not establish privacy, participant willingness, or authority. See `docs/embedding-evaluation.md`.
