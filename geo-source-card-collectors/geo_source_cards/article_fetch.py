"""Public source articles through Scrapling HTTP, dynamic and stealth readers."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from lxml import html

from .source_analysis import validate_public_url

BLOCKED = re.compile(
    r"安全验证|访问验证|访问过于频繁|人机验证|Access denied|Just a moment|Security verification",
    re.I,
)


def use_scrapling_source(path: Path | None) -> str:
    if path:
        path = path.resolve()
        if not (path / "scrapling/__init__.py").is_file():
            raise ValueError("Scrapling source directory does not contain its package")
        loaded = sys.modules.get("scrapling")
        if loaded and not Path(loaded.__file__).resolve().is_relative_to(path):
            raise RuntimeError(
                "Another Scrapling is already imported; use a fresh process"
            )
        sys.path.insert(0, str(path))
    return str(Path(importlib.import_module("scrapling").__file__).resolve())


def clean_text(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def check_article_relevance(article: dict, expected_title: str) -> dict:
    """Quarantine obvious URL drift, with an auditable lexical signal."""
    if re.fullmatch(r"[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", expected_title.strip()):
        return {
            **article,
            "title_relevance": None,
            "title_relevance_note": "Platform provided only a domain, not an article title",
        }
    title = re.sub(r"[^\w\u4e00-\u9fff]", "", expected_title).casefold()
    if len(title) < 8 or article.get("status") != "fetched":
        return article
    grams = {title[i : i + 3] for i in range(len(title) - 2)}
    actual = re.sub(
        r"[^\w\u4e00-\u9fff]", "", article.get("title", "") + article.get("text", "")
    ).casefold()
    overlap = sum(g in actual for g in grams) / max(1, len(grams))
    result = {**article, "title_relevance": round(overlap, 4)}
    if overlap < 0.08:
        result.update(
            status="failed",
            error="Downloaded content appears unrelated to the cited title; possible redirect or URL drift",
            rejected_text=result.get("text", ""),
            text="",
        )
    return result


def extract_article(markup: str, url: str = "") -> dict:
    tree = html.fromstring(markup)

    def meta(*names):
        for name in names:
            found = tree.xpath(
                "//meta[@property=$name or @name=$name]/@content", name=name
            )
            if found:
                return clean_text(found[0])
        return ""

    title = meta("og:title", "twitter:title") or clean_text(
        "".join(tree.xpath("//title/text()"))
    )
    metadata = {
        "published_at": meta("article:published_time", "pubdate", "date"),
        "author": meta("author"),
        "publisher": meta("og:site_name"),
        "canonical_url": urljoin(
            url, next(iter(tree.xpath('//link[@rel="canonical"]/@href')), url)
        ),
    }
    if BLOCKED.search(title):
        raise ValueError("Verification/access-denied page is not an article")
    structured = []

    def walk(value):
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            if str(value.get("@type")) in {
                "NewsArticle",
                "Article",
                "BlogPosting",
                "MedicalWebPage",
            }:
                structured.append(value)
            for child in value.values():
                if isinstance(child, (list, dict)):
                    walk(child)

    for raw in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            walk(json.loads(raw))
        except ValueError:
            pass
    for node in tree.xpath(
        "//script|//style|//nav|//footer|//aside|//form|//noscript|//svg"
    ):
        node.drop_tree()
    candidates = tree.xpath(
        '//article|//main|//*[@itemprop="articleBody"]|//div|//section'
    )
    if not candidates:
        candidates = [tree]

    def score(node):
        text = clean_text(node.text_content())
        link_chars = sum(len(clean_text(a.text_content())) for a in node.xpath(".//a"))
        density = min(1, link_chars / max(1, len(text)))
        paragraphs = sum(
            len(clean_text(p.text_content())) >= 25 for p in node.xpath(".//p")
        )
        name = (node.get("id", "") + " " + node.get("class", "")).lower()
        bonus = (
            6
            if node.tag in {"article", "main"}
            or re.search(r"article|content|正文|detail|story", name)
            else 0
        )
        return (
            math.log1p(len(text)) * (1 - density) * 3 + min(paragraphs, 20) * 2 + bonus
        )

    # Baijiahao renders paragraphs as spans, while its sidebar uses p/li.
    # Prefer its explicit article boundary so the sidebar cannot outscore it.
    article_nodes = tree.xpath('//*[@data-testid="article"]') if (urlsplit(url).hostname or '').lower() == 'baijiahao.baidu.com' else []
    chosen = max(article_nodes or candidates, key=score)
    paragraphs = []
    headings = []
    for node in chosen.xpath('.//h1|.//h2|.//h3|.//h4|.//p|.//li|.//blockquote|.//span[contains(concat(" ",normalize-space(@class)," ")," bjh-p ")]'):
        if node.xpath("ancestor::p|ancestor::li|ancestor::blockquote"):
            continue
        text = clean_text(node.text_content())
        if not text or text in [p["text"] for p in paragraphs]:
            continue
        is_heading = str(node.tag).startswith("h")
        if is_heading:
            headings.append(text)
        paragraphs.append(
            {"kind": "heading" if is_heading else "paragraph", "text": text}
        )
    method = "dom_text_density"
    body = "\n\n".join(p["text"] for p in paragraphs)
    if len(body) < 160:
        body = "\n".join(
            clean_text(line)
            for line in chosen.text_content().splitlines()
            if clean_text(line)
        )
        paragraphs = [
            {"kind": "paragraph", "text": line} for line in body.splitlines() if line
        ]
    for item in structured:
        if (
            len(str(item.get("articleBody", ""))) > len(body)
            and len(str(item.get("articleBody", ""))) >= 160
        ):
            body = clean_text(item["articleBody"])
            paragraphs = [
                {"kind": "paragraph", "text": s.strip()}
                for s in re.split(r"\n+", item["articleBody"])
                if s.strip()
            ]
            title = str(item.get("headline") or title)
            metadata["published_at"] = str(
                item.get("datePublished") or metadata["published_at"]
            )
            method = "jsonld_article_body"
    if len(body) < 160:
        raise ValueError(
            "Too little article text; dynamic content or access restriction remains"
        )
    if BLOCKED.search(body[:250]) and len(body) < 1000:
        raise ValueError("Verification/access-denied content is not an article")
    return {
        "title": title or next(iter(headings), ""),
        "text": body,
        "paragraphs": paragraphs,
        "headings": headings,
        "metadata": metadata,
        "extraction_method": method,
        "sha256": hashlib.sha256(body.encode()).hexdigest(),
    }


class MediaScopedFetcher:
    """Skip sources the production media registry would exclude anyway.

    Preserve their links and an explicit classification-pending status. Baidu
    redirect links are resolved by the underlying reader and checked downstream.
    """

    def __init__(self, fetcher, registry):
        self.fetcher, self.registry = fetcher, registry

    def __call__(self, url):
        from .daily_editorial import media_identity

        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        redirect = host in {
            "www.baidu.com",
            "baidu.com",
            "m.baidu.com",
            "mbd.baidu.com",
        } and parsed.path.startswith(("/link", "/s", "/newspage"))
        if not media_identity(url, self.registry) and not redirect:
            return {
                "status": "unregistered_media",
                "requested_url": url,
                "text": "",
                "error": "Not in the configured mainland media registry; retained for classification review, not treated as missing article or non-mainland proof.",
            }
        return self.fetcher(url)


class ScraplingArticleFetcher:
    def __init__(
        self,
        *,
        source: Path | None = None,
        timeout: int = 30,
        max_bytes: int = 3_000_000,
        backends=("http", "dynamic", "stealth"),
        validator=validate_public_url,
        engines=None,
    ):
        self.library = use_scrapling_source(source)
        self.timeout, self.max_bytes = timeout, max_bytes
        self.backends, self.validator, self.engines = backends, validator, engines

    def _fetch(self, backend: str, url: str):
        if self.engines:
            return self.engines[backend](url)
        from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

        if backend == "http":
            return Fetcher.get(
                url, timeout=self.timeout, retries=1, follow_redirects=False
            )
        from monitor_core.cdp_chat import chrome_executable

        def setup(page):
            def route(request_route):
                request = request_route.request
                if request.is_navigation_request():
                    try:
                        self.validator(request.url)
                    except (ValueError, OSError):
                        request_route.abort()
                        return
                request_route.continue_()

            page.route("**/*", route)

        def action(page):
            for _ in range(3):
                page.evaluate("window.scrollBy(0, Math.min(innerHeight, 700))")
                page.wait_for_timeout(300)

        fetcher = DynamicFetcher if backend == "dynamic" else StealthyFetcher
        return fetcher.fetch(
            url,
            headless=True,
            timeout=self.timeout * 1000,
            retries=1,
            executable_path=str(chrome_executable()),
            network_idle=False,
            load_dom=True,
            wait=800,
            page_setup=setup,
            page_action=action,
            google_search=False,
            disable_resources=False,
        )

    def __call__(self, url: str) -> dict:
        attempts = []
        original = url
        for backend in self.backends:
            target = original
            try:
                for _ in range(6):
                    self.validator(target)
                    response = self._fetch(backend, target)
                    status = int(response.status)
                    headers = {
                        str(k).lower(): str(v) for k, v in response.headers.items()
                    }
                    if status in (301, 302, 303, 307, 308):
                        if not headers.get("location"):
                            raise ValueError("Redirect lacks a target")
                        target = urljoin(target, headers["location"])
                        continue
                    if status >= 400:
                        raise ValueError(f"HTTP {status}")
                    final_url = str(response.url or target)
                    self.validator(final_url)
                    if len(response.body) > self.max_bytes:
                        raise ValueError("Article exceeds size limit")
                    content_type = headers.get("content-type", "").split(";")[0]
                    if content_type and content_type not in {
                        "text/html",
                        "application/xhtml+xml",
                        "text/plain",
                    }:
                        return {
                            "status": "unsupported",
                            "text": "",
                            "final_url": final_url,
                            "content_type": content_type,
                            "attempts": attempts,
                            "error": "This article reader currently supports HTML/plain text",
                        }
                    extracted = extract_article(response.html_content, final_url)
                    attempts.append({"backend": backend, "status": "fetched"})
                    return {
                        "status": "fetched",
                        "requested_url": original,
                        "final_url": final_url,
                        "backend": backend,
                        "scrapling_library": self.library,
                        "attempts": attempts,
                        **extracted,
                    }
                raise ValueError("Too many redirects")
            except Exception as exc:
                attempts.append(
                    {"backend": backend, "status": "failed", "error": str(exc)[:500]}
                )
        return {
            "status": "failed",
            "requested_url": original,
            "text": "",
            "attempts": attempts,
            "error": "All enabled Scrapling readers failed; inspect attempts or provide a permitted source copy",
        }
