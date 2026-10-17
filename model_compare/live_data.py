"""Shared instructor-funded AA refresh, with retry backoff and saved-data fallback."""
from copy import deepcopy
from hashlib import sha256
from threading import Lock
from time import monotonic
from .snapshots import fetch_artificial_analysis


class SnapshotFeed:
    def __init__(self, fetch=fetch_artificial_analysis, clock=monotonic,
                 refresh_seconds=6 * 60 * 60, retry_seconds=5 * 60):
        self.fetch, self.clock = fetch, clock
        self.refresh_seconds, self.retry_seconds = refresh_seconds, retry_seconds
        self.lock = Lock()
        self.key_id = None
        self.snapshot = None
        self.next_attempt = 0
        self.unavailable = False

    def read(self, api_key):
        """Return (last good snapshot, refresh unavailable), never a credential.

        One download per refresh window per server process, shared by visitors.
        Failed requests retry after five minutes; uploads bypass this service.
        """
        if not api_key:
            return None, False
        with self.lock:
            key_id = sha256(api_key.encode()).hexdigest()
            if key_id != self.key_id:
                self.key_id, self.snapshot = key_id, None
                self.next_attempt, self.unavailable = 0, False
            if self.clock() >= self.next_attempt:
                try:
                    self.snapshot = self.fetch(api_key)
                    self.unavailable = False
                    self.next_attempt = self.clock() + self.refresh_seconds
                except (ValueError, RuntimeError, OSError):
                    # Provider messages/credentials never reach student-facing output.
                    self.unavailable = True
                    self.next_attempt = self.clock() + self.retry_seconds
            return deepcopy(self.snapshot), self.unavailable
