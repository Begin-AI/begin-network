"""Durable participant-owned discovery state; network tools never choose trust anchors."""
from .discovery_client import RemotePool
from .runtime_bridge import require
from .shared_index import enroll, fingerprint, revocations


class DiscoveryRunner:
    def __init__(self, participant, configs):
        self.participant = participant
        self.configs = configs
        self.pools = {name: RemotePool(config) for name, config in configs.items()}
        require(all(name == config['pool'] for name, config in configs.items()), 'pool configuration key mismatch')

    def selected(self, pool):
        require(pool in self.pools and pool in self.participant.get('discovery_policy', 'pools'), 'pool not selected')
        return self.pools[pool]

    def identifier(self, pool, idempotency_key):
        require(isinstance(idempotency_key, str) and 1 <= len(idempotency_key) <= 128, 'bounded idempotency key required')
        return fingerprint({'pool': pool, 'key': idempotency_key})

    def publish(self, pool, intention_id, idempotency_key, minimum_score=500000):
        remote = self.selected(pool)
        p = self.participant
        item, representation = p.representation(intention_id)
        identifier = self.identifier(pool, idempotency_key)
        digest = fingerprint([intention_id, item.revision, representation, minimum_score])
        record = p.get('network_enrollments', identifier)
        if record is None:
            require(len(p.records('network_enrollments')) < 8, 'runner enrollment budget exhausted')
            offer = p.offer_discovery(intention_id, pool)
            owner, uploads = enroll(offer['card'], representation, pool, remote.nodes, now=p.now(), minimum_score=minimum_score)
            record = {'pool': pool, 'digest': digest, 'owner': owner, 'uploads': uploads,
                      'invitation': offer['invitation_id'], 'state': 'pending'}
            p.put('network_enrollments', identifier, record)  # Before any network side effects.
        require(record['digest'] == digest and record['state'] != 'withdrawn' and 'withdrawals' not in record,
                'conflicting or withdrawn enrollment')
        p._live_invitation(record['invitation'])
        remote.upload(self.configs[pool]['enrollment_key'], record['uploads'])
        record['state'] = 'enrolled'
        p.put('network_enrollments', identifier, record)
        return {'enrollment_id': identifier, 'state': record['state'], 'expires_at': record['owner']['expires']}

    def withdraw(self, enrollment_id):
        p = self.participant
        record = p.get('network_enrollments', enrollment_id)
        require(record is not None, 'unknown enrollment')
        remote = self.selected(record['pool'])
        p.revoke_discovery(record['invitation'])  # Local consent stops even if a node is unavailable.
        if record['state'] != 'withdrawn':
            if 'withdrawals' not in record:
                record['withdrawals'] = revocations(record['owner'], remote.nodes, now=p.now())
                p.put('network_enrollments', enrollment_id, record)
            remote.upload(self.configs[record['pool']]['enrollment_key'], record['withdrawals'])
            record['state'] = 'withdrawn'
            p.put('network_enrollments', enrollment_id, record)
        return {'enrollment_id': enrollment_id, 'state': record['state']}

    def search(self, pool, intention_id, idempotency_key, minimum_score=500000):
        remote = self.selected(pool)
        p = self.participant
        item, representation = p.representation(intention_id)
        identifier = self.identifier(pool, idempotency_key)
        digest = fingerprint([intention_id, item.revision, representation, minimum_score])
        record = p.get('network_searches', identifier)
        if record is None:
            require(sum(r['pool'] == pool for r in p.records('network_searches').values()) < 3, 'runner search budget exhausted')
            record = {'pool': pool, 'digest': digest, 'intention': intention_id, 'revision': item.revision,
                      'job': remote.plan(representation, p, minimum_score=minimum_score)}
            p.put('network_searches', identifier, record)
        require(record['digest'] == digest, 'conflicting search retry')
        remote.start(record['job'], p)
        return {'search_id': identifier, 'state': 'submitted', 'expires_at': record['job']['session']['expires_at']}

    def check(self, search_id):
        p = self.participant
        record = p.get('network_searches', search_id)
        require(record is not None, 'unknown search')
        p.representation(record['intention'], record['revision'])
        result = self.selected(record['pool']).poll(record['job'], p)
        if result['state'] == 'complete':
            record['matches'] = {fingerprint(card): card for card in result['cards']}
            p.put('network_searches', search_id, record)
            return {'state': 'complete', 'matches': [{'match_id': key, 'identity': card['identity']}
                                                     for key, card in record['matches'].items()]}
        return result

    def contact(self, search_id, match_id, description, idempotency_key):
        p = self.participant
        record = p.get('network_searches', search_id)
        require(record is not None and match_id in record.get('matches', {}), 'unknown completed match')
        self.selected(record['pool']).check_job(record['job'], p)
        p.representation(record['intention'], record['revision'])
        return p.contact_discovered(record['intention'], record['matches'][match_id], description,
                                    idempotency_key=idempotency_key)
