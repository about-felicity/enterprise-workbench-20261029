"""Bounded streaming projection of archive metadata for the activity feed.

The archive is atomically replaced by its writer. Never deserialize the whole
archive in an HTTP thread: only status and the existing ownership label matter.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class _JSONStream:
    def __init__(self, stream, chunk_size=65536):
        self.stream, self.chunk_size = stream, chunk_size
        self.buffer, self.position, self.eof = "", 0, False
        self.decoder = json.JSONDecoder()

    def more(self):
        self.buffer = self.buffer[self.position:]
        self.position = 0
        chunk = self.stream.read(self.chunk_size)
        self.buffer += chunk
        self.eof = not chunk
        if len(self.buffer) > 16 * 1024 * 1024:
            raise ValueError("Archive entry exceeds activity reader bound")

    def peek(self):
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer):
                return self.buffer[self.position]
            if self.eof:
                return ""
            self.more()

    def expect(self, token):
        if self.peek() != token:
            raise ValueError("Invalid archive JSON delimiter")
        self.position += 1

    def value(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                # A number can be a valid prefix at a chunk boundary (e.g. 1e2).
                if end == len(self.buffer) and not self.eof:
                    self.more()
                    continue
                if end < len(self.buffer) and self.buffer[end] not in " \t\r\n,:}]":
                    if not self.eof:
                        self.more()
                        continue
                    raise ValueError("Invalid archive JSON value")
                self.position = end
                return value
            except json.JSONDecodeError:
                if self.eof:
                    raise
                self.more()

    def keys(self):
        self.expect("{")
        if self.peek() == "}":
            self.position += 1
            return
        while True:
            key = self.value()
            if not isinstance(key, str):
                raise ValueError("Invalid archive key")
            self.expect(":")
            yield key
            if self.peek() == "}":
                self.position += 1
                return
            self.expect(",")


def read_activity_entries(path: Path, *, chunk_size=65536):
    result = {}
    with path.open(encoding="utf-8-sig") as stream:
        reader = _JSONStream(stream, chunk_size)
        for key in reader.keys():
            if key != "entries":
                reader.value()
                continue
            if reader.peek() != "{":
                reader.value()
                continue
            for url in reader.keys():
                entry = reader.value()
                if not isinstance(entry, dict):
                    continue
                compact = {"status": str(entry.get("status") or "")}
                mentions = entry.get("own_product_mentions")
                if isinstance(mentions, list):
                    # Consumers only inspect list presence and truthiness.
                    compact["own_product_mentions"] = [True] if mentions else []
                result[url] = compact
        if reader.peek():
            raise ValueError("Trailing archive JSON data")
    return result


class ActivityIndexCache:
    """One compact generation; lock coalesces cold loads across HTTP threads."""
    def __init__(self, path: Path, refresh_seconds=5.0):
        self.path, self.refresh_seconds = path, refresh_seconds
        self.lock = threading.Lock()
        self.stamp, self.checked, self.entries = None, 0.0, {}

    def get(self):
        with self.lock:
            now = time.monotonic()
            if now - self.checked < self.refresh_seconds:
                return self.entries
            try:
                stat = self.path.stat()
                stamp = (stat.st_mtime_ns, stat.st_size)
                if stamp != self.stamp:
                    entries = read_activity_entries(self.path)
                    self.entries, self.stamp = entries, stamp
                self.checked = now
            except (OSError, ValueError):
                # Preserve last complete metadata if replacement is unreadable.
                self.checked = now
            return self.entries
