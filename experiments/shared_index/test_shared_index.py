"""Protocol behavior and leakage boundaries; synthetic same-host experiment."""
import copy
import math
from pathlib import Path
import tempfile
import time
import unittest

from begin_network.encoders import SyntheticEncoder
from begin_network.envelope import Rejected, decode, generate_key
from begin_network.runtime_bridge import Participant, BlindRelay, canonical
from begin_network.shared_index import (IndexNode, PARAMETERS, contract, fingerprint, open_json, private_row,
    public_snapshot, reconstruct, revocations, signed)
from harness import Committee

MEASUREMENTS = []


class Encoder(SyntheticEncoder):
    def encode(self, intention):
        if intention.aspirations == ('synthetic unfamiliar option',) or intention.aspirations == ['synthetic unfamiliar option']:
            return [0.3, math.sqrt(0.91)]
        return super().encode(intention)


class SharedIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='begin-shared-index-')
        self.root = Path(self.tmp.name)
        self.pool = Committee(self.root / 'pool')
        self.participants = []
        self.now = int(time.time())
        self.requester = self.participant('requester', 'seek')
        self.candidate = self.participant('candidate', 'offer')
        self.owner, self.uploads, self.offer = self.pool.enroll(self.candidate, 'intention')
        _, self.query = self.requester.representation('intention')

    def tearDown(self):
        self.pool.close()
        for participant in self.participants:
            participant.close()
        self.tmp.cleanup()

    def participant(self, name, role, purpose='window', text='synthetic guitar', **changes):
        participant = Participant(self.root / name, encoder=Encoder())
        options = dict(purpose=purpose, role=role, facts=[], aspirations=[text], inferences=[],
                       consent=True, disclosure=['aspirations'], available_from=self.now,
                       available_until=self.now+600, expires_at=self.now+900)
        options.update(changes)
        participant.set_intention('intention', **options)
        self.participants.append(participant)
        return participant

    def test_private_candidate_scan_exploration_and_purpose_constraints(self):
        other = self.participant('piano', 'offer', text='synthetic piano')
        self.pool.enroll(other, 'intention')
        self.pool.enroll(self.participant('wrong-role', 'seek'), 'intention')
        mirror = self.participant('mirror', 'offer', purpose='mirror')
        self.pool.enroll(mirror, 'intention')
        self.pool.enroll(self.participant('later', 'offer', available_from=self.now+650, available_until=self.now+700), 'intention')
        unfamiliar = self.participant('unfamiliar', 'offer', text='synthetic unfamiliar option')
        self.pool.enroll(unfamiliar, 'intention', minimum_score=200000)
        strict = self.participant('strict', 'offer', text='synthetic unfamiliar option')
        self.pool.enroll(strict, 'intention', minimum_score=500000)
        self.assertEqual(self.requester.records('peers'), {})
        cards, session, results, configs, boxes = self.pool.search(self.query, self.requester)
        self.assertEqual([c['identity']['address'] for c in cards], [self.candidate.id])
        self.assertEqual(len({m['pid'] for m in self.pool.last_metrics}), 3)
        MEASUREMENTS.append({'case': 'unfamiliar-candidate-search', 'dimensions': 2, 'records': 7,
                             'parties': self.pool.last_metrics})
        # Neither complete keys, the private card nor the query occurs in node inputs.
        for node, config in zip(self.pool.nodes, configs):
            raw = canonical(node.snapshot(session['contract'])) + canonical(config)
            self.assertNotIn(self.offer['card']['token'], raw)
            self.assertNotIn(self.candidate.id, raw)
            self.assertNotIn('synthetic guitar', raw)
            self.assertNotEqual(config['query_share'], private_row(self.query))
        # Completed retry uses the persisted encrypted output, with no new MPC or budget charge.
        self.assertEqual(self.pool.run(configs), results)
        self.assertEqual(self.pool.last_metrics, [])
        for node in self.pool.nodes:
            self.assertEqual(node.db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)
        # A requester needs all three fresh additive outputs; two cannot open a card.
        with self.assertRaises(Rejected):
            reconstruct(session, results[:2], self.pool.pins, self.requester.encryption['private'], boxes, now=int(time.time()))
        partial = [open_json(r['box'], self.requester.encryption['private'], session['id'], self.requester.id) for r in results[:2]]
        from begin_network.shared_index import field_type
        partial_values = [(a+b) % field_type().modulus for a,b in zip(*partial)]
        self.assertFalse(all(v in (0, 1) for v in partial_values[::33]))
        cards, *_ = self.pool.search(self.query, self.requester, minimum_score=200000)
        self.assertEqual({c['identity']['address'] for c in cards}, {self.candidate.id, unfamiliar.id})
        mirror_query = dict(self.query, purpose='mirror')
        cards, *_ = self.pool.search(mirror_query, self.requester)
        self.assertEqual([c['identity']['address'] for c in cards], [mirror.id])

    def test_unknown_participants_complete_existing_encrypted_exchange(self):
        cards, *_ = self.pool.search(self.query, self.requester)
        a, b = self.requester, self.candidate
        self.assertEqual(a.records('peers'), {})
        self.assertEqual(b.records('peers'), {})
        a.configure_discovery_pools([self.pool.id])
        relay = BlindRelay(self.root / 'relay.sqlite', 'independent-relay',
                           {p.id: decode(p.signing['public']) for p in (a, b)})
        # Use the existing signed bootstrap validator, including a failed first mirror.
        import sys
        sys.path.insert(0, str(Path(__file__).parents[2] / 'tests'))
        import test_runtime_bridge as fixture
        self.a, self.b, self.relay, self.publisher = a, b, relay, generate_key()
        fixture.BridgeTests.publish(self)
        try:
            request = a.contact_discovered('intention', cards[0], 'Synthetic private discovery request.', idempotency_key='unknown')['request_id']
            with self.assertRaises(Rejected): a.disclose(request)
            a.flush(relay); b.poll(relay); b.flush(relay); a.poll(relay)
            self.assertEqual(b.records('query_budgets'), {})
            with self.assertRaises(Rejected): a.disclose(request)
            b.accept(request); b.flush(relay); a.poll(relay)
            a.disclose(request); a.flush(relay); b.poll(relay)
            b.reply(request, 'Synthetic response from an unfamiliar participant.', idempotency_key='reply')
            b.flush(relay); a.poll(relay)
            self.assertTrue(any('unfamiliar' in m.get('text', '') for m in a.inbox()))
            a.reply(request, 'Synthetic related follow-up.', idempotency_key='followup')
            a.flush(relay); b.poll(relay)
            self.assertTrue(any('follow-up' in m.get('text', '') for m in b.inbox()))
            self.assertNotIn(b'Synthetic private discovery request.', (self.root / 'relay.sqlite').read_bytes())
        finally:
            relay.close()

    def test_revocation_rollback_wrong_owner_and_inflight_snapshot(self):
        session, configs = self.pool.prepare(self.query, self.requester)
        updates = revocations(self.owner, self.pool.keys, now=int(time.time()))
        for node, update, enrollment in zip(self.pool.nodes, updates, self.uploads):
            node.apply(update)
            self.assertTrue(node.apply(update)['duplicate'])
            self.assertEqual(node.snapshot(contract(self.query)), [])
            with self.assertRaises(Rejected): node.apply(enrollment)
        self.assertEqual(self.pool.run(configs, expect_failure=True), [])
        self.assertTrue(all('PREFLIGHT_OK' not in (d / 'worker.log').read_text() for d in self.pool.dirs))
        # A different signing key cannot revoke the same record.
        fake = generate_key()
        from begin_network.envelope import strict_json
        body = strict_json(decode(updates[0]['token'].split('.')[1]))['body']
        body['revision'] += 1
        forged = {'public': fake['public'], 'token': signed(fake, self.pool.keys[0]['kid'], 'forged', body,
                  int(time.time()), int(time.time())+60, kind='revocation')}
        with self.assertRaisesRegex(Rejected, 'signer'): self.pool.nodes[0].apply(forged)

    def test_session_tampering_and_wrong_result_recipient_rejected(self):
        cards, session, results, configs, boxes = self.pool.search(self.query, self.requester)
        wrong = self.participant('wrong', 'seek')
        with self.assertRaises(Rejected):
            reconstruct(session, results, self.pool.pins, wrong.encryption['private'], boxes, now=int(time.time()))
        changed = copy.deepcopy(results)
        changed[0]['box']['ciphertext'] = changed[0]['box']['ciphertext'][::-1]
        with self.assertRaises(Rejected):
            reconstruct(session, changed, self.pool.pins, self.requester.encryption['private'], boxes, now=int(time.time()))
        for config in configs:
            config['consents'] = []
        self.assertEqual(self.pool.run(configs, expect_failure=True), [])
        self.assertTrue(all('PREFLIGHT_OK' not in (d / 'worker.log').read_text() for d in self.pool.dirs))

    def test_node_loss_requires_whole_independently_selected_pool(self):
        session, configs = self.pool.prepare(self.query, self.requester)
        self.assertEqual(self.pool.run(configs, missing=2, expect_failure=True), [])
        for node in self.pool.nodes[:2]:
            self.assertEqual(node.db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)
        alternate = Committee(self.root / 'alternate')
        try:
            alternate.enroll(self.candidate, 'intention')  # fresh independent shares and explicit enrollment
            cards, *_ = alternate.search(self.query, self.requester)
            self.assertEqual([c['identity']['address'] for c in cards], [self.candidate.id])
            self.assertTrue(set(alternate.pins).isdisjoint(self.pool.pins))
            MEASUREMENTS.append({'case': 'independent-pool-after-node-loss', 'parties': alternate.last_metrics})
        finally:
            alternate.close()

    def test_budget_survives_reopen_and_failed_computation(self):
        node = self.pool.nodes[0]
        for i in range(PARAMETERS['max_queries_per_key']):
            node.reserve({'id': str(i)}, self.requester.id)
        node.close()
        node = IndexNode(self.pool.dirs[0], self.pool.keys[0], self.pool.id)
        self.pool.nodes[0] = node
        with self.assertRaisesRegex(Rejected, 'budget'): node.reserve({'id': 'another'}, self.requester.id)
        with self.assertRaisesRegex(Rejected, 'incomplete'): node.reserve({'id': '0'}, self.requester.id)
        with self.assertRaisesRegex(Rejected, 'conflicting'): node.reserve({'id': '0', 'changed': True}, self.requester.id)

    def test_secret_range_normalization_and_willingness_gates(self):
        for values in ([1001, 0], [0, 0]):
            query = private_row(self.query)
            query[:2] = values
            cards, *_ = self.pool.search(self.query, self.requester, query_override=query)
            self.assertEqual(cards, [])
        query = private_row(self.query)
        query[-1] = 0
        cards, *_ = self.pool.search(self.query, self.requester, query_override=query)
        self.assertEqual(cards, [])

    def test_expiry_removes_shares_and_stale_snapshot_cannot_complete(self):
        session, _ = self.pool.prepare(self.query, self.requester)
        node = self.pool.nodes[0]
        node.reserve(session, self.requester.id)
        update = revocations(self.owner, self.pool.keys, now=int(time.time()))[0]
        node.apply(update)
        with self.assertRaisesRegex(Rejected, 'index changed'): node.complete(session, {'not': 'released'})
        self.assertIsNone(node.db.execute('SELECT result FROM sessions').fetchone()[0])
        other = self.pool.nodes[1]
        other.clock = lambda: self.now + 1000
        self.assertEqual(other.snapshot(contract(self.query)), [])
        stored = other.db.execute('SELECT value FROM records').fetchone()[0]
        self.assertNotIn('shares', stored)
        self.assertNotIn('card_box', stored)


if __name__ == '__main__':
    unittest.main()
