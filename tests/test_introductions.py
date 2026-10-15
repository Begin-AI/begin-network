"""Unknown-key contact capability does not replace mutual disclosure permission."""
import copy
from pathlib import Path
import tempfile
import unittest

from begin_network.encoders import SyntheticEncoder
from begin_network.envelope import Rejected, decode, generate_key
from begin_network.runtime_bridge import Participant, BlindRelay
import test_runtime_bridge as bridge_fixture


class IntroductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = 100
        self.clock = lambda: self.now
        self.a = Participant(self.root / 'a', encoder=SyntheticEncoder(), clock=self.clock)
        self.b = Participant(self.root / 'b', encoder=SyntheticEncoder(), clock=self.clock)
        self.relay = BlindRelay(self.root / 'relay.sqlite', 'independent-relay',
            {p.id: decode(p.signing['public']) for p in (self.a, self.b)}, clock=self.clock)
        self.publisher = generate_key()
        bridge_fixture.BridgeTests.publish(self)
        bridge_fixture.BridgeTests.form(self, self.a, 'need', 'seek')
        bridge_fixture.BridgeTests.form(self, self.b, 'offer', 'offer')
        self.pool = 'a' * 64
        for participant in (self.a, self.b):
            participant.configure_discovery_pools([self.pool])
        self.offer = self.b.offer_discovery('offer', self.pool)
        self.card = self.offer['card']

    def tearDown(self):
        self.a.close(); self.b.close(); self.relay.close(); self.tmp.cleanup()

    def contact(self, retry='one'):
        return self.a.contact_discovered('need', self.card, 'Synthetic sealed private request.', idempotency_key=retry)['request_id']

    def proposed(self):
        request = self.contact()
        self.a.flush(self.relay); self.b.poll(self.relay)
        self.b.flush(self.relay); self.a.poll(self.relay)
        return request

    def test_unfamiliar_keys_introduction_accept_disclose_reply(self):
        self.assertEqual(self.a.records('peers'), {})
        self.assertEqual(self.b.records('peers'), {})
        request = self.proposed()
        self.assertEqual(self.a.get('threads', request)['status'], 'proposed')
        self.assertEqual(self.b.records('query_budgets'), {})  # No extra owner-local vector disclosure.
        with self.assertRaises(Rejected): self.a.disclose(request)
        self.b.accept(request); self.b.flush(self.relay); self.a.poll(self.relay)
        self.a.disclose(request); self.a.flush(self.relay); self.b.poll(self.relay)
        self.b.reply(request, 'Synthetic response.', idempotency_key='answer')
        self.b.flush(self.relay); self.a.poll(self.relay)
        self.assertTrue(any(m.get('text') == 'Synthetic response.' for m in self.a.inbox()))

    def test_one_use_invitation_and_durable_retry(self):
        request = self.contact()
        packet = next(iter(self.a.records('outbox').values()))
        self.b.receive(packet)
        self.b.close()
        self.b = Participant(self.root / 'b', encoder=SyntheticEncoder(), clock=self.clock)
        self.assertTrue(self.b.receive(packet)['duplicate'])
        self.assertEqual(self.contact(), request)
        self.contact('two')
        # UUID ordering is arbitrary; select packet that was not the original.
        new_packet = next(p for p in self.a.records('outbox').values() if p != packet)
        with self.assertRaisesRegex(Rejected, 'used'): self.b.receive(new_packet)
        self.assertEqual(len(self.b.records('threads')), 1)

    def test_revocation_blocks_initial_contact_and_later_disclosure(self):
        request = self.proposed()
        self.b.accept(request); self.b.flush(self.relay); self.a.poll(self.relay)
        self.b.revoke_discovery(self.offer['invitation_id'])
        self.a.disclose(request)
        packet = next(iter(self.a.records('outbox').values()))
        with self.assertRaisesRegex(Rejected, 'revoked'): self.b.receive(packet)
        self.assertFalse(any(m['kind'] == 'description' for m in self.b.inbox()))

    def test_withdraw_before_contact(self):
        self.contact()
        self.b.revoke_discovery(self.offer['invitation_id'])
        with self.assertRaises(Rejected): self.b.receive(next(iter(self.a.records('outbox').values())))
        self.assertEqual(self.b.records('peers'), {})

    def test_edit_and_retirement_invalidate_invitation(self):
        self.contact()
        self.b.retire_intention('offer', 1)
        with self.assertRaises(ValueError): self.b.receive(next(iter(self.a.records('outbox').values())))
        self.assertEqual(self.b.records('peers'), {})

    def test_expiry_wrong_pool_and_tampered_keys_fail_closed(self):
        card = copy.deepcopy(self.card)
        card['identity']['encryption_public'] = self.a.encryption['public']
        with self.assertRaises(Rejected):
            self.a.contact_discovered('need', card, 'Synthetic', idempotency_key='bad')
        self.a.configure_discovery_pools([])
        with self.assertRaisesRegex(Rejected, 'pool'): self.contact()
        self.a.configure_discovery_pools([self.pool])
        self.now = 800
        with self.assertRaises(Rejected): self.contact()
        self.assertEqual(self.a.records('peers'), {})

    def test_decline_is_terminal(self):
        request = self.proposed()
        self.b.decline(request); self.b.flush(self.relay); self.a.poll(self.relay)
        with self.assertRaises(Rejected): self.a.disclose(request)
        with self.assertRaises(Rejected): self.b.accept(request)

    def test_self_certified_key_does_not_admit_a_normal_query(self):
        a, b = self.a, self.b
        a.pin_peer(b.identity()); b.pin_peer(a.identity())
        grant = b.allow_matching(a.id, 'offer')['grant']
        a.discover('need', b.id, grant, 'Synthetic', idempotency_key='ordinary')
        packet = next(iter(a.records('outbox').values()))
        packet['signing_public'] = a.signing['public']
        b.db.execute("DELETE FROM records WHERE namespace='peers'")
        with self.assertRaisesRegex(Rejected, 'only permits introduction'): b.receive(packet)
        self.assertEqual(b.records('peers'), {})
        self.assertEqual(b.records('query_budgets'), {})

    def test_model_change_and_removed_pool_invalidate_invitation(self):
        self.contact()
        packet = next(iter(self.a.records('outbox').values()))
        self.b.encoder.model = 'unapproved-new-model'
        with self.assertRaisesRegex(Rejected, 'representation changed'): self.b.receive(packet)
        self.b.encoder = SyntheticEncoder()
        self.b.configure_discovery_pools([])
        with self.assertRaisesRegex(Rejected, 'pool'): self.b.receive(packet)
        self.assertEqual(self.b.records('peers'), {})

    def test_contact_permission_cannot_outlive_either_availability(self):
        long_offer = self.b.offer_discovery('offer', self.pool, ttl=3600)
        self.assertEqual(long_offer['expires_at'], 900)
        bridge_fixture.BridgeTests.form(self, self.a, 'need', 'seek', available_until=150, expected_revision=1)
        request = self.a.contact_discovered('need', long_offer['card'], 'Synthetic', idempotency_key='short')['request_id']
        self.assertEqual(self.a.get('threads', request)['expires'], 150)


if __name__ == '__main__':
    unittest.main()
