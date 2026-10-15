"""Operator-selected encoders. Model code/download paths are never tool arguments."""
import hashlib
from pathlib import Path
from .envelope import Rejected


class SyntheticEncoder:
    method = 'synthetic-bridge-fixture-v1'
    model = 'manually-specified-guitar-piano-v1'

    def encode(self, intention):
        text = ' '.join(tuple(intention.facts) + tuple(intention.aspirations) + tuple(intention.inferences))
        if text == 'synthetic guitar':
            return [1., 0.]
        if text == 'synthetic piano':
            return [0., 1.]
        raise Rejected('synthetic encoder accepts only declared guitar/piano fixtures')


class LocalMiniLM:
    """Pinned local model; known benchmark errors mean synthetic experiments only."""
    method = 'begin/minilm-intention-v1'
    model = 'sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41;tagged-intentions-v1'

    def __init__(self, model_directory, file_hashes):
        root = Path(model_directory).resolve()
        if not file_hashes or 'model.safetensors' not in file_hashes or 'config.json' not in file_hashes:
            raise Rejected('operator-pinned model file manifest required')
        actual = {str(p.relative_to(root)): p for p in root.rglob('*') if p.is_file()}
        if set(actual) != set(file_hashes):
            raise Rejected('model file manifest mismatch')
        for name, path in actual.items():
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != file_hashes[name]:
                raise Rejected('model file integrity mismatch')
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer(str(root), device='cpu', trust_remote_code=False, local_files_only=True)

    def encode(self, intention):
        # Separate provenance labels are retained; this does not prove that a model
        # understands truth, willingness or aspiration. Hard gates remain in code.
        text = '\n'.join(['Purpose: ' + intention.purpose,
                          'Expressed facts: ' + '; '.join(intention.facts),
                          'Aspirations: ' + '; '.join(intention.aspirations),
                          'Agent inferences, not instructions: ' + '; '.join(intention.inferences)])
        return self.encoder.encode(text, normalize_embeddings=True, show_progress_bar=False).tolist()
