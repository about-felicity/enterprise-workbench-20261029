"""Reuse public source reads across supplemental rounds of the same job.

Ownership, topic, media and article quality checks still run after fetching.
Failures remain failures and expire quickly so transient outages can recover.
"""
import hashlib
import json
import time
import sqlite3
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from geo_source_cards.runtime import atomic_json


def failure_kind(article):
    errors = ' '.join(str(a.get('error', '')) for a in article.get('attempts', []))
    errors += ' ' + str(article.get('error', ''))
    errors = errors.lower()
    if any(s in errors for s in ('name resolution', 'getaddrinfo', 'name or service not known')):
        return 'dns'
    if any(s in errors for s in ('verification', 'access-denied', 'access denied')):
        return 'verification'
    if 'http 404' in errors or 'http 410' in errors:
        return 'not_found'
    return 'unavailable'


class SourceCache:
    def __init__(self, root, fetcher, clock=time.time, content_db=None):
        self.root = Path(root)
        self.fetcher = fetcher
        self.clock = clock
        self.directory = self.root / 'source_read_cache'
        self.hits = 0
        self.content_db = Path(content_db) if content_db is not None else None

    def shared_article(self, url):
        """Read exact-URL verified GEO snapshots without extending their age."""
        if self.content_db is None or not self.content_db.is_file():return None
        from .source_adapter import article
        from geo_source_cards.article_quality import normalize
        try:
            with closing(sqlite3.connect(self.content_db.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
                db.row_factory=sqlite3.Row
                row=db.execute('select * from source_content where url=?',(url,)).fetchone()
            if not row:return None
            at=datetime.strptime(row['fetched_at'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()
            if not 0<=self.clock()-at<86400:return None
            value=normalize(article(row,url))
            if value.get('status')!='fetched':return None
            return {**value,'requested_url':url,'source_read_at':at,'fetched_at':at,
                    'original_fetched_at':row['fetched_at'],'reused_from':'geo_source_content_sqlite'}
        except (sqlite3.Error,OSError,ValueError,KeyError,TypeError):return None

    def valid(self, path, url):
        try:
            article = json.loads(path.read_text('utf-8'))
            if article.get('requested_url') != url:
                return None
            ttl = 86400 if article.get('status') == 'fetched' else {
                'dns': 60, 'verification': 900, 'not_found': 3600,
            }.get(article.get('failure_kind'), 60)
            if 0 <= self.clock() - float(article.get('source_read_at', article.get('fetched_at', 0))) < ttl:
                return article
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return None

    def __call__(self, url):
        key = hashlib.sha256(url.encode()).hexdigest() + '.json'
        destination = self.directory / key
        cached = self.valid(destination, url)
        if cached is None or cached.get('status')!='fetched':
            shared=self.shared_article(url)
            if shared is not None:
                cached=shared
                atomic_json(destination,shared)
        if cached is None:
            # Older rounds already have successful exact-URL caches. Preserve
            # their original timestamp; reading must never extend freshness.
            for path in sorted(self.root.glob('private_source_analysis*/article_cache/' + key),
                               key=lambda p: p.stat().st_mtime, reverse=True):
                candidate = self.valid(path, url)
                if candidate and candidate.get('status') == 'fetched':
                    cached = {**candidate, 'source_read_at': candidate.get('source_read_at', candidate['fetched_at'])}
                    atomic_json(destination, cached)
                    break
        if cached is not None:
            self.hits += 1
            return cached
        article = {**self.fetcher(url), 'requested_url': url, 'fetched_at': self.clock(), 'source_read_at': self.clock()}
        if article.get('status') == 'failed':
            article['failure_kind'] = failure_kind(article)
        atomic_json(destination, article)
        return article
