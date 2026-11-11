"""Coordinate browser capacity and platform cooldown across video ledgers."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
import time


class CheckBudget:
    def __init__(self, directory=None, ledger="creator", shared_slots=3):
        self.directory = Path(directory) if directory else None
        self.slots = (f"reserved-{ledger}", *(f"shared-{index}" for index in range(shared_slots)))
        self.local_pause_until = 0

    @contextmanager
    def browser_slot(self):
        if self.directory is None:
            yield True
            return
        from fcntl import LOCK_EX, LOCK_NB, flock

        for name in self.slots:
            with (self.directory / name).open("ab") as stream:
                try:
                    flock(stream, LOCK_EX | LOCK_NB)
                except BlockingIOError:
                    continue
                # The OS releases the slot even if a collector process exits.
                yield True
                return
        yield False

    def paused_until(self):
        if self.directory is None:
            return self.local_pause_until
        try:
            return float((self.directory / "platform-pause").read_text(encoding="ascii"))
        except FileNotFoundError:
            return 0

    def pause(self, seconds):
        until = time.time() + seconds
        if self.directory is None:
            self.local_pause_until = max(until, self.local_pause_until)
            return
        from fcntl import LOCK_EX, flock

        with (self.directory / "platform-pause.lock").open("ab") as lock:
            flock(lock, LOCK_EX)
            if until > self.paused_until():
                stream = NamedTemporaryFile(mode="w", encoding="ascii", dir=self.directory, delete=False)
                temporary = Path(stream.name)
                try:
                    with stream:
                        stream.write(str(until))
                    temporary.replace(self.directory / "platform-pause")
                finally:
                    temporary.unlink(missing_ok=True)
