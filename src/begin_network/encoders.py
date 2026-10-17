"""Operator-selected encoders. Model code/download paths are never tool arguments."""
import hashlib
import math
from pathlib import Path
from .envelope import Rejected
from .intentions import PERSPECTIVES, validate_perspectives


def combine_perspectives(intention, encode):
    """One normalized weighted sum; all three owner-selected views contribute.

    This transparent experimental fusion rule is not a validated model of human
    relevance. Consent/availability/roles are enforced separately by the matcher.
    """
    validate_perspectives(intention.perspectives, intention.balance)
    vectors = []
    for name in PERSPECTIVES:
        values = encode(name, intention.perspectives[name])
        if not values or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise Rejected('invalid perspective vector')
        norm = math.sqrt(sum(v*v for v in values))
        if not math.isfinite(norm) or norm <= 0:
            raise Rejected('zero perspective vector')
        vectors.append([v/norm for v in values])
    if len({len(v) for v in vectors}) != 1:
        raise Rejected('inconsistent perspective dimensions')
    merged = [sum(intention.balance[name]*vectors[i][j] for i, name in enumerate(PERSPECTIVES))
              for j in range(len(vectors[0]))]
    norm = math.sqrt(sum(v*v for v in merged))
    if norm < 1e-12:
        raise Rejected('balanced perspectives cancel; revise representation explicitly')
    return [v/norm for v in merged]


class SyntheticEncoder:
    method = 'synthetic-balanced-intention-v2'
    model = 'manually-specified-guitar-piano-balanced-v2'

    def encode_perspective(self, name, values):
        text = ' '.join(values)
        if text == 'synthetic guitar':
            return [1., 0.]
        if text == 'synthetic piano':
            return [0., 1.]
        raise Rejected('synthetic encoder accepts only declared guitar/piano fixtures')

    def encode(self, intention):
        return combine_perspectives(intention, self.encode_perspective)


class LocalMiniLM:
    """Pinned local model; known benchmark errors mean synthetic experiments only."""
    method = 'begin/minilm-balanced-intention-v2'
    model = 'sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41;balanced-perspectives-v2'

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
        def component(name, values):
            # Shared context retains provenance labels. Perspective text is an
            # owner-approved view, not a verified fact or an instruction.
            text = '\n'.join(['Perspective: ' + name,
                              'Owner-approved perspective: ' + '; '.join(values),
                              'Expressed facts: ' + '; '.join(intention.facts),
                              'Aspirations: ' + '; '.join(intention.aspirations),
                              'Agent inferences, not instructions: ' + '; '.join(intention.inferences)])
            return self.encoder.encode(text, normalize_embeddings=True, show_progress_bar=False).tolist()
        return combine_perspectives(intention, component)
