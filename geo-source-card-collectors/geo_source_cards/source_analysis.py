"""Fetch public source articles and report reproducible literal content metrics."""

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from .runtime import atomic_json, atomic_write, process_lock, runtime_root


class ArticleParser(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "aside", "form", "noscript", "svg"}
    BLOCK = {
        "p",
        "div",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "br",
        "section",
        "article",
        "main",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.article = []
        self.main = []
        self.title = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"br", "img", "meta", "link", "input", "hr", "source", "wbr"}:
            self.stack.append(tag)
        if tag in self.BLOCK:
            self._append("\n")

    def handle_endtag(self, tag):
        if tag in self.stack:
            at = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[at:]
        if tag in self.BLOCK:
            self._append("\n")

    def _append(self, value):
        if any(tag in self.SKIP for tag in self.stack):
            return
        if "title" in self.stack:
            self.title.append(value)
            return
        self.text.append(value)
        if "article" in self.stack:
            self.article.append(value)
        if "main" in self.stack:
            self.main.append(value)

    def handle_data(self, data):
        self._append(data)

    def result(self):
        selected = next(
            (
                v
                for v in (self.article, self.main, self.text)
                if len("".join(v).strip()) >= 80
            ),
            self.text,
        )
        text = "\n".join(
            re.sub(r"\s+", " ", line).strip() for line in "".join(selected).splitlines()
        )
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return {
            "title": "".join(self.title).strip(),
            "text": text,
            "extraction_method": "html_article_main_or_body",
        }


def validate_public_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Only public HTTP(S) source URLs are supported")
    addresses = socket.getaddrinfo(
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    if not addresses or any(
        not ipaddress.ip_address(item[4][0]).is_global for item in addresses
    ):
        raise ValueError("Source resolves to a non-public address")


def fetch_article(url, session=None, max_bytes=2_000_000):
    owned = session is None
    session = session or requests.Session()
    started = time.monotonic()
    response = None
    try:
        for _ in range(6):
            validate_public_url(url)
            response = session.get(
                url,
                timeout=(5, 15),
                allow_redirects=False,
                stream=True,
                headers={"User-Agent": "GeoSourceCollector/0.2 (+article analysis)"},
            )
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("Redirect has no target")
                url = urljoin(url, location)
                response.close()
                continue
            response.raise_for_status()
            kind = (
                response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            )
            if kind not in ("text/html", "application/xhtml+xml", "text/plain"):
                return {
                    "status": "unsupported",
                    "final_url": url,
                    "content_type": kind,
                    "text": "",
                    "error": "Only HTML/plain text is supported; PDF/media are preserved as links",
                }
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError("Source exceeds download size limit")
                if time.monotonic() - started > 30:
                    raise TimeoutError("Source download deadline exceeded")
            charset = re.search(
                r'charset\s*=\s*["\']?([^;\s"\']+)',
                response.headers.get("Content-Type", ""),
                re.I,
            )
            encoding = charset[1] if charset else "utf-8"
            try:
                text = bytes(body).decode(encoding)
            except (UnicodeError, LookupError):
                text = bytes(body).decode("gb18030", errors="replace")
            if kind == "text/plain":
                extracted = {
                    "title": "",
                    "text": text.strip(),
                    "extraction_method": "plain_text",
                }
            else:
                parser = ArticleParser()
                parser.feed(text)
                extracted = parser.result()
            if len(extracted["text"]) < 80:
                raise ValueError(
                    "Source has too little extractable text; may require JavaScript or verification"
                )
            if any(
                term in extracted["title"].casefold()
                for term in ("安全验证", "访问验证", "access denied", "just a moment")
            ):
                raise ValueError("Source is a verification/access-denied page")
            return {
                "status": "fetched",
                "final_url": url,
                "content_type": kind,
                **extracted,
                "sha256": hashlib.sha256(extracted["text"].encode()).hexdigest(),
            }
        raise ValueError("Too many redirects")
    except (requests.RequestException, OSError, ValueError, TimeoutError) as exc:
        return {"status": "failed", "final_url": url, "text": "", "error": str(exc)}
    finally:
        if response is not None:
            response.close()
        if owned:
            session.close()


def text_metrics(text, keywords=(), brands=()):
    text = str(text or "")

    def occurrences(terms):
        return {
            term: len(re.findall(re.escape(term), text, flags=re.I))
            for term in terms
            if term
        }

    return {
        "characters": len(text),
        "keyword_mentions": occurrences(keywords),
        "brand_mentions": occurrences(brands),
        "method": "literal_case_insensitive_mentions",
        "semantic_recommendation_inferred": False,
    }


def load_records(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = (
        json.loads(text)
        if text.lstrip().startswith("[")
        else [json.loads(line) for line in text.splitlines() if line.strip()]
    )
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Input must be a JSON array or JSONL objects")
    return rows


def analyze_records(
    records, keywords=(), brands=(), fetch=True, cache_dir=None, fetcher=fetch_article
):
    cache_dir = cache_dir or runtime_root() / "source_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    seen = {}
    for record in records:
        output = {
            "task_id": record.get("task_id"),
            "model": record.get("model"),
            "question": record.get("question"),
            "body": record.get("body", record.get("body_markdown", "")),
            "answer_analysis": text_metrics(
                record.get("body", record.get("body_markdown", "")), keywords, brands
            ),
            "source_capture_complete": record.get("source_capture_complete"),
            "sources": [],
        }
        for item in record.get("sources") or []:
            if not isinstance(item, dict):
                raise ValueError(
                    "Every source must be an object containing url or href"
                )
            url = str(item.get("url") or item.get("href") or "")
            key = hashlib.sha256(url.encode()).hexdigest()
            path = cache_dir / (key + ".json")
            article = seen.get(url)
            if article is None and path.exists():
                try:
                    cached = json.loads(path.read_text(encoding="utf8"))
                    age = time.time() - float(cached.get("fetched_at", 0))
                    if cached.get("status") == "fetched" and 0 <= age < 86400:
                        article = cached
                except (OSError, ValueError, TypeError, AttributeError):
                    pass
            if article is None:
                article = (
                    fetcher(url) if fetch else {"status": "not_fetched", "text": ""}
                )
                article = {**article, "requested_url": url, "fetched_at": time.time()}
                if article["status"] == "fetched":
                    atomic_json(path, article)
            seen[url] = article
            output["sources"].append(
                {
                    "title": item.get("title", ""),
                    "url": url,
                    "article": article,
                    "content_analysis": text_metrics(
                        article.get("text", ""), keywords, brands
                    )
                    if article["status"] == "fetched"
                    else None,
                }
            )
        yield output


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Fetch source article text and count literal keyword/brand mentions"
    )
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--runtime-dir", type=Path)
    p.add_argument("--keyword", action="append", default=[])
    p.add_argument("--brand", action="append", default=[])
    p.add_argument("--no-fetch", action="store_true")
    args = p.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        p.error("Output must differ from input")
    if args.runtime_dir:
        import os

        os.environ["GEO_COLLECTOR_RUNTIME"] = str(args.runtime_dir.resolve())
    with process_lock(runtime_root() / "analysis.lock"):
        rows = list(
            analyze_records(
                load_records(args.input), args.keyword, args.brand, not args.no_fetch
            )
        )
        atomic_write(
            args.output,
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        )
    print(
        json.dumps(
            {"records": len(rows), "output": str(args.output)}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
