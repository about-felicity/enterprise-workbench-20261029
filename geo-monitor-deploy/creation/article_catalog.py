"""Reuse validated article listings until their inputs change."""
import hashlib
import json
import logging
import os
from pathlib import Path

from geo_source_cards.runtime import atomic_json, process_lock

from .article_format import revision_path


# Bump the version when listing inputs or validation rules change.
CATALOG_VERSION = 2


def stat_signature(info):
    return (info.st_mode, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def file_signature(path):
    try:
        return stat_signature(path.stat())
    except FileNotFoundError:
        return None


def folder_signature(folder):
    try:
        with os.scandir(folder) as it:
            entries = []
            for entry in it:
                info = stat_signature(entry.stat(follow_symlinks=False))
                target = file_signature(Path(entry.path)) if entry.is_symlink() else None
                entries.append((entry.name, info, target))
        return sorted(entries)
    except FileNotFoundError:
        return None


def listing_signature(root):
    receipts = sorted((root / 'approved').glob('*/*/*/receipt.json'))
    if not receipts:
        return None
    folders = [receipt.parent for receipt in receipts]
    days = sorted({folder.parent.parent.name for folder in folders})
    inputs = (
        file_signature(root / 'job.json'),
        file_signature(root / 'product.json'),
        file_signature(root / 'logic_policy.json'),
        folder_signature(root / 'revocations'),
        [(day, file_signature(root / 'days' / day / 'product.json')) for day in days],
        [(folder.relative_to(root).as_posix(), folder_signature(folder),
          file_signature(revision_path(folder))) for folder in folders],
    )
    return hashlib.sha256(json.dumps(inputs, separators=(',', ':')).encode()).hexdigest()


class ArticleCatalog:
    """Keep listing results on disk so the first request after restart can reuse them."""

    def __init__(self, path):
        self.path = path
        try:
            stored = json.loads(path.read_text('utf-8-sig'))
            entries = stored.get('entries')
            self.previous = entries if stored.get('version') == CATALOG_VERSION and isinstance(entries, dict) else {}
        except (OSError, ValueError, AttributeError):
            self.previous = {}
        self.entries = {}

    def articles(self, root, build):
        signature = listing_signature(root)
        if signature is None:
            return []
        key = str(root)
        saved = self.previous.get(key)
        if isinstance(saved, dict) and saved.get('signature') == signature and isinstance(saved.get('rows'), list):
            self.entries[key] = saved
            return saved['rows']
        rows = build(root)
        # Do not associate a listing with files written while it was being read.
        if listing_signature(root) == signature:
            self.entries[key] = {'signature': signature, 'rows': rows}
        return rows

    def save(self):
        if self.entries != self.previous:
            try:
                with process_lock(self.path.with_suffix('.lock'), blocking=True):
                    atomic_json(self.path, {'version': CATALOG_VERSION, 'entries': self.entries})
            except (OSError, RuntimeError):
                logging.exception('Article catalog cache could not be saved')
