"""Coalesce dashboard polling without caching sessions or failed snapshots."""
import threading
import time


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
