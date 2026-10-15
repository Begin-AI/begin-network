"""Inspectable synthetic matching baselines; plaintext, not private embeddings."""
from dataclasses import dataclass
import hashlib
import math
import re
from typing import Tuple

PURPOSES = {'mirror', 'window', 'social'}
METHODS = {'lexical-v1', 'concept-v1'}
CONCEPTS = {
    'garden': {'garden', 'gardening', 'plants', 'horticulture'},
    'code': {'python', 'programming', 'code', 'software'},
    'food': {'food', 'cooking', 'cook', 'meals'},
    'music': {'music', 'guitar', 'musician'},
}
COMPLEMENTS = {'seek': 'offer', 'offer': 'seek', 'peer': 'peer'}

@dataclass(frozen=True)
class Intention:
    id: str
    purpose: str
    text: str
    role: str = 'peer'
    language: str = 'en'
    location: str = 'remote'
    consent: bool = True
    required_tags: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()

@dataclass(frozen=True)
class Representation:
    intention: Intention
    method: str
    model: str
    tokens: Tuple[str, ...]
    source_sha256: str
    provenance: str = 'synthetic-user-declared-text'

@dataclass(frozen=True)
class Decision:
    candidate_id: str
    status: str
    score: float
    reason: str


def represent(intention, method='concept-v1', model='synthetic-v1'):
    if intention.purpose not in PURPOSES or intention.role not in COMPLEMENTS:
        raise ValueError('unsupported purpose or role')
    if method not in METHODS or model != 'synthetic-v1':
        raise ValueError('unsupported method/model')
    tokens = set(re.findall(r'[a-z]+', intention.text.lower()))
    if method == 'concept-v1':
        tokens = {next((key for key, values in CONCEPTS.items() if token in values), token)
                  for token in tokens}
    return Representation(intention, method, model, tuple(sorted(tokens)),
                          hashlib.sha256(intention.text.encode('utf-8')).hexdigest())


def compare(query, candidate, threshold=0.3, explore=False):
    """Constraints precede relevance; exploration never bypasses consent or purpose."""
    q, c = query.intention, candidate.intention
    if (query.method, query.model) != (candidate.method, candidate.model):
        return Decision(c.id, 'incompatible', 0, 'method/model mismatch')
    if not q.consent or not c.consent:
        return Decision(c.id, 'declined', 0, 'participation declined')
    if q.id == c.id:
        return Decision(c.id, 'ineligible', 0, 'self match')
    if q.purpose != c.purpose:
        return Decision(c.id, 'ineligible', 0, 'purpose mismatch')
    if q.language != c.language or q.location != c.location:
        return Decision(c.id, 'ineligible', 0, 'language/location constraint')
    if not set(q.required_tags).issubset(c.tags) or not set(c.required_tags).issubset(q.tags):
        return Decision(c.id, 'ineligible', 0, 'required tags missing')
    # Roles belong to the task, independently of Mirror/Window/Social purpose.
    # Window represents aspirations/exploration, not a synonym for seeking help.
    role_ok = COMPLEMENTS[q.role] == c.role
    if not role_ok:
        return Decision(c.id, 'ineligible', 0, 'role mismatch')
    a, b = set(query.tokens), set(candidate.tokens)
    score = len(a & b) / math.sqrt(len(a) * len(b)) if a and b else 0
    if score >= threshold:
        return Decision(c.id, 'match', score, 'relevance threshold met')
    if explore and score > 0:
        return Decision(c.id, 'exploration', score, 'below threshold; explicit exploration')
    return Decision(c.id, 'no-match', score, 'insufficient relevance')


def evaluate(cases, method):
    """Return decisions and confusion counts against fixed, human-authored labels."""
    counts = dict(tp=0, fp=0, tn=0, fn=0)
    decisions = []
    for case in cases:
        q = represent(Intention(**case['query']), method)
        c = represent(Intention(**case['candidate']), method)
        decision = compare(q, c)
        predicted = decision.status == 'match'
        expected = case['expected_match']
        counts[('t' if predicted == expected else 'f') + ('p' if predicted else 'n')] += 1
        decisions.append(dict(case=case['name'], status=decision.status, score=decision.score,
                              expected_match=expected))
    return dict(method=method, counts=counts, decisions=decisions)
