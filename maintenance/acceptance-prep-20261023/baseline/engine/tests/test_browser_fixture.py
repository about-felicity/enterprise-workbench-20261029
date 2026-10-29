"""Opt-in integration test using real headless Chrome and a local HTML fixture."""

import os
import socket
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from web_collectors.collector import BrowserCollector
from web_collectors.config import SiteConfig
from wenxin_monitor.controller import (
    BAIDU_AI_SNAPSHOT_JS,
    BAIDU_VISIBLE_SOURCES_JS,
    WENXIN_SEARCH_SNAPSHOT_JS,
    ScraplingStealthPage,
    WenxinWebCollector,
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(
    os.environ.get("GEO_RUN_BROWSER_TESTS") == "1",
    "Set GEO_RUN_BROWSER_TESTS=1 to use installed Chrome",
)
class BrowserFixtureTests(unittest.TestCase):
    def test_answer_expansion_ignores_product_more_link(self):
        fixture = Path(__file__).parent / 'fixtures' / 'baidu_ai.html'
        with tempfile.TemporaryDirectory() as temp:
            page = ScraplingStealthPage(Path(temp) / 'profile')
            collector = WenxinWebCollector(page=page)
            try:
                page.page.set_content(fixture.read_text(encoding='utf8'))
                page.evaluate("""(()=>{
                  const card=document.querySelector('.ai-entry');
                  const goods=document.createElement('button');goods.textContent='查看更多';
                  goods.onclick=()=>{document.body.dataset.wrongClick='yes'};card.prepend(goods);
                  const expand=document.createElement('span');expand.className='cos-fold-switch-text';
                  expand.textContent='展开剩余47%结果';expand.onclick=()=>expand.remove();card.append(expand);
                })()""")
                self.assertTrue(page.evaluate(BAIDU_AI_SNAPSHOT_JS)['folded'])
                self.assertTrue(collector._expand_ai_card())
                self.assertFalse(page.evaluate(BAIDU_AI_SNAPSHOT_JS)['folded'])
                self.assertIsNone(page.evaluate('document.body.dataset.wrongClick || null'))
                self.assertFalse(collector._expand_ai_card())
            finally:
                collector.close()

    def test_expand_short_card_before_body_threshold(self):
        fixture = Path(__file__).parent / "fixtures" / "baidu_ai.html"
        with tempfile.TemporaryDirectory() as temp:
            page = ScraplingStealthPage(Path(temp) / "profile")
            collector = WenxinWebCollector(page=page)
            try:
                page.page.set_content(fixture.read_text(encoding="utf8"))
                page.evaluate(
                    "document.querySelectorAll('.cosd-markdown-content').forEach(e=>e.style.display='none');const b=document.createElement('button');b.textContent='展开全部';b.onclick=()=>{document.querySelectorAll('.cosd-markdown-content').forEach(e=>e.style.display='block');b.remove()};document.querySelector('.ai-entry').appendChild(b)"
                )
                snapshot = page.evaluate(BAIDU_AI_SNAPSHOT_JS)
                self.assertTrue(snapshot["folded"])
                original = page.evaluate
                with patch.object(
                    page,
                    "evaluate",
                    side_effect=lambda script, **kw: (
                        "https://www.baidu.com/s?wd=fixture"
                        if script == "location.href"
                        else original(script, **kw)
                    ),
                ):
                    result = collector.collect_search(
                        "测试问题", timeout=25, preloaded_navigation_id="fixture-short"
                    )
                self.assertIn("正文第一段", result["body"])
                self.assertTrue(result["source_capture_complete"])
                self.assertFalse(original(BAIDU_AI_SNAPSHOT_JS)["folded"])
            finally:
                collector.close()

    def test_baidu_waits_for_late_citations_after_stable_body(self):
        fixture = Path(__file__).parent / "fixtures" / "baidu_ai.html"
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"WENXIN_STEALTH_HEADLESS": "1"}),
        ):
            page = ScraplingStealthPage(Path(temp) / "profile")
            collector = WenxinWebCollector(page=page)
            try:
                page.page.set_content(fixture.read_text(encoding="utf8"))
                page.evaluate(
                    "document.querySelectorAll('.cosd-citation').forEach(e=>e.remove());"
                    "setTimeout(()=>{const box=document.querySelector('.ai-entry');"
                    "box.insertAdjacentHTML('beforeend','<button class=\"cosd-citation\">1</button>"
                    '<button class="cosd-citation">2</button>\')},6000)'
                )
                evaluate = page.evaluate

                def fixture_evaluate(script, **kwargs):
                    if script == "location.href":
                        return "https://www.baidu.com/s?wd=fixture"
                    return evaluate(script, **kwargs)

                with patch.object(page, "evaluate", side_effect=fixture_evaluate):
                    result = collector.collect_search(
                        "测试问题",
                        timeout=25,
                        preloaded_navigation_id="fixture-document",
                    )
                self.assertEqual(result["capture_mode"], "baidu_search_ai")
                self.assertEqual(result["citation_count"], 2)
                self.assertTrue(result["source_capture_complete"])
                self.assertEqual(
                    result["sources"][0]["url"], "https://example.com/baidu"
                )
            finally:
                collector.close()

    def test_scrapling_real_baidu_and_wenxin_dom(self):
        fixture_root = Path(__file__).parent / "fixtures"
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"WENXIN_STEALTH_HEADLESS": "1"}),
        ):
            page = ScraplingStealthPage(Path(temp) / "profile")
            try:
                page.page.set_content(
                    (fixture_root / "baidu_ai.html").read_text(encoding="utf8")
                )
                snapshot = page.evaluate(BAIDU_AI_SNAPSHOT_JS)
                self.assertTrue(snapshot["ok"])
                self.assertIn("正文第一段", snapshot["body"])
                self.assertIn("正文第二段", snapshot["body"])
                self.assertEqual(snapshot["query"], "测试问题")
                self.assertEqual(snapshot["citationCount"], 2)
                sources = page.evaluate(BAIDU_VISIBLE_SOURCES_JS)["sources"]
                self.assertEqual(sources[0]["url"], "https://example.com/baidu")
                self.assertEqual(sources[0]["media"], "来源媒体")
                page.page.set_content(
                    (fixture_root / "wenxin_card.html").read_text(encoding="utf8")
                )
                snapshot = page.evaluate(WENXIN_SEARCH_SNAPSHOT_JS)
                self.assertTrue(snapshot["finished"])
                self.assertEqual(snapshot["expectedSourceCount"], 3)
                self.assertEqual(snapshot["extractedSourceItemCount"], 3)
                self.assertEqual(len(snapshot["sources"]), 2)
            finally:
                page.close()

    def test_real_dom_fragments_popup_sources_and_completion(self):
        fixture_root = Path(__file__).parent / "fixtures"
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(QuietHandler, directory=str(fixture_root))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            chrome_port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{server.server_port}/deepseek_answer.html"
        site = SiteConfig(
            "deepseek",
            "Local fixture",
            url,
            chrome_port,
            ("127.0.0.1",),
            ("textarea",),
            (".ds-markdown",),
        )
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"GEO_COLLECTOR_RUNTIME": temp}),
            patch("web_collectors.collector.site_config", return_value=site),
        ):
            collector = BrowserCollector("deepseek", headless=True)
            try:
                collector.navigate_home()
                snapshot = collector._snapshot()
                self.assertIn("回答第一部分", snapshot["body"])
                self.assertIn("回答第二部分", snapshot["body"])
                self.assertFalse(snapshot["busy"])
                self.assertEqual(collector.session_status()["status"], "ready")
                collector.page.evaluate(
                    "document.querySelector('textarea').disabled=true"
                )
                self.assertEqual(collector.session_status()["status"], "ready")
                collector.page.evaluate(
                    "const login=document.createElement('button');login.id='login-test';login.textContent='登录';document.body.appendChild(login)"
                )
                self.assertEqual(collector.session_status()["status"], "login_required")
                collector.page.evaluate(
                    "document.querySelector('#login-test').remove();document.querySelector('textarea').disabled=false"
                )
                self.assertEqual(
                    {item["url"] for item in snapshot["sources"]},
                    {"https://example.com/article-a", "https://example.com/article-b"},
                )
                settled = collector._wait_current_answer(
                    "本轮唯一问题 FIXTURE-REQUEST-42", timeout=30, stable_seconds=3
                )
                self.assertEqual(settled["body"], snapshot["body"])
                collector.page.evaluate(
                    "document.querySelector('#stop').style.display='block'"
                )
                self.assertTrue(collector._snapshot()["busy"])
                collector.page.evaluate(
                    "const p=document.createElement('p');p.innerHTML='普通数字2不改写，引用<span class=\"ds-markdown-cite\"><span style=\"opacity:0\">-</span><span>2</span></span>，重复引用<span class=\"ds-markdown-cite\">2</span>';document.querySelector('.ds-markdown').appendChild(p)"
                )
                clean = collector._snapshot()["body"]
                self.assertIn("普通数字2不改写，引用[2]，重复引用[2]", clean)
                self.assertEqual(clean.count("普通数字2不改写"), 1)
                self.assertNotIn("[[2]]", clean)
                collector.page.evaluate(
                    "const search=document.createElement('span');search.textContent='搜索到 2 个网页';search.onclick=()=>{window.fixtureSearchExpanded=true};document.body.appendChild(search)"
                )
                self.assertEqual(collector._expand_source_panel(), 2)
                self.assertTrue(collector.page.evaluate("window.fixtureSearchExpanded"))
                collector.page.evaluate(
                    "[...document.querySelectorAll('span')].find(e=>e.textContent==='搜索到 2 个网页').textContent='Found 2 web pages'"
                )
                self.assertEqual(collector._expand_source_panel(), 2)
                collector.page.evaluate(
                    "document.querySelectorAll('main,.ds-markdown').forEach(e=>e.remove())"
                )
                self.assertEqual(collector._snapshot()["body"], "")
            finally:
                collector.close()


if __name__ == "__main__":
    unittest.main()
