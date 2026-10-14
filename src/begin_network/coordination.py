"""Durable local coordination after envelope and permission verification.

This module does not authenticate callers, verify signatures, or execute remote code.
The embedding application must supply a verified recipient identity on every call.
"""
import hashlib
import sqlite3
import time
from dataclasses import dataclass


class CoordinationError(ValueError):
    pass


@dataclass(frozen=True)
class Delivery:
    operation_id: str
    recipient: str
    ciphertext: bytes
    expires_at: float
    state: str


class Mailbox:
    """One SQLite store shared by independent, authenticated receiver adapters.

    Operation IDs are unique across this store. Tombstones are retained so retries
    cannot recreate acknowledged, expired, or revoked work.
    """

    def __init__(self, path, *, max_pending=100, max_bytes=1048576, clock=time.time):
        if max_pending < 1 or max_bytes < 1:
            raise CoordinationError("quotas must be positive")
        self.clock = clock
        self.max_pending = max_pending
        self.max_bytes = max_bytes
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
            operation_id TEXT PRIMARY KEY, recipient TEXT NOT NULL,
            ciphertext BLOB NOT NULL, digest TEXT NOT NULL,
            expires_at REAL NOT NULL, state TEXT NOT NULL)""")

    def close(self):
        self.db.close()

    def _expire(self):
        self.db.execute("UPDATE deliveries SET state='expired', ciphertext=X'' "
                        "WHERE expires_at<=? AND state IN ('pending','claimed')", (self.clock(),))

    def submit(self, operation_id, recipient, ciphertext, expires_at):
        """Queue opaque ciphertext from an already-verified request.

        Identical retries return the existing state; conflicting reuse is rejected.
        """
        if not isinstance(operation_id, str) or not operation_id or not isinstance(recipient, str) or not recipient:
            raise CoordinationError("operation and recipient must be nonempty strings")
        if not isinstance(ciphertext, bytes) or not ciphertext:
            raise CoordinationError("ciphertext must be nonempty bytes")
        if not isinstance(expires_at, (int, float)) or not 0 < expires_at < float('inf'):
            raise CoordinationError("invalid expiry")
        digest = hashlib.sha256(ciphertext).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._expire()
            row = self.db.execute("SELECT recipient,digest,expires_at,state FROM deliveries WHERE operation_id=?", (operation_id,)).fetchone()
            if row:
                if row[:3] != (recipient, digest, expires_at):
                    raise CoordinationError("conflicting operation ID")
                state = row[3]
            else:
                if expires_at <= self.clock():
                    raise CoordinationError("request already expired")
                count, size = self.db.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(ciphertext)),0) FROM deliveries WHERE recipient=? AND state IN ('pending','claimed')", (recipient,)).fetchone()
                if count >= self.max_pending or size + len(ciphertext) > self.max_bytes:
                    raise CoordinationError("recipient quota exceeded")
                self.db.execute("INSERT INTO deliveries VALUES (?,?,?,?,?,'pending')", (operation_id, recipient, ciphertext, digest, expires_at))
                state = 'pending'
            self.db.execute("COMMIT")
            return state
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def retrieve(self, recipient):
        """Return pending work only for the authenticated recipient supplied by host."""
        self._expire()
        return [Delivery(*row) for row in self.db.execute("SELECT operation_id,recipient,ciphertext,expires_at,state FROM deliveries WHERE recipient=? AND state='pending' ORDER BY operation_id", (recipient,))]

    def claim(self, recipient, operation_id):
        """Atomically claim once. A lost/crashed claim is deliberately not retried."""
        self._expire()
        return self.db.execute("UPDATE deliveries SET state='claimed' WHERE operation_id=? AND recipient=? AND state='pending' AND expires_at>?", (operation_id, recipient, self.clock())).rowcount == 1

    def acknowledge(self, recipient, operation_id):
        self._expire()
        return self.db.execute("UPDATE deliveries SET state='acknowledged', ciphertext=X'' WHERE operation_id=? AND recipient=? AND state='claimed' AND expires_at>?", (operation_id, recipient, self.clock())).rowcount == 1

    def revoke(self, recipient, operation_id):
        """Apply a revocation after its authorization has been checked by the host."""
        return self.db.execute("UPDATE deliveries SET state='revoked',ciphertext=X'' WHERE operation_id=? AND recipient=? AND state IN ('pending','claimed')", (operation_id, recipient)).rowcount == 1

    def snapshot(self, destination):
        """Back up a stopped node for migration, preserving deduplication tombstones.

        The host must stop writes and retire the original before opening the copy.
        This is an operational transfer, not a distributed consensus mechanism.
        """
        target = sqlite3.connect(destination)
        try:
            self.db.backup(target)
        finally:
            target.close()
