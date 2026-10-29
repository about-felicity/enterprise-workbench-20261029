from __future__ import annotations

import os
import random
import re
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests

from geo_source_cards.runtime import runtime_root
from geo_source_cards.search_recovery import SecurityVerificationError
from monitor_core.cdp_chat import CDPPage, chrome_executable


class ScraplingStealthPage:
    """Small compatibility adapter around Scrapling's persistent stealth browser."""

    def __init__(self, profile: Path, timeout: int = 60):
        self.is_stealth = True
        try:
            from scrapling.fetchers import StealthySession
        except ImportError as exc:
            raise RuntimeError(
                "文心隐身浏览器不可用，请安装 scrapling[fetchers]"
            ) from exc
        profile.mkdir(parents=True, exist_ok=True)
        self.adaptive_storage = profile / "scrapling_adaptive_elements.db"
        self._adaptive_snapshot_cache: dict[str, Any] | None = None
        self.timeout_ms = max(30, int(timeout)) * 1000
        self.session = StealthySession(
            # Wenxin collection is a background production job. Keep the
            # stealth browser hidden unless an operator explicitly opts into
            # a visible troubleshooting window.
            headless=os.environ.get("WENXIN_STEALTH_HEADLESS", "1") != "0",
            user_data_dir=str(profile),
            max_pages=4,
            timeout=self.timeout_ms,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            google_search=False,
            extra_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
            disable_resources=False,
            block_webrtc=True,
            hide_canvas=True,
            allow_webgl=True,
            retries=1,
            # Reuse the system Chrome when present. This avoids a separate
            # ~200 MB browser runtime and keeps enterprise workstation memory
            # and patch management under one browser installation.
            executable_path=os.environ.get("WENXIN_CHROME_PATH")
            or str(chrome_executable()),
        )
        self.session.start()
        context = self.session.context
        if context is None:
            self.session.close()
            raise RuntimeError("Scrapling 隐身浏览器没有创建持久化上下文")
        self.page = context.pages[0] if context.pages else context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        self.page.set_default_navigation_timeout(self.timeout_ms)

    def _adaptive_document(self):
        """Parse the live DOM with Scrapling's persisted adaptive relocator."""
        from scrapling import Selector
        from scrapling.core.storage import SQLiteStorageSystem

        if getattr(self, "_adaptive_store", None) is None:

            class OwnedStorage(SQLiteStorageSystem.__wrapped__):
                def close(self):
                    if not getattr(self, "_closed", False):
                        super().close()
                        self._closed = True

            self._adaptive_store = OwnedStorage(
                storage_file=str(self.adaptive_storage), url="https://www.baidu.com/"
            )

        return Selector(
            self.page.content(),
            # Use one stable domain key so changing search query/element IDs do
            # not fragment Scrapling's learned element fingerprints.
            url="https://www.baidu.com/",
            adaptive=True,
            _storage=self._adaptive_store,
            storage_args={
                "storage_file": str(self.adaptive_storage),
                "url": "https://www.baidu.com/",
            },
        )

    @staticmethod
    def _adaptive_find(
        document: Any, selectors: tuple[str, ...], identifier: str, percentage: int = 40
    ) -> list[Any]:
        for css in selectors:
            elements = list(document.css(css))
            if elements:
                document.save(elements[0], identifier)
                return elements
        saved = document.retrieve(identifier)
        if not saved:
            return []
        relocated = document.relocate(saved, percentage)
        if not relocated:
            return []
        return [relocated, *list(relocated.find_similar())]

    def adaptive_ai_snapshot(self) -> dict[str, Any]:
        """Locate the AI card/body/citations even after volatile IDs change."""
        if self._adaptive_snapshot_cache is not None:
            return dict(self._adaptive_snapshot_cache)
        document = self._adaptive_document()
        cards = self._adaptive_find(
            document,
            (
                '#content_left [tpl="new_baikan_index"]',
                '#content_left [m-name*="new_baikan_index"]',
                '#content_left [tpl="wenda_generate"]',
                "#content_left .ai-entry",
            ),
            "baidu-wenxin-ai-card",
            42,
        )
        if not cards:
            return {"ok": False, "body": "", "citationCount": 0, "citationXpaths": []}
        card = cards[0]
        answers = self._adaptive_find(
            card,
            (
                ".cosd-markdown-content",
                '[class*="accordion-panels-title"]',
                '[class*="markdown-content"]',
            ),
            "baidu-wenxin-answer-body",
            38,
        )
        # Adaptive relocation can return structurally similar nodes elsewhere;
        # retain only nodes that are still descendants of the learned AI card.
        answers = [item for item in answers if card._root in item._root.iterancestors()]
        chunks: list[str] = []
        for item in answers:
            value = re.sub(
                r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]",
                "",
                str(item.get_all_text(separator="\n", strip=True)),
            ).strip()
            if value and value not in chunks:
                chunks.append(value)
        citations = self._adaptive_find(
            card,
            (
                ".cosd-citation",
                "[data-citation]",
                "[data-source-index]",
                'a[class*="citation"]',
                'button[class*="citation"]',
                'span[class*="citation"]',
                '[class*="reference"] a[href]',
            ),
            "baidu-wenxin-citation",
            36,
        )
        citations = [
            item for item in citations if card._root in item._root.iterancestors()
        ]
        xpaths: list[str] = []
        for item in citations:
            path = str(item._root.getroottree().getpath(item._root))
            if path and path not in xpaths:
                xpaths.append(path)
        body = "\n\n".join(chunks).strip()
        result = {
            "ok": bool(body),
            "body": body,
            "citationCount": len(xpaths),
            "citationXpaths": xpaths,
            "adaptive": True,
        }
        if result["ok"]:
            self._adaptive_snapshot_cache = dict(result)
        return result

    def adaptive_citation_point(self, index: int) -> dict[str, float] | None:
        snapshot = self.adaptive_ai_snapshot()
        paths = list(snapshot.get("citationXpaths") or [])
        if index < 0 or index >= len(paths):
            return None
        locator = self.page.locator(f"xpath={paths[index]}").first
        # ``scroll_into_view_if_needed`` leaves a citation at the bottom edge
        # when even one pixel is visible.  Its tooltip then opens off-screen.
        # Always center the marker so the complete popup can render and be read.
        locator.evaluate(
            "element => element.scrollIntoView({block:'center', inline:'nearest'})",
            timeout=5_000,
        )
        self.page.wait_for_timeout(300)
        box = locator.bounding_box(timeout=5_000)
        if not box:
            return None
        return {
            "x": float(box["x"] + box["width"] / 2),
            "y": float(box["y"] + box["height"] / 2),
        }

    @staticmethod
    def _target(page: Any) -> str:
        return f"scrapling-{id(page):x}"

    def call(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 15
    ) -> dict[str, Any]:
        values = params or {}
        timeout_ms = max(1_000, int(timeout * 1000))
        if method == "Page.reload":
            self._adaptive_snapshot_cache = None
            self.page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
            return {"frameId": self._target(self.page)}
        if method == "Page.navigate":
            self._adaptive_snapshot_cache = None
            try:
                self.page.goto(
                    str(values.get("url") or "about:blank"),
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )
            except Exception as error:
                # A slow existing navigation is not permission to search again.
                # Wait for this document only; fresh-query checks run upstream.
                if type(
                    error
                ).__name__ != "TimeoutError" or "Page.goto: Timeout" not in str(error):
                    raise
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=45000)
                except Exception as waited_error:
                    if type(waited_error).__name__ != "TimeoutError":
                        raise
                    # Playwright's nested load-state timeout drops "Page.goto".
                    # Keep its read-only navigation origin for the bounded
                    # recovery classifier; never classify a chat send this way.
                    raise TimeoutError("Page.goto: Timeout waiting for original document: " + str(waited_error)) from waited_error
            return {"frameId": self._target(self.page)}
        if method == "Input.dispatchMouseEvent":
            event_type = str(values.get("type") or "")
            x, y = float(values.get("x") or 0), float(values.get("y") or 0)
            if event_type == "mouseMoved":
                self.page.mouse.move(x, y)
            elif event_type == "mousePressed":
                self.page.mouse.move(x, y)
                self.page.mouse.down(button=str(values.get("button") or "left"))
            elif event_type == "mouseReleased":
                self.page.mouse.move(x, y)
                self.page.mouse.up(button=str(values.get("button") or "left"))
            return {}
        raise NotImplementedError(f"Scrapling 页面不支持调试命令：{method}")

    def evaluate(self, expression: str, timeout: float = 15) -> Any:
        self.page.set_default_timeout(max(1_000, int(timeout * 1000)))
        try:
            read_only = expression in {
                BAIDU_AI_SNAPSHOT_JS,
                WENXIN_SEARCH_SNAPSHOT_JS,
                "location.href",
                "String(performance.timeOrigin||0)",
            }
            for attempt in range(4):
                try:
                    return self.page.evaluate(expression)
                except Exception as error:
                    # Only these exact, audited snapshots are safe to repeat.
                    # Arbitrary expressions may submit and are never replayed.
                    navigation = "Execution context was destroyed" in str(
                        error
                    ) or "Cannot find context with specified id" in str(error)
                    if not read_only or not navigation or attempt == 3:
                        raise
                    time.sleep(0.5 * (attempt + 1))
        finally:
            self.page.set_default_timeout(self.timeout_ms)

    def click(self, x: int, y: int) -> None:
        self.page.mouse.click(float(x), float(y), button="left")

    def replace_tab(self, url: str, timeout: float = 20) -> dict[str, str]:
        old_page = self.page
        old_target = self._target(old_page)
        context = self.session.context
        if context is None:
            raise RuntimeError("Scrapling 隐身浏览器上下文已经关闭")
        new_page = context.new_page()
        new_page.set_default_timeout(self.timeout_ms)
        new_page.set_default_navigation_timeout(self.timeout_ms)
        try:
            new_page.goto(
                str(url or "about:blank"),
                wait_until="domcontentloaded",
                timeout=max(3_000, int(timeout * 1000)),
            )
        except Exception:
            new_page.close()
            raise
        self.page = new_page
        self._adaptive_snapshot_cache = None
        old_page.close()
        return {
            "old_target": old_target,
            "new_target": self._target(new_page),
            "url": str(url or "about:blank"),
        }

    def close(self) -> None:
        try:
            self.session.close()
        finally:
            if getattr(self, "_adaptive_store", None) is not None:
                self._adaptive_store.close()
                self._adaptive_store = None


BAIDU_AI_SNAPSHOT_JS = r"""
(()=>{
  const card = document.querySelector(
    '#content_left [tpl="new_baikan_index"], #content_left [m-name*="new_baikan_index"], ' +
    '#content_left [tpl="wenda_generate"], #content_left .ai-entry'
  );
  const query = String(
    document.querySelector('#kw')?.value ||
    document.querySelector('input[name="wd"]')?.value || ''
  ).trim();
  if (!card) {
    return {
      ok:false,
      cardPresent:false,
      searchResultsCount:document.querySelectorAll('#content_left .result, #content_left .c-container').length,
      url:location.href,
      query,
      readyState:document.readyState,
      pageText:String(document.body?.innerText || '').slice(0, 1200)
    };
  }
  const chunks = [];
  const seen = new Set();
  for (const element of card.querySelectorAll(
    '[class*="accordion-panels-title"], .cosd-markdown-content'
  )) {
    const text = String(element.innerText || '')
      .replace(/[\u200b-\u200f\u202a-\u202e\u2060\ufeff]/g, '')
      .trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    chunks.push(text);
  }
  const body = chunks.join('\n\n').trim();
  const folded = Array.from(card.querySelectorAll('button, [role="button"], div, span'))
    .some(element => /^展开(?:剩余\s*\d+\s*%\s*(?:内容|结果)|全部(?:内容|结果)?|更多(?:内容|结果)?|全文)?$/.test(String(element.innerText || '').trim()) && element.getBoundingClientRect().height > 0);
  const citationSelectors = [
    '.cosd-citation',
    '[data-citation]',
    '[data-source-index]',
    'a[class*="citation"], button[class*="citation"], span[class*="citation"]',
    '[class*="reference"] a[href]'
  ];
  let citations = [];
  for (const selector of citationSelectors) {
    citations = Array.from(card.querySelectorAll(selector));
    if (citations.length) break;
  }
  return {
    ok:Boolean(body),
    cardPresent:true,
    url:location.href,
    query,
    body,
    folded,
    citationCount:citations.length,
    readyState:document.readyState,
    cardId:String(card.id || ''),
    cardTemplate:String(card.getAttribute('tpl') || '')
  };
})()
"""


BAIDU_AI_SOURCES_JS = r"""
(async()=>{
  const card = document.querySelector(
    '#content_left [tpl="new_baikan_index"], #content_left [m-name*="new_baikan_index"], ' +
    '#content_left [tpl="wenda_generate"], #content_left .ai-entry'
  );
  if (!card) return {ok:false, error:'ai_card_missing', sources:[]};
  const citations = Array.from(card.querySelectorAll('.cosd-citation'));
  const found = new Map();
  let citationsWithSources = 0;
  const delay = (milliseconds) => new Promise(resolve => setTimeout(resolve, milliseconds));
  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
      rect.width > 0 && rect.height > 0;
  };
  for (const citation of citations) {
    citation.scrollIntoView({block:'center', inline:'nearest'});
    try {
      citation.click();
    } catch (_) {
      citation.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
    }
    await delay(450);
    const current = new Set();
    for (const popup of Array.from(document.querySelectorAll('.cos-tooltip-content')).filter(visible)) {
      for (const anchor of popup.querySelectorAll('a[href]')) {
        const href = String(anchor.href || anchor.getAttribute('href') || '').trim();
        const title = String(
          anchor.querySelector('.cosd-citation-title-text')?.innerText ||
          anchor.innerText || anchor.title || ''
        ).trim();
        if (!href || !title) continue;
        const item = anchor.closest('.cosd-citation-aggregated-item') || anchor.parentElement;
        const media = String(item?.querySelector('.cos-color-text-slim')?.innerText || '').trim();
        const key = href + '\u0000' + title;
        current.add(key);
        found.set(key, {url:href, title, media});
      }
    }
    if (current.size) citationsWithSources += 1;
  }
  return {
    ok:true,
    citationCount:citations.length,
    citationsWithSources,
    sources:Array.from(found.values())
  };
})()
"""


BAIDU_VISIBLE_SOURCES_JS = r"""
(()=>{
  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
      rect.width > 0 && rect.height > 0;
  };
  const sources = [];
  for (const popup of Array.from(document.querySelectorAll('.cos-tooltip-content')).filter(visible)) {
    for (const anchor of popup.querySelectorAll('a[href]')) {
      const href = String(anchor.href || anchor.getAttribute('href') || '').trim();
      const title = String(
        anchor.querySelector('.cosd-citation-title-text')?.innerText ||
        anchor.innerText || anchor.title || ''
      ).trim();
      if (!href || !title) continue;
      const item = anchor.closest('.cosd-citation-aggregated-item') || anchor.parentElement;
      sources.push({
        url:href,
        title,
        media:String(item?.querySelector('.cos-color-text-slim')?.innerText || '').trim()
      });
    }
  }
  return {sources};
})()
"""


WENXIN_SEARCH_SNAPSHOT_JS = r"""
(()=>{
  const pageText = String(document.body?.innerText || '');
  const chunks = [];
  const seen = new Set();
  for (const element of document.querySelectorAll('.cosd-markdown-content')) {
    const text = String(element.innerText || '')
      .replace(/[\u200b-\u200f\u202a-\u202e\u2060\ufeff]/g, '')
      .trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    chunks.push(text);
  }
  const sources = [];
  const sourceKeys = new Set();
  let parsedSourceItemCount = 0;
  const sourceItems = Array.from(document.querySelectorAll('li[data-long-press-ext-info]'));
  for (const item of sourceItems) {
    let metadata = {};
    try { metadata = JSON.parse(item.getAttribute('data-long-press-ext-info') || '{}'); }
    catch (_) { metadata = {}; }
    const anchor = item.querySelector('a[href]');
    const url = String(metadata.link || anchor?.href || anchor?.getAttribute('href') || '').trim();
    const title = String(
      metadata.linkTitle || item.querySelector('[class*="_text_"]')?.innerText ||
      anchor?.innerText || anchor?.title || item.innerText || ''
    ).trim();
    const key = url + '\u0000' + title;
    if (!url || !title) continue;
    parsedSourceItemCount += 1;
    if (sourceKeys.has(key)) continue;
    sourceKeys.add(key);
    sources.push({url, title, media:''});
  }
  const counts = [...pageText.matchAll(/(?:共参考|搜索全网)\s*(\d+)\s*篇资料/g)].map(m=>Number(m[1]));
  const busy = [...document.querySelectorAll('button,[role=button]')].some(el=>{
    const r=el.getBoundingClientRect(),s=getComputedStyle(el);
    return r.width>0&&r.height>0&&s.visibility!=='hidden'&&
      /^(停止生成|停止回答)$/.test(String(el.innerText||el.getAttribute('aria-label')||'').trim());
  });
  return {
    ok:chunks.join('\n\n').trim().length >= 40,
    url:location.href,
    queryCandidates:[...document.querySelectorAll('input,textarea,h1,[class*="question"],[class*="query-title"]')]
      .map(e=>String(e.value||e.innerText||'').trim()).filter(t=>t.length>0&&t.length<300),
    pageText:pageText.slice(0, 1200),
    readyState:document.readyState,
    finished:Boolean(document.querySelector('[class*="answer-finished"]')) && !busy,
    body:chunks.join('\n\n').trim(),
    expectedSourceCount:counts.length ? Math.max(...counts) : 0,
    sourceItemCount:sourceItems.length,
    extractedSourceItemCount:parsedSourceItemCount,
    sources
  };
})()
"""


class WenxinWebCollector:
    """Collect Baidu search AI answers directly; no emulator or Wenxin App is used."""

    HOME = "https://www.baidu.com/"
    SEARCH = "https://www.baidu.com/s"
    WENXIN_SEARCH = "https://chat.baidu.com/search"

    def __init__(
        self,
        port: int = 9444,
        *,
        page: CDPPage | None = None,
        session: requests.Session | None = None,
        profile: Path | None = None,
    ):
        if page is None:
            del (
                port
            )  # Kept in the public signature for existing control-panel settings.
            page = ScraplingStealthPage(
                profile
                or (runtime_root() / "profiles" / "baidu" / "scrapling_profile"),
                timeout=60,
            )
        self.page = page
        self.session = session or requests.Session()

    def close(self) -> None:
        close = getattr(self.page, "close", None)
        if callable(close):
            close()
        self.session.close()

    @staticmethod
    def search_url(question: str) -> str:
        return f"{WenxinWebCollector.SEARCH}?{urlencode({'wd': str(question or '').strip()})}"

    @staticmethod
    def _compact(value: str) -> str:
        return re.sub(r"\s+", "", str(value or ""))

    @staticmethod
    def _query_key(value: str) -> str:
        # Baidu normalizes full-width punctuation in its search box. Keep
        # exact wording and punctuation; only normalize Unicode width/spacing.
        return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")))

    @staticmethod
    def _is_security_verification(snapshot: dict[str, Any]) -> bool:
        url = str(snapshot.get("url") or "").casefold()
        text = str(snapshot.get("pageText") or "")
        return (
            "wappass.baidu.com" in url
            or "/static/captcha/" in url
            or "百度安全验证" in text
            or "请完成下方验证" in text
        )

    def ensure_ready(self, timeout: int = 30) -> dict[str, Any]:
        self.page.call("Page.navigate", {"url": self.HOME})
        deadline = time.monotonic() + max(5, timeout)
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last = (
                self.page.evaluate(
                    "({url:location.href,title:document.title,body:String(document.body?.innerText||'').slice(0,500)})"
                )
                or {}
            )
            if self._is_security_verification(
                {**last, "pageText": last.get("body", "")}
            ):
                raise SecurityVerificationError("检测到百度安全验证，网页未就绪")
            if "baidu.com" in str(last.get("url") or "") and "百度" in (
                str(last.get("title") or "") + str(last.get("body") or "")
            ):
                return {"ok": True, **last}
            time.sleep(0.5)
        raise TimeoutError(f"百度搜索专用 Chrome 未就绪：{last}")

    def account_identity(self) -> dict[str, str]:
        self.ensure_ready()
        return {"name": "百度搜索 AI 直采", "masked": "无需登录"}

    def reset_after_round(self) -> dict[str, str]:
        """Open one clean Baidu tab and close the exact tab used by the completed round."""
        return self.page.replace_tab(self.HOME)

    def _navigate_fresh(self, url: str) -> str:
        """Navigate to a new document and return its CDP loader identity.

        A repeated Baidu card is still a valid new observation when it came
        from a new search document.  The loader id distinguishes that case from
        accidentally rereading the previous tab while its DOM is still visible.
        """
        previous_origin = (
            str(self.page.evaluate("String(performance.timeOrigin||0)") or "")
            if getattr(self.page, "is_stealth", False)
            else ""
        )
        try:
            value = self.page.call("Page.navigate", {"url": url}) or {}
        except Exception as error:
            if "Timeout" not in type(error).__name__ and "Timeout" not in str(error):
                raise
            # User-authorized recovery of this read-only search, never a new
            # question or an unchecked refresh of another result document.
            current = str(self.page.evaluate("location.href") or "")
            if current != url:
                raise
            value = (
                self.page.call("Page.reload", {"ignoreCache": False}, timeout=60) or {}
            )
        loader_id = str(value.get("loaderId") or "") if isinstance(value, dict) else ""
        if loader_id:
            identity = f"loader:{loader_id}"
            if identity == getattr(self, "_last_navigation_id", None):
                raise RuntimeError("搜索未产生新文档，拒绝复用上一轮页面")
            self._last_navigation_id = identity
            return identity
        # Scrapling wraps Playwright and exposes a stable page/frame identity
        # instead of CDP's loaderId.  performance.timeOrigin changes for every
        # real document navigation, so their combination is equally suitable
        # for rejecting a stale DOM without rejecting a valid repeated card.
        frame_id = str(value.get("frameId") or "") if isinstance(value, dict) else ""
        time_origin = str(self.page.evaluate("String(performance.timeOrigin||0)") or "")
        valid_time_origin = time_origin not in {"", "0", "0.0", "nan", "NaN"}
        if getattr(self.page, "is_stealth", False) and (
            not frame_id or not valid_time_origin
        ):
            raise RuntimeError("百度新页面导航凭证不完整，拒绝把旧页面当成新轮次")
        identity = f"frame:{frame_id}:time:{time_origin}"
        if (
            identity == getattr(self, "_last_navigation_id", None)
            or previous_origin
            and previous_origin == time_origin
        ):
            raise RuntimeError("搜索未产生新文档，拒绝复用上一轮页面")
        self._last_navigation_id = identity
        return identity

    @classmethod
    def _wenxin_question_matches(cls, snapshot, question):
        parsed = urlparse(str(snapshot.get("url") or ""))
        if parsed.hostname not in {
            "www.baidu.com",
            "baidu.com",
            "wenxin.baidu.com",
            "chat.baidu.com",
        }:
            return False
        expected = cls._query_key(question)
        query = parse_qs(parsed.query).get("word", [""])[0]
        if query:
            return cls._query_key(query) == expected
        # Wenxin redirects to /search/<id>, removing the word parameter.
        # Require an exact displayed question, never a substring in an answer.
        candidates = list(snapshot.get("queryCandidates") or [])
        candidates.extend(str(snapshot.get("pageText") or "").splitlines())
        return bool(expected) and any(
            cls._query_key(value) == expected for value in candidates
        )

    def _resolve_source_url(self, url: str) -> str:
        value = str(url or "").strip()
        parsed = urlparse(value)
        if (
            parsed.netloc.casefold().removeprefix("www.") != "baidu.com"
            or parsed.path != "/link"
        ):
            return value
        try:
            response = self.session.get(
                value,
                allow_redirects=False,
                stream=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            try:
                location = str(response.headers.get("Location") or "").strip()
            finally:
                response.close()
            resolved = urljoin(value, location)
            if urlparse(resolved).scheme in {"http", "https"}:
                return resolved
        except requests.RequestException:
            pass
        return value

    def _normalize_sources(self, raw_sources: list[Any]) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        seen: set[str] = set()
        for raw in raw_sources:
            if not isinstance(raw, dict):
                continue
            original = str(raw.get("url") or "").strip()
            title = str(raw.get("title") or "").strip()
            if not original or not title:
                continue
            resolved = self._resolve_source_url(original)
            key = resolved.rstrip("/").casefold()
            if key in seen:
                continue
            seen.add(key)
            output.append(
                {
                    "url": resolved,
                    "baidu_redirect_url": original if resolved != original else "",
                    "title": title,
                    "media": str(raw.get("media") or "").strip(),
                }
            )
        return output

    def _expand_ai_card(self) -> bool:
        point = self.page.evaluate(r"""
(()=>{
  const card = document.querySelector(
    '#content_left [tpl="new_baikan_index"], #content_left [m-name*="new_baikan_index"], ' +
    '#content_left [tpl="wenda_generate"], #content_left .ai-entry'
  );
  if (!card) return null;
  // Product carousels also say "查看更多". They do not expand the answer
  // and may navigate away. Use only the answer's explicit expansion control.
  const controls = Array.from(card.querySelectorAll('.cos-fold-switch-text, button, [role="button"], div, span'));
  const control = controls.find(element => /^展开(?:剩余\s*\d+\s*%\s*(?:内容|结果)|全部(?:内容|结果)?|更多(?:内容|结果)?|全文)?$/.test(String(element.innerText || '').trim()) && element.getBoundingClientRect().height > 0);
  if (!control) return null;
  control.scrollIntoView({block:'center', inline:'nearest'});
  const rect = control.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0
    ? {x:rect.left + rect.width / 2, y:rect.top + rect.height / 2}
    : null;
})()
""")
        if isinstance(point, dict):
            self.page.click(int(point["x"]), int(point["y"]))
            time.sleep(0.6)
            return True
        return False

    def _scroll_ai_card(self) -> None:
        """Visibly walk the full AI card so lazy content and citations are loaded."""
        bounds = self.page.evaluate(r"""
(()=>{
  const card = document.querySelector(
    '#content_left [tpl="new_baikan_index"], #content_left [m-name*="new_baikan_index"], ' +
    '#content_left [tpl="wenda_generate"], #content_left .ai-entry'
  );
  if (!card) return null;
  const rect = card.getBoundingClientRect();
  return {top:Math.max(0, rect.top + scrollY - 100), bottom:rect.bottom + scrollY};
})()
""")
        if not isinstance(bounds, dict):
            return
        position = int(bounds.get("top") or 0)
        bottom = int(bounds.get("bottom") or position)
        step = 520
        while position < bottom:
            self.page.evaluate(
                f"window.scrollTo({{top:{position},behavior:'instant'}})"
            )
            time.sleep(0.25)
            position += step
        self.page.evaluate(
            f"window.scrollTo({{top:{max(position, bottom)},behavior:'instant'}})"
        )
        time.sleep(0.4)

    def _scroll_document(self) -> None:
        height = int(
            self.page.evaluate(
                "Math.max(document.body.scrollHeight,document.documentElement.scrollHeight)"
            )
            or 0
        )
        position = 0
        while position < height:
            self.page.evaluate(
                f"window.scrollTo({{top:{position},behavior:'instant'}})"
            )
            time.sleep(0.2)
            position += 560
        self.page.evaluate(f"window.scrollTo({{top:{height},behavior:'instant'}})")
        time.sleep(0.4)

    def _settled_wenxin_snapshot(self, timeout: int = 15) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        previous = None
        while time.monotonic() < deadline:
            current = self.page.evaluate(WENXIN_SEARCH_SNAPSHOT_JS, timeout=30) or {}
            if self._is_security_verification(current):
                raise SecurityVerificationError("检测到百度安全验证")
            body = str(current.get("body") or "")
            if current.get("finished") and len(self._compact(body)) >= 40:
                if body == previous:
                    return current
                previous = body
            else:
                previous = None
            time.sleep(1)
        raise TimeoutError("文心正文滚动后未能确认完成并稳定")

    def _expand_wenxin_sources(self) -> bool:
        point = self.page.evaluate(r'''(()=>{
          const label=/^(?:(?:查看|展开|显示)?全部|查看更多|展开更多)(?:信源|来源|资料)$/;
          const elements=[...document.querySelectorAll('button,[role="button"],span')];
          const e=elements.find(e=>label.test((e.innerText||'').trim()) &&
            !e.closest('a[href]') && e.getBoundingClientRect().width>0 && e.getBoundingClientRect().height>0);
          if(!e)return null;
          e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
          return {x:r.left+r.width/2,y:r.top+r.height/2};
        })()''')
        if not isinstance(point, dict):
            return False
        self.page.click(int(point['x']), int(point['y']))
        return True

    def collect_wenxin_search(self, question: str, timeout: int = 90) -> dict[str, Any]:
        current_url = (
            str(self.page.evaluate("location.href") or "")
            if getattr(self.page, "is_stealth", False)
            else self.HOME
        )
        if "baidu.com" not in current_url:
            self.page.call("Page.navigate", {"url": self.HOME}, timeout=30)
            time.sleep(random.uniform(1.8, 3.2))
        url = f"{self.WENXIN_SEARCH}?{urlencode({'word': question, 'pd': 'csaitab', 'setype': 'csaitab'})}"
        navigation_id = self._navigate_fresh(url)
        deadline = time.monotonic() + max(30, timeout)
        stable = 0
        previous_body = ""
        expansions = 0
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            if expansions < 3 and self._expand_wenxin_sources():
                expansions += 1
                time.sleep(0.5)
            value = self.page.evaluate(WENXIN_SEARCH_SNAPSHOT_JS, timeout=30)
            last = value if isinstance(value, dict) else {}
            if self._is_security_verification(last):
                raise SecurityVerificationError("检测到百度安全验证，立即关闭当前页面")
            body = str(last.get("body") or "")
            sources = list(last.get("sources") or [])
            expected = int(last.get("expectedSourceCount") or 0)
            source_items = int(last.get("sourceItemCount") or expected)
            extracted_items = int(last.get("extractedSourceItemCount") or len(sources))
            body_complete = bool(
                last.get("ok")
                and last.get("finished")
                and len(self._compact(body)) >= 40
                and self._wenxin_question_matches(last, question)
            )
            sources_complete = bool(
                source_items > 0 and extracted_items >= max(source_items, expected)
            )
            stable = (
                stable + 1
                if body_complete and body == previous_body
                else (1 if body_complete else 0)
            )
            previous_body = body
            if stable >= 2 and sources_complete:
                break
            time.sleep(1)
        else:
            # A finished answer must not block the entire production queue merely
            # because Baidu reports one more reference card than it exposes as a
            # usable unique URL.  Preserve the completeness flag and let the
            # pipeline ingest the usable answer and links transparently.
            if stable < 2 or len(self._compact(previous_body)) < 40:
                raise TimeoutError(
                    f"文心入口回答未完整：{question}（正文 {len(previous_body)} 字，"
                    f"信源 {len(last.get('sources') or [])}/{int(last.get('expectedSourceCount') or 0)} 条）"
                )
        self._scroll_document()
        # Re-read after visible scrolling in case the page lazy-loaded more references.
        final = self._settled_wenxin_snapshot()
        body = str(final.get("body") or "")
        if not self._wenxin_question_matches(final, question):
            raise RuntimeError("文心最终页面问题不匹配，拒绝保存其他问题的正文")
        raw_sources = list(final.get("sources") or [])
        sources = self._normalize_sources(raw_sources)
        displayed_items = int(final.get("expectedSourceCount") or 0)
        source_items = int(final.get("sourceItemCount") or displayed_items)
        extracted_items = int(final.get("extractedSourceItemCount") or len(raw_sources))
        if len(self._compact(body)) < 40:
            raise RuntimeError(f"文心入口正文完整性复核失败：正文 {len(body)} 字")
        source_capture_complete = bool(
            sources and source_items > 0 and extracted_items >= max(source_items, displayed_items)
        )
        # The page's article count includes duplicate cards.  Once every card
        # has been parsed, production statistics intentionally use unique URLs.
        expected_unique = len(sources) if source_capture_complete else displayed_items
        return {
            "url": str(final.get("url") or url),
            "body": body,
            "page_body": body,
            "body_capture_complete": True,
            "sources": sources,
            "source_count": len(sources),
            "expected_source_count": expected_unique,
            "citation_count": source_items,
            "displayed_source_count": displayed_items,
            "source_capture_complete": source_capture_complete,
            "capture_warning": (
                ""
                if source_capture_complete
                else f"页面标示 {displayed_items} 篇资料，解析 {extracted_items}/{source_items} 个资料项，"
                f"取得 {len(sources)} 条有效唯一链接"
            ),
            "capture_mode": "baidu_wenxin_search",
            "page_navigation_id": navigation_id,
            "fresh_search": True,
            "verified_question": question,
        }

    def _citation_point(self, index: int) -> dict[str, float] | None:
        adaptive_point = getattr(self.page, "adaptive_citation_point", None)
        if callable(adaptive_point):
            try:
                point = adaptive_point(index)
                if isinstance(point, dict):
                    return point
            except Exception:
                # Keep the live-DOM selector fallback for first-run pages before
                # Scrapling has learned a stable element fingerprint.
                pass
        value = self.page.evaluate(rf"""
(()=>{{
  const card = document.querySelector(
    '#content_left [tpl="new_baikan_index"], #content_left [m-name*="new_baikan_index"], ' +
    '#content_left [tpl="wenda_generate"], #content_left .ai-entry'
  );
  const citationSelectors = [
    '.cosd-citation',
    '[data-citation]',
    '[data-source-index]',
    'a[class*="citation"], button[class*="citation"], span[class*="citation"]',
    '[class*="reference"] a[href]'
  ];
  let citations = [];
  for (const selector of citationSelectors) {{
    citations = Array.from(card?.querySelectorAll(selector) || []);
    if (citations.length) break;
  }}
  // Keep the legacy lookup as a compatibility fallback for cached result DOMs.
  const legacyCitation = card?.querySelectorAll('.cosd-citation')[{int(index)}];
  const citation = citations[{int(index)}] || legacyCitation;
  if (!citation) return null;
  citation.scrollIntoView({{block:'center', inline:'nearest'}});
  const rect = citation.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0
    ? {{x:rect.left + rect.width / 2, y:rect.top + rect.height / 2}}
    : null;
}})()
""")
        return value if isinstance(value, dict) else None

    def _visible_sources(self) -> list[dict[str, str]]:
        value = self.page.evaluate(BAIDU_VISIBLE_SOURCES_JS, timeout=20)
        return list(value.get("sources") or []) if isinstance(value, dict) else []

    def public_card_references(self) -> dict[str, Any]:
        """Inspect only reference containers, never shopping or related-search links."""
        opened=self.page.evaluate(r'''(()=>{const card=document.querySelector('#content_left [tpl="new_baikan_index"],#content_left [tpl="wenda_generate"],#content_left .cosc-card');if(!card)return false;const candidates=[...card.querySelectorAll('button,[role=button],a,[tabindex],span,div')].filter(e=>{const t=(e.innerText||'').trim();return t.length<90&&/参考\s*\d+\s*篇(?:资料|内容)|(?:查看|展开).*(?:信源|来源|参考资料)/.test(t)});const el=candidates.sort((a,b)=>a.innerText.length-b.innerText.length)[0];if(!el)return false;el.scrollIntoView({block:'center'});el.click();return true})()''')
        if opened:time.sleep(1.2)
        result=self.page.evaluate(r'''(()=>{const card=document.querySelector('#content_left [tpl="new_baikan_index"],#content_left [tpl="wenda_generate"],#content_left .cosc-card');if(!card)return {};const text=card.innerText||'';const counts=[...text.matchAll(/(?:参考|AI总结)\s*(\d+)\s*篇(?:资料|内容|结果)?/g)].map(m=>Number(m[1]));const roots=[card,...document.querySelectorAll('[role="dialog"],[class*="reference"][class*="drawer"]')];const sources=[];for(const root of roots){if(!root.getBoundingClientRect().height)continue;for(const a of root.querySelectorAll('[class*="citation"] a[href],[class*="reference"] a[href],[class*="source"] a[href]')){if(a.closest('[class*="goods"],[class*="shopping"]'))continue;const u=a.href,t=(a.querySelector('[class*="title"]')?.innerText||a.title||a.innerText||'').trim();if(!/^https?:/.test(u)||!t||/\/s\?/.test(u))continue;sources.push({url:u,title:t,media:''})}}return {declared_count:Math.max(0,...counts),sources,card_present:true,card_template:card.getAttribute('tpl'),footer:text.slice(-350)}})()''') or {}
        return {**result,'drawer_opened':bool(opened)}

    def _collect_citation_sources(
        self, citation_count: int
    ) -> tuple[list[dict[str, str]], int]:
        raw_sources: list[dict[str, str]] = []
        citations_with_sources = 0
        for index in range(citation_count):
            current: list[dict[str, str]] = []
            for attempt in range(3):
                # Close the previous tooltip first.  Without this, a slow Baidu
                # render can leave the preceding citation visible and make the
                # next marker look empty (or falsely reuse the previous links).
                self.page.call(
                    "Input.dispatchMouseEvent",
                    {"type": "mouseMoved", "x": 8 + attempt, "y": 8 + attempt},
                )
                time.sleep(0.3 + attempt * 0.2)
                point = self._citation_point(index)
                if point is None:
                    continue
                coordinates = {"x": int(point["x"]), "y": int(point["y"])}
                self.page.call(
                    "Input.dispatchMouseEvent", {"type": "mouseMoved", **coordinates}
                )
                time.sleep(0.8 + attempt * 0.35)
                current = self._visible_sources()
                if not current:
                    self.page.click(coordinates["x"], coordinates["y"])
                    time.sleep(0.8 + attempt * 0.35)
                    current = self._visible_sources()
                if current:
                    break
            if current:
                citations_with_sources += 1
                raw_sources.extend(current)
        return raw_sources, citations_with_sources

    def collect_search(
        self,
        question: str,
        timeout: int = 90,
        *,
        preloaded_navigation_id: str = "",
    ) -> dict[str, Any]:
        question = str(question or "").strip()
        if not question:
            raise ValueError("百度搜索问题不能为空")
        current_url = (
            str(self.page.evaluate("location.href") or "")
            if getattr(self.page, "is_stealth", False)
            else self.HOME
        )
        if preloaded_navigation_id:
            if "baidu.com" not in current_url:
                raise RuntimeError("文心批量回收页面已离开百度，拒绝抓取以防串轮")
            url = current_url
            navigation_id = preloaded_navigation_id
        else:
            if "baidu.com" not in current_url:
                self.page.call("Page.navigate", {"url": self.HOME}, timeout=30)
                time.sleep(random.uniform(1.8, 3.2))
            url = self.search_url(question)
            navigation_id = self._navigate_fresh(url)
        deadline = time.monotonic() + max(10, timeout)
        stable = 0
        complete_without_ai = 0
        previous_body = ""
        last: dict[str, Any] = {}
        expansion_attempts = 0
        while time.monotonic() < deadline:
            value = self.page.evaluate(BAIDU_AI_SNAPSHOT_JS, timeout=30)
            last = value if isinstance(value, dict) else {}
            if self._is_security_verification(last):
                raise SecurityVerificationError("检测到百度安全验证，立即关闭当前页面")
            body = str(last.get("body") or "")
            query_matches = self._query_key(last.get("query") or "") == self._query_key(
                question
            )
            ready = last.get("readyState") == "complete"
            if query_matches and last.get("cardPresent") and expansion_attempts < 3:
                # Expand before demanding a long body: collapsed cards can
                # contain only a heading and never reach that threshold.
                if self._expand_ai_card():
                    expansion_attempts += 1
                    stable = 0
                    continue
            if (
                last.get("ok")
                and query_matches
                and ready
                and len(self._compact(body)) >= 40
            ):
                complete_without_ai = 0
                stable = stable + 1 if body == previous_body else 1
                previous_body = body
                if stable >= 2:
                    break
            else:
                stable = 0
                previous_body = body
                # Baidu sometimes completes a redirected/cached result page but
                # leaves the search box empty or carrying the previous query.
                # Waiting the full collector timeout in that state only blocks
                # the enterprise queue.  After a short stable page window, use
                # the dedicated Wenxin result entry, which is authoritative for
                # both the answer and its source list.
                complete_without_ai = complete_without_ai + 1 if ready else 0
                if complete_without_ai >= 12 and (
                    not getattr(self, "strict_card", False)
                    or (
                        query_matches
                        and last.get("cardPresent") is False
                        and int(last.get("searchResultsCount") or 0) > 0
                    )
                ):
                    return self.collect_wenxin_search(
                        question, timeout=max(45, timeout)
                    )
            time.sleep(1)
        else:
            return self.collect_wenxin_search(question, timeout=max(45, timeout))

        self._expand_ai_card()
        expanded_stable = 0
        expanded_body = ""
        expanded_deadline = min(deadline, time.monotonic() + 15)
        while time.monotonic() < expanded_deadline:
            value = self.page.evaluate(BAIDU_AI_SNAPSHOT_JS, timeout=30)
            expanded = value if isinstance(value, dict) else {}
            body = str(expanded.get("body") or "")
            if (
                expanded.get("ok")
                and not expanded.get("folded")
                and len(body) >= len(previous_body)
            ):
                expanded_stable = expanded_stable + 1 if body == expanded_body else 1
                expanded_body = body
                last = expanded
                if expanded_stable >= 2:
                    previous_body = expanded_body
                    break
            else:
                expanded_stable = 0
                expanded_body = body
            time.sleep(0.5)
        else:
            raise RuntimeError("百度 AI 回答未能完全展开并稳定，拒绝保存可能截断的正文")

        self._scroll_ai_card()
        # Citation widgets can appear several seconds after the answer text.
        # A stable body alone is insufficient evidence of complete provenance.
        provenance_deadline = min(deadline, time.monotonic() + 25)
        provenance_stable = 0
        previous_provenance = None
        while time.monotonic() < provenance_deadline:
            value = self.page.evaluate(BAIDU_AI_SNAPSHOT_JS, timeout=30)
            snapshot = value if isinstance(value, dict) else {}
            if self._is_security_verification(snapshot):
                raise SecurityVerificationError("检测到百度安全验证，立即关闭当前页面")
            body = str(snapshot.get("body") or "")
            signature = (body, int(snapshot.get("citationCount") or 0))
            if (
                snapshot.get("ok")
                and not snapshot.get("folded")
                and self._query_key(snapshot.get("query") or "")
                == self._query_key(question)
                and len(body) >= len(previous_body)
                and signature[1] > 0
            ):
                provenance_stable = (
                    provenance_stable + 1 if signature == previous_provenance else 1
                )
                last = snapshot
                previous_body = body
                if provenance_stable >= 3:
                    break
            else:
                provenance_stable = 0
            previous_provenance = signature
            time.sleep(1)
        else:
            return self.collect_wenxin_search(question, timeout=max(45, timeout))
        adaptive_snapshot = getattr(self.page, "adaptive_ai_snapshot", None)
        if callable(adaptive_snapshot):
            try:
                adaptive = adaptive_snapshot()
                adaptive_body = str(adaptive.get("body") or "")
                # Prefer the larger stable body; this also protects against a
                # renamed answer class truncating the JavaScript extraction.
                if len(self._compact(adaptive_body)) > len(
                    self._compact(previous_body)
                ):
                    previous_body = adaptive_body
                last["citationCount"] = max(
                    int(last.get("citationCount") or 0),
                    int(adaptive.get("citationCount") or 0),
                )
            except Exception:
                pass
        citation_count = int(last.get("citationCount") or 0)
        # A Baidu AI answer always has provenance.  A zero count means the result
        # page changed its citation markup (or lazy rendering has not completed),
        # never that a source-less capture is production-complete.  Use the
        # dedicated Wenxin result page as the authoritative fallback instead of
        # incorrectly persisting a successful 0/0 round.
        if citation_count <= 0:
            return self.collect_wenxin_search(question, timeout=max(45, timeout))
        raw_sources, captured_citations = self._collect_citation_sources(citation_count)
        sources = self._normalize_sources(raw_sources)
        if citation_count and captured_citations < citation_count:
            # The card exists but one or more citation popups are not usable.
            # This is the same fallback condition as a missing card: obtain the
            # authoritative answer/reference list from the Wenxin result page.
            return self.collect_wenxin_search(question, timeout=max(45, timeout))
        if not sources:
            return self.collect_wenxin_search(question, timeout=max(45, timeout))
        return {
            "url": url,
            "body": previous_body,
            "page_body": previous_body,
            "body_capture_complete": True,
            "sources": sources,
            "source_count": len(sources),
            "expected_source_count": len(sources),
            "citation_count": citation_count,
            "source_capture_complete": True,
            "capture_mode": "baidu_search_ai",
            "page_navigation_id": navigation_id,
            "fresh_search": True,
            "verified_question": question,
        }
