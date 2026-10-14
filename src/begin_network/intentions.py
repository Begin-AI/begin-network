"""Participant-controlled synthetic intentions and revision-bound vector contracts."""
from dataclasses import dataclass
import math
from typing import Tuple


class InvalidIntention(ValueError):
    pass


@dataclass(frozen=True)
class Intention:
    id: str
    revision: int
    purpose: str
    facts: Tuple[str, ...]
    aspirations: Tuple[str, ...]
    inferences: Tuple[str, ...]
    consent: bool
    disclosure: Tuple[str, ...]
    role: str
    available_from: int
    available_until: int
    expires_at: int
    retired: bool = False


@dataclass(frozen=True)
class Vector:
    intention_id: str
    revision: int
    purpose: str
    method: str
    model: str
    dimension: int
    normalization: str
    language: str
    values: Tuple[float, ...]


def _texts(values):
    if not isinstance(values, (tuple, list)):
        raise InvalidIntention('text categories must be lists or tuples')
    return tuple(values)


class Store:
    """Local reference store, not a signed database or network authority."""
    def __init__(self):
        self._intentions = {}

    def create(self, id, purpose, facts=(), aspirations=(), inferences=(), consent=False,
               disclosure=(), role='peer', available_from=0, available_until=1,
               expires_at=1):
        if id in self._intentions:
            raise InvalidIntention('identifier already exists')
        item = Intention(id, 1, purpose, _texts(facts), _texts(aspirations), _texts(inferences),
                         consent, _texts(disclosure), role, available_from, available_until, expires_at)
        self._validate(item)
        self._intentions[id] = item
        return item

    def get(self, id):
        return self._intentions[id]

    def edit(self, id, expected_revision, **changes):
        from dataclasses import replace
        current = self.get(id)
        if current.revision != expected_revision or current.retired:
            raise InvalidIntention('stale revision or retired intention')
        editable = {'facts', 'aspirations', 'inferences', 'consent', 'disclosure', 'role',
                    'available_from', 'available_until', 'expires_at'}
        if set(changes) - editable:
            raise InvalidIntention('immutable or unknown field')
        for field in ('facts', 'aspirations', 'inferences', 'disclosure'):
            if field in changes:
                changes[field] = _texts(changes[field])
        updated = replace(current, revision=current.revision + 1, **changes)
        self._validate(updated)
        self._intentions[id] = updated
        return updated

    def retire(self, id, expected_revision):
        from dataclasses import replace
        current = self.get(id)
        if current.revision != expected_revision:
            raise InvalidIntention('stale revision')
        updated = replace(current, revision=current.revision + 1, retired=True, consent=False)
        self._intentions[id] = updated
        return updated

    @staticmethod
    def _validate(item):
        if not isinstance(item.id, str) or not item.id or not isinstance(item.purpose, str) or item.purpose not in {'mirror', 'window', 'social'}:
            raise InvalidIntention('invalid identity/purpose')
        if not isinstance(item.role, str) or item.role not in {'seek', 'offer', 'peer'} or type(item.consent) is not bool:
            raise InvalidIntention('invalid role/consent')
        if any(type(n) is not int for n in (item.available_from, item.available_until, item.expires_at)):
            raise InvalidIntention('integer timestamps required')
        if not item.available_from < item.available_until <= item.expires_at:
            raise InvalidIntention('invalid timing bounds')
        for field in (item.facts, item.aspirations, item.inferences, item.disclosure):
            if any(not isinstance(s, str) or not s for s in field):
                raise InvalidIntention('nonempty text fields required')
        if not set(item.disclosure) <= {'facts', 'aspirations', 'inferences'}:
            raise InvalidIntention('unknown disclosure boundary')

    def disclose(self, id, now):
        item = self.get(id)
        self._active(item, now)
        return {field: getattr(item, field) for field in item.disclosure}

    @staticmethod
    def _active(item, now):
        if type(now) is not int:
            raise InvalidIntention('integer current timestamp required')
        if item.retired or not item.consent or now >= item.expires_at:
            raise InvalidIntention('retired, declined, or expired')

    def vector(self, id, values, method, model, language='en'):
        item = self.get(id)
        values = tuple(values)
        if not values or any(type(v) not in (int, float) or abs(v) > 1e150 or not math.isfinite(v) for v in values):
            raise InvalidIntention('finite numeric vector required')
        norm = math.sqrt(sum(v*v for v in values))
        if not math.isfinite(norm) or norm == 0 or not all(isinstance(s, str) and s for s in (method, model, language)):
            raise InvalidIntention('nonzero vector and method metadata required')
        return Vector(id, item.revision, item.purpose, method, model, len(values), 'l2', language,
                      tuple(v/norm for v in values))

    def compare(self, left, right, now, roles=('seek', 'offer')):
        """Caller supplies task role relation; purpose never implies a universal role."""
        items = []
        for vector in (left, right):
            item = self.get(vector.intention_id)
            self._active(item, now)
            if type(vector.revision) is not int or vector.revision != item.revision or vector.purpose != item.purpose:
                raise InvalidIntention('stale representation')
            if type(vector.dimension) is not int or not isinstance(vector.values, (tuple,list)) or vector.dimension != len(vector.values) or vector.normalization != 'l2' or any(type(v) not in (int,float) or abs(v)>1 or not math.isfinite(v) for v in vector.values) or not math.isclose(sum(v*v for v in vector.values), 1, abs_tol=1e-9):
                raise InvalidIntention('invalid vector contract')
            items.append(item)
        if left.intention_id == right.intention_id:
            raise InvalidIntention('self comparison')
        contract = lambda v: (v.purpose, v.method, v.model, v.dimension, v.normalization, v.language)
        if contract(left) != contract(right):
            raise InvalidIntention('incompatible representation contract')
        if tuple(i.role for i in items) != tuple(roles):
            raise InvalidIntention('task role constraint')
        start = max(now, *(i.available_from for i in items))
        end = min(i.available_until for i in items)
        if start >= end:
            raise InvalidIntention('no remaining shared availability')
        return sum(a*b for a,b in zip(left.values, right.values))
