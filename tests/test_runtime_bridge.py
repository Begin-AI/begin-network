"""Real original-runtime integration; distinct owners, blind relay, synthetic inputs."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from begin_network.envelope import VERSION, Rejected, decode, generate_key, sign, verify
from begin_network.discovery_index import ATTESTATION_PROFILE
from begin_network.runtime_bridge import Participant, BlindRelay, canonical
from begin_network.sealed import _decrypt_bound, encryption_key


class FixtureEncoder:
    method = 'synthetic-bridge-fixture-v1'
    model = 'manually-specified-guitar-piano-v1'

    def encode(self, intention):
        # Explicit fixtures only; no claim of semantic understanding.
        text = ' '.join(intention.facts + intention.aspirations + intention.inferences)
        if text == 'synthetic guitar':
            return [1., 0.]
        if text == 'synthetic piano':
            return [0., 1.]
        raise Rejected('unknown synthetic encoder fixture')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = 100
        self.clock = lambda: self.now
        self.a = Participant(self.root / 'a', encoder=FixtureEncoder(), clock=self.clock)
        self.b = Participant(self.root / 'b', encoder=FixtureEncoder(), clock=self.clock)
        self.a.pin_peer(self.b.identity()); self.b.pin_peer(self.a.identity())
        self.relay = BlindRelay(self.root / 'relay.sqlite', 'independent-relay', self.a.keys(), clock=self.clock)
        self.publisher = generate_key()
        self.publish()
        self.form(self.a, 'need', role='seek')
        self.form(self.b, 'offer', role='offer')
        self.grant = self.b.allow_matching(self.a.id, 'offer', max_queries=2)['grant']

    def tearDown(self):
        self.a.close(); self.b.close(); self.relay.close(); self.tmp.cleanup()

    def publish(self):
        index = json.loads((Path(__file__).parents[1] / 'discovery/index.json').read_text())
        stamp = lambda n: datetime.fromtimestamp(n, timezone.utc).isoformat().replace('+00:00', 'Z')
        index['generated_at'] = stamp(self.now)
        index['nodes'] = [{'id': self.relay.id, 'endpoint': 'https://relay.example.org',
                           'capabilities': ['mailbox'], 'expires_at': stamp(self.now + 1000),
                           'trust': 'unverified-advertisement'}]
        raw = canonical(index).encode()
        token = sign({'version': VERSION, 'type': 'response', 'sender': self.publisher['kid'], 'id': 'index',
                      'audience': 'participant-bootstrap', 'issued_at': self.now, 'expires_at': self.now + 1000,
                      'proofs': [], 'body': {'profile': ATTESTATION_PROFILE, 'index_sha256': hashlib.sha256(raw).hexdigest(),
                        'protocol_version': VERSION, 'generated_at': index['generated_at']}}, decode(self.publisher['private']))
        (self.root / 'index.json').write_bytes(raw); (self.root / 'index.jws').write_text(token)
        self.sources = [(self.root / 'offline.json', self.root / 'offline.jws'),
                        (self.root / 'index.json', self.root / 'index.jws')]
        self.pins = {self.publisher['kid']: decode(self.publisher['public'])}
        for participant in (self.a, self.b):
            checked = participant.select_service(self.sources, self.pins, 'participant-bootstrap', service_id=self.relay.id)
            self.assertEqual(checked['rejected_mirrors'], 1)
            self.assertFalse(checked['authority_granted'])

    def form(self, participant, intention_id, role, text='synthetic guitar', **changes):
        options = dict(purpose='window', facts=[], aspirations=[text], inferences=[], role=role,
                       available_from=100, available_until=900, expires_at=1000, consent=True,
                       disclosure=['aspirations'])
        options.update(changes)
        return participant.set_intention(intention_id, **options)

    def send(self, key='query-1'):
        return self.a.discover('need', self.b.id, self.grant, 'Synthetic private question: can we arrange a lesson?', idempotency_key=key)['request_id']

    def match(self):
        request = self.send()
        self.a.flush(self.relay); self.b.poll(self.relay)
        self.b.flush(self.relay); self.a.poll(self.relay)
        return request

    def disclose(self):
        request = self.match()
        self.b.accept(request); self.b.flush(self.relay); self.a.poll(self.relay)
        self.a.disclose(request); self.a.flush(self.relay); self.b.poll(self.relay)
        return request

    def test_full_discovery_authorization_reply_followup_and_reopen(self):
        request = self.disclose()
        description = next(x for x in self.b.inbox() if x['kind'] == 'description')
        self.assertIn('arrange a lesson', description['text'])
        response = self.b.reply(request, 'Synthetic willingness: yes, let us discuss.', idempotency_key='reply-1')
        self.assertEqual(self.b.reply(request, 'Synthetic willingness: yes, let us discuss.', idempotency_key='reply-1')['message_id'], response['message_id'])
        self.b.flush(self.relay)
        old_id = self.a.id
        self.a.close()
        self.a = Participant(self.root / 'a', encoder=FixtureEncoder(), clock=self.clock)
        self.assertEqual(self.a.id, old_id)
        self.a.poll(self.relay)
        message = next(x for x in self.a.inbox() if x['kind'] == 'reply')
        self.assertEqual(message['text'], 'Synthetic willingness: yes, let us discuss.')
        self.a.reply(request, 'Synthetic follow-up: which times?', idempotency_key='followup')
        self.a.flush(self.relay); self.b.poll(self.relay)
        self.assertTrue(any(x.get('text') == 'Synthetic follow-up: which times?' for x in self.b.inbox()))
        self.a.acknowledge(message['message_id'])
        self.assertNotIn(message['message_id'], [x['message_id'] for x in self.a.inbox()])

    def test_description_not_in_query_or_relay_and_relay_cannot_decrypt(self):
        request = self.send()
        packet = next(iter(self.a.records('outbox').values()))
        raw = canonical(packet)
        for secret in ('synthetic guitar', 'arrange a lesson', 'values', 'aspirations', 'need', 'offer'):
            self.assertNotIn(secret, raw)
        outer = verify(packet['token'], self.a.keys(), self.b.id, now=self.now)
        with self.assertRaises(Rejected):
            _decrypt_bound(packet['box'], decode(encryption_key()['private']), outer)
        self.a.flush(self.relay)
        stored = self.relay.mailbox.db.execute('SELECT ciphertext FROM deliveries').fetchone()[0]
        self.assertNotIn(b'arrange a lesson', stored)
        self.assertNotIn(b'private', stored)
        with self.assertRaises(Rejected): self.a.disclose(request)
        self.b.poll(self.relay); self.b.flush(self.relay); self.a.poll(self.relay)
        with self.assertRaises(Rejected): self.a.disclose(request)
        self.assertEqual(self.a.get('threads', request)['status'], 'proposed')
        self.assertFalse(any(x['kind'] == 'description' for x in self.b.inbox()))

    def test_duplicate_crash_recovery_uses_same_signed_output(self):
        request = self.send()
        self.assertEqual(self.send(), request)
        packet = next(iter(self.a.records('outbox').values()))
        self.relay.submit(packet)
        self.b.receive(packet)  # crash before transport ack
        reply = self.b.records('outbox')
        self.b.close(); self.b = Participant(self.root / 'b', encoder=FixtureEncoder(), clock=self.clock)
        self.assertTrue(self.b.receive(packet)['duplicate'])
        self.assertEqual(self.b.records('outbox'), reply)
        self.assertEqual(list(self.b.records('query_budgets').values()), [1])
        self.b.poll(self.relay)
        self.assertEqual(len(self.b.records('inbox')), 1)

    def test_pinned_peer_and_grant_cannot_be_supplied_by_an_advertisement(self):
        identity = self.b.identity(); identity['encryption_public'] = encryption_key()['public']
        with self.assertRaises(Rejected): self.a.pin_peer(identity)
        outsider = generate_key()
        with self.assertRaises(Rejected):
            self.a.discover('need', outsider['kid'], self.grant, 'synthetic', idempotency_key='bad-peer')
        self.assertEqual(len(self.a.records('outbox')), 0)

    def test_tampered_wrong_recipient_wrong_signer_and_conflicting_retries(self):
        self.send()
        packet = next(iter(self.a.records('outbox').values()))
        tampered = copy.deepcopy(packet)
        tampered['box']['ciphertext'] = tampered['box']['ciphertext'][::-1]
        with self.assertRaises(Rejected): self.b.receive(tampered)
        with self.assertRaises(Rejected): self.a.receive(packet)
        forged = copy.deepcopy(packet)
        outer = verify(packet['token'], self.a.keys(), self.b.id, now=self.now)
        stranger = generate_key()
        outer['sender'] = stranger['kid']
        forged['token'] = sign(outer, decode(stranger['private']))
        with self.assertRaises(Rejected): self.b.receive(forged)
        with self.assertRaises(Rejected):
            self.a.discover('need', self.b.id, self.grant, 'changed', idempotency_key='query-1')
        self.assertEqual(self.b.records('query_budgets'), {})

    def test_revocation_edits_and_retirement_stop_future_disclosure(self):
        request = self.match()
        self.b.accept(request); self.b.flush(self.relay); self.a.poll(self.relay)
        grant_id = self.b.get('threads', request)['grant_id']
        self.b.revoke_matching(grant_id)
        self.a.disclose(request)
        packet = next(iter(self.a.records('outbox').values()))
        with self.assertRaises(Rejected): self.b.receive(packet)
        self.assertFalse(any(x['kind'] == 'description' for x in self.b.inbox()))
        self.a.retire_intention('need', 1)
        with self.assertRaises(ValueError): self.a.reply(request, 'synthetic', idempotency_key='after-retirement')

    def test_edit_invalidates_old_query_grant(self):
        self.send()
        self.form(self.b, 'offer', role='offer', expected_revision=1)
        with self.assertRaises(Rejected): self.b.receive(next(iter(self.a.records('outbox').values())))

    def test_cumulative_budget_survives_restart_and_reissued_grant(self):
        self.match()
        self.send('query-2'); self.a.flush(self.relay); self.b.poll(self.relay)
        self.b.close(); self.b = Participant(self.root / 'b', encoder=FixtureEncoder(), clock=self.clock)
        self.grant = self.b.allow_matching(self.a.id, 'offer', max_queries=2)['grant']
        self.send('query-3')
        with self.assertRaises(Rejected): self.b.receive(next(iter(self.a.records('outbox').values())))
        self.assertEqual(list(self.b.records('query_budgets').values()), [2])

    def test_no_match_never_authorizes_and_expiry_stops_processing(self):
        self.form(self.b, 'offer', role='offer', text='synthetic piano', expected_revision=1)
        self.grant = self.b.allow_matching(self.a.id, 'offer')['grant']
        request = self.match()
        self.assertEqual(self.a.get('threads', request)['status'], 'no-match')
        with self.assertRaises(Rejected): self.b.accept(request)
        with self.assertRaises(Rejected): self.a.disclose(request)
        self.now = 1000
        self.assertEqual(self.b.inbox(), [])

    def test_index_required_expiry_and_replacement_without_begin_signer(self):
        self.a.db.execute("DELETE FROM records WHERE namespace='bootstrap'")
        with self.assertRaises(Rejected): self.send()
        self.assertEqual(self.a.records('threads'), {})
        self.publisher = generate_key()
        self.publish()
        self.assertEqual(self.a.get('bootstrap', 'selected')['attested_by'], self.publisher['kid'])
        self.now = 401
        with self.assertRaises(Rejected): self.send()

    def test_mailbox_identity_is_signed_and_not_a_caller_argument(self):
        self.send(); self.a.flush(self.relay)
        token = self.a.signed('request', 'pull-a', self.relay.id, {'operation': 'retrieve'}, 150)
        self.assertEqual(self.relay.retrieve(token), [])
        with self.assertRaises(Rejected): self.relay.retrieve(token)
        self.assertEqual(len(self.relay.mailbox.retrieve(self.b.id)), 1)

    def test_decline_blocks_disclosure_and_response(self):
        request = self.match()
        self.b.decline(request); self.b.flush(self.relay); self.a.poll(self.relay)
        self.assertEqual(self.a.get('threads', request)['status'], 'declined')
        self.assertNotIn('description', self.a.get('threads', request))
        with self.assertRaises(Rejected): self.a.disclose(request)
        with self.assertRaises(Rejected): self.b.accept(request)
        with self.assertRaises(Rejected): self.b.reply(request, 'synthetic', idempotency_key='forbidden')

    def test_out_of_order_acceptance_and_proposal_are_retried(self):
        request = self.send()
        self.a.flush(self.relay); self.b.poll(self.relay)
        self.b.accept(request)
        self.b.flush(self.relay)
        original = self.relay.retrieve
        def reversed_delivery(token):
            result = original(token)
            # Force accepted packet before proposal without trusting mailbox order.
            def kind(delivery):
                packet = json.loads(delivery.ciphertext)
                outer = verify(packet['token'], self.a.keys(), self.a.id, now=self.now)
                return json.loads(_decrypt_bound(packet['box'], decode(self.a.encryption['private']), outer))['kind']
            return sorted(result, key=lambda d: kind(d) != 'accepted')
        self.relay.retrieve = reversed_delivery
        self.a.poll(self.relay)
        self.assertEqual(self.a.get('threads', request)['status'], 'accepted')
        self.assertEqual(self.a.last_delivery_errors, [])

    def test_expired_payloads_removed_but_retry_tombstones_remain(self):
        request = self.disclose()
        self.now = 1100
        self.a.expire(); self.b.expire()
        self.assertEqual(self.a.get('threads', request), {'expires': 700, 'status': 'expired'})
        self.assertEqual(self.a.records('outbox'), {})
        self.assertTrue(self.a.records('submissions'))
        self.assertFalse(any('text' in x for x in self.b.records('inbox').values()))


if __name__ == '__main__':
    unittest.main()
