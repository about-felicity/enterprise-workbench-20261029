import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone


CDP_HOST = "http://127.0.0.1:9222"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_SCRIPT = os.path.join(BASE_DIR, "save_deepseek_refs.py")


OPEN_LATEST_JS = r"""
(() => {
  const clean = (text) => String(text || "").replace(/\s+/g, " ").trim();
  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
  };

  const links = Array.from(document.querySelectorAll("a[href]"))
    .filter((a) => isVisible(a) && /\/a\/chat\/s\//.test(a.href))
    .map((a) => ({
      text: clean(a.innerText || a.textContent),
      href: a.href,
      top: a.getBoundingClientRect().top,
      left: a.getBoundingClientRect().left
    }))
    .filter((x) => x.text)
    .sort((a, b) => a.top - b.top || a.left - b.left);

  if (!links.length) {
    if (/\/a\/chat\/s\//.test(location.href)) {
      return { ok: true, alreadyOpen: true, href: location.href, text: document.title.replace(/\s*-\s*DeepSeek\s*$/, "") };
    }
    return { ok: false, error: "cannot find DeepSeek latest history chat link", url: location.href, title: document.title };
  }

  return { ok: true, href: links[0].href, text: links[0].text, current: location.href };
})()
"""


PAGE_SNAPSHOT_JS = r"""
(() => {
  const clean = (text) => String(text || "").replace(/\s+/g, " ").trim();
  const body = clean(document.body ? document.body.innerText || "" : "");
  const expectedMatch = body.match(/已阅读\s*(\d+)\s*个网页/);
  const questionCandidates = Array.from(document.querySelectorAll("div, p, span"))
    .map((el) => clean(el.innerText || el.textContent))
    .filter((text) => text && text.length >= 4 && text.length <= 120 && !/^已阅读/.test(text));

  return {
    url: location.href,
    title: document.title,
    body: body.slice(0, 4000),
    expectedCount: expectedMatch ? Number(expectedMatch[1]) || 0 : 0,
    questionCandidates: questionCandidates.slice(0, 80)
  };
})()
"""


COLLECT_REFS_JS = r"""
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clean = (text) => String(text || "").replace(/\s+/g, " ").trim();
  const seen = new Map();

  function sourceTextFor(anchor) {
    const text = clean(anchor.innerText || anchor.textContent);
    if (text) return text;
    const title = clean(anchor.getAttribute("title") || anchor.getAttribute("aria-label"));
    if (title) return title;
    return "DeepSeek citation";
  }

  function addLinks() {
    for (const a of document.querySelectorAll("a[href]")) {
      const href = a.href || "";
      if (!/^https?:\/\//.test(href)) continue;
      if (href.includes("chat.deepseek.com/a/chat/s/")) continue;
      if (!seen.has(href)) {
        seen.set(href, {
          title: sourceTextFor(a),
          href,
          source: "deepseek answer a[href]"
        });
      }
    }
  }

  window.scrollTo(0, 0);
  await sleep(400);
  addLinks();

  for (let i = 0; i < 16; i += 1) {
    window.scrollBy(0, Math.max(450, Math.floor(window.innerHeight * 0.7)));
    await sleep(250);
    addLinks();
  }

  window.scrollTo(0, document.body.scrollHeight);
  await sleep(500);
  addLinks();

  const body = clean(document.body ? document.body.innerText || "" : "");
  const expectedMatch = body.match(/已阅读\s*(\d+)\s*个网页/);
  const items = Array.from(seen.values()).map((item, index) => ({
    index: index + 1,
    title: item.title,
    href: item.href,
    source: item.source
  }));

  return {
    ok: true,
    status: "done",
    complete: items.length > 0,
    count: items.length,
    expectedCount: expectedMatch ? Number(expectedMatch[1]) || items.length : items.length,
    items,
    body: body.slice(0, 5000)
  };
})()
"""


def request_json(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def find_deepseek_page():
    pages = request_json(f"{CDP_HOST}/json")
    candidates = []
    for page in pages:
        if page.get("type") != "page":
            continue
        title = page.get("title") or ""
        url = page.get("url") or ""
        if "chat.deepseek.com" in url or "DeepSeek" in title:
            candidates.append(page)
    if not candidates:
        raise RuntimeError("没有找到 DeepSeek Web 页面。请用 open_chrome_debug.bat 打开的 Chrome 打开 https://chat.deepseek.com/")
    candidates.sort(key=lambda p: 0 if "/a/chat/s/" in (p.get("url") or "") else 1)
    return candidates[0]


def cdp_call(ws_url, method, params=None, timeout=90):
    try:
        import websocket
    except Exception as exc:
        raise RuntimeError("缺少 websocket-client，请运行：python -m pip install websocket-client") from exc

    ws = websocket.create_connection(ws_url, timeout=timeout)
    try:
        message_id = 1
        ws.send(json.dumps({
            "id": message_id,
            "method": method,
            "params": params or {},
        }))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") != message_id:
                continue
            result = msg.get("result", {})
            if "exceptionDetails" in result:
                details = result.get("exceptionDetails") or {}
                raise RuntimeError(json.dumps(details, ensure_ascii=False))
            if "error" in msg:
                raise RuntimeError(json.dumps(msg["error"], ensure_ascii=False))
            return result
    finally:
        ws.close()


def evaluate_js(ws_url, expression, timeout=90):
    return cdp_call(ws_url, "Runtime.evaluate", {
        "expression": expression,
        "awaitPromise": True,
        "returnByValue": True,
    }, timeout=timeout).get("result", {}).get("value")


def navigate_and_wait(ws_url, href):
    cdp_call(ws_url, "Page.navigate", {"url": href}, timeout=20)
    last = None
    for _ in range(40):
        time.sleep(1)
        page = find_deepseek_page()
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            continue
        try:
            snapshot = evaluate_js(ws_url, PAGE_SNAPSHOT_JS, timeout=10)
        except Exception:
            continue
        last = snapshot
        if isinstance(snapshot, dict) and snapshot.get("url", "").rstrip("/") == href.rstrip("/") and "已阅读" in (snapshot.get("body") or ""):
            return ws_url, snapshot
    raise RuntimeError("导航到 DeepSeek 最新会话后没有等到回答加载：" + json.dumps(last, ensure_ascii=False))


def infer_question(snapshot, fallback_title):
    body = snapshot.get("body") or ""
    title = (fallback_title or "").replace(" - DeepSeek", "").strip()
    match = re.search(r"快速模式\s+(.{4,120}?)\s+已阅读\s*\d+\s*个网页", body)
    if match:
        return match.group(1).strip()
    lines = [line.strip() for line in re.split(r"\s{2,}|\n", body) if line.strip()]
    for line in lines:
        if 5 <= len(line) <= 80 and not line.startswith(("开启新对话", "今天", "已阅读")):
            if line != title:
                return line
    return title


def run_grab():
    page = find_deepseek_page()
    ws_url = page.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("DeepSeek 页面缺少 webSocketDebuggerUrl，请确认 Chrome 是用 open_chrome_debug.bat 打开的")

    latest = evaluate_js(ws_url, OPEN_LATEST_JS, timeout=20)
    if not isinstance(latest, dict) or not latest.get("ok"):
        raise RuntimeError("打开 DeepSeek 最新会话失败：" + json.dumps(latest, ensure_ascii=False))

    if latest.get("alreadyOpen"):
        snapshot = evaluate_js(ws_url, PAGE_SNAPSHOT_JS, timeout=20)
    else:
        ws_url, snapshot = navigate_and_wait(ws_url, latest["href"])

    payload = evaluate_js(ws_url, COLLECT_REFS_JS, timeout=90)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise RuntimeError("DeepSeek 抓取失败：" + json.dumps(payload, ensure_ascii=False))
    if payload.get("count", 0) <= 0:
        raise RuntimeError("DeepSeek 没有抓到引用链接：" + json.dumps(payload, ensure_ascii=False))

    payload["url"] = snapshot.get("url") or latest.get("href") or page.get("url")
    payload["title"] = snapshot.get("title") or page.get("title")
    payload["chatTitle"] = latest.get("text") or (snapshot.get("title") or "").replace(" - DeepSeek", "")
    payload["question"] = infer_question(snapshot, payload["chatTitle"])
    payload["extractedAt"] = datetime.now(timezone.utc).isoformat()
    return payload


def save_payload(payload):
    raw = json.dumps(payload, ensure_ascii=False)
    out = subprocess.check_output(
        [sys.executable, SAVE_SCRIPT, raw],
        cwd=BASE_DIR,
        encoding="utf-8",
        errors="ignore",
    )
    return out.strip()


def main():
    try:
        payload = run_grab()
        save_result = save_payload(payload)
        print(json.dumps({
            "ok": True,
            "count": payload.get("count"),
            "expectedCount": payload.get("expectedCount"),
            "complete": payload.get("complete"),
            "chatTitle": payload.get("chatTitle"),
            "question": payload.get("question"),
            "save": save_result,
        }, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error": str(exc),
        }, ensure_ascii=False))
        raise


if __name__ == "__main__":
    main()
