import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from pathlib import Path
from begin_network.coordination import CoordinationError, Mailbox


class MailboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'mailbox.db'
        self.now = 100
        self.box = Mailbox(self.path, clock=lambda: self.now, max_pending=2, max_bytes=8)

    def tearDown(self):
        self.box.close()
        self.tmp.cleanup()

    def submit(self, key='one', recipient='alice', body=b'abc', expiry=200):
        return self.box.submit(key, recipient, body, expiry)

    def test_offline_reopen_and_recipient_scope(self):
        self.submit()
        self.box.close()
        self.box = Mailbox(self.path, clock=lambda: self.now)
        self.assertEqual(self.box.retrieve('bob'), [])
        self.assertFalse(self.box.claim('bob', 'one'))
        self.assertEqual(self.box.retrieve('alice')[0].ciphertext, b'abc')

    def test_claim_ack_retry_does_not_repeat_work(self):
        self.submit()
        other = Mailbox(self.path, clock=lambda: self.now)
        try:
            self.assertTrue(self.box.claim('alice', 'one'))
            self.assertFalse(other.claim('alice', 'one'))
            self.assertFalse(self.box.acknowledge('bob', 'one'))
            self.assertTrue(self.box.acknowledge('alice', 'one'))
            self.assertEqual(self.submit(), 'acknowledged')
            self.assertEqual(self.box.retrieve('alice'), [])
        finally:
            other.close()

    def test_conflicting_reuse(self):
        self.submit()
        for args in [('one','bob',b'abc',200), ('one','alice',b'abd',200), ('one','alice',b'abc',201)]:
            with self.assertRaises(CoordinationError):
                self.box.submit(*args)

    def test_expiry_and_revocation_are_terminal(self):
        self.submit()
        self.now = 200
        self.assertFalse(self.box.claim('alice', 'one'))
        self.assertEqual(self.submit(), 'expired')
        self.now = 100
        self.submit('two')
        self.assertTrue(self.box.claim('alice', 'two'))
        self.assertTrue(self.box.revoke('alice', 'two'))
        self.assertFalse(self.box.acknowledge('alice', 'two'))
        self.assertEqual(self.submit('two'), 'revoked')

    def test_quotas_and_expiry_release_capacity(self):
        self.submit(body=b'12345678')
        with self.assertRaises(CoordinationError): self.submit('two')
        self.now = 200
        self.submit('two', expiry=300)
        self.submit('three', expiry=300)
        with self.assertRaises(CoordinationError): self.submit('four', body=b'a', expiry=300)
        self.submit('four', recipient='bob', expiry=300)

    def test_expired_and_nonfinite_requests_rejected(self):
        for expiry in [100, float('nan'), float('inf'), -1]:
            with self.assertRaises(CoordinationError): self.submit(expiry=expiry)

    def test_migration_preserves_tombstones_and_pending(self):
        self.submit()
        self.box.claim('alice','one')
        self.box.acknowledge('alice','one')
        self.submit('two')
        destination = Path(self.tmp.name) / 'migrated.db'
        self.box.snapshot(destination)
        migrated = Mailbox(destination, clock=lambda: self.now)
        try:
            self.assertEqual(migrated.submit('one','alice',b'abc',200), 'acknowledged')
            self.assertEqual([x.operation_id for x in migrated.retrieve('alice')], ['two'])
        finally: migrated.close()

    def test_independent_coordinators_race_for_one_operation(self):
        self.submit()
        barrier = Barrier(4)
        def attempt(_):
            node = Mailbox(self.path, clock=lambda: 100)
            try:
                barrier.wait()
                return node.claim('alice', 'one')
            finally:
                node.close()
        with ThreadPoolExecutor(max_workers=4) as workers:
            self.assertEqual(sum(workers.map(attempt, range(4))), 1)

    def test_independent_submitters_cannot_race_past_quota(self):
        barrier = Barrier(4)
        def attempt(i):
            node = Mailbox(self.path, clock=lambda: 100, max_pending=2)
            try:
                barrier.wait()
                try:
                    node.submit(str(i), 'alice', b'a', 200)
                    return True
                except CoordinationError:
                    return False
            finally:
                node.close()
        with ThreadPoolExecutor(max_workers=4) as workers:
            self.assertEqual(sum(workers.map(attempt, range(4))), 2)
