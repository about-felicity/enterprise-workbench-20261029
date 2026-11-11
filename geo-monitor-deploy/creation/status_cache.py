"""Coalesce dashboard polling without caching sessions or failed snapshots."""
import threading
import time
import logging


class StatusCache:
    def __init__(self, ttl=2.0, wait_timeout=8.0):
        self.ttl = ttl
        self.wait_timeout = wait_timeout
        self.condition = threading.Condition()
        self.generation = 0
        self.running = False
        self.value = None
        self.expires = 0

    def invalidate(self):
        with self.condition:
            self.generation += 1
            self.value = None
            self.condition.notify_all()

    def get(self, build):
        deadline = time.monotonic() + self.wait_timeout
        with self.condition:
            while True:
                if self.value is not None and time.monotonic() < self.expires:
                    return self.value
                if not self.running:
                    self.running = True
                    generation = self.generation
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Task status is still refreshing')
                self.condition.wait(remaining)
        try:
            value = build()
            with self.condition:
                if generation == self.generation:
                    self.value = value
                    self.expires = time.monotonic() + self.ttl
            return value
        finally:
            with self.condition:
                self.running = False
                self.condition.notify_all()


class LibraryCache(StatusCache):
    """Serve the last library during refresh; downloads still validate current files."""
    def __init__(self, max_stale=120, **kwargs):
        super().__init__(**kwargs)
        self.max_stale = max_stale
        self.queued = False

    def get(self, build, *, max_stale=None):
        with self.condition:
            stale_limit=self.max_stale if max_stale is None else max_stale
            if self.value is not None and time.monotonic() < self.expires + stale_limit:
                if time.monotonic() >= self.expires and not self.queued and not self.running:
                    self.queued = True
                    threading.Thread(target=self._refresh, args=(build,), daemon=True).start()
                return self.value
        return super().get(build)

    def _refresh(self, build):
        try:
            super().get(build)
        except Exception:
            logging.exception('Article library refresh failed')
        finally:
            with self.condition:
                self.queued = False
