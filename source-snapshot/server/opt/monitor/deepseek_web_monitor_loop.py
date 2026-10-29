import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone


CDP_HOST = "http://127.0.0.1:9222"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_SCRIPT = os.path.join(BASE_DIR, "save_deepseek_refs.py")
DEFAULT_QUESTION = "帮我推荐一款防过敏的白发染发剂"


WAIT_READY_JS = r"""
(() => {
  const clean = (text) => String(text || "").replace(/\s+/g, " ").trim();
  const body = clean(document.body ? document.body.innerText || "" : "");
  const links = Array.from(document.querySelectorAll("a[href]")).filter((a) => {
    const href = a.href || "";
    return /^https?:\/\//.test(href) && !href.includes("chat.deepseek.com/a/chat/s/");
  });
  return {
    url: location.href,
    title: document.title,
    hasRead: /已阅读\s*\d+\s*个网页/.test(body),
    linkCount: new Set(links.map((a) => a.href)).size,
    hasTextarea: !!document.querySelector("textarea"),
    bodyTail: body.slice(-1200)
  };
})()
"""


COLLECT_REFS_JS = r"""
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clean = (text) => String(text || "").replace(/\s+/g, " ").trim();
  const seen = new Map();

  function addLinks() {
    for (const a of document.querySelectorAll("a[href]")) {
      const href = a.href || "";
      if (!/^https?:\/\//.test(href)) continue;
      if (href.includes("chat.deepseek.com/a/chat/s/")) continue;
      const text = clean(a.innerText || a.textContent || a.getAttribute("title") || a.getAttribute("aria-label"));
      if (!seen.has(href)) {
        seen.set(href, {
          title: text || "DeepSeek citation",
          href,
          source: "deepseek web answer a[href]"
        });
      }
    }
  }

  window.scrollTo(0, 0);
  await sleep(300);
  addLinks();
  for (let i = 0; i < 18; i += 1) {
    window.scrollBy(0, Math.max(450, Math.floor(window.innerHeight * 0.7)));
    await sleep(220);
    addLinks();
  }
  window.scrollTo(0, document.body.scrollHeight);
  await sleep(500);
  addLinks();

  const body = clean(document.body ? document.body.innerText || "" : "");
  const expectedMatch = body.match(/已阅读\s*(\d+)\s*个网页/);
  const title = document.title || "";
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
    url: location.href,
    title,
    chatTitle: title.replace(/\s*-\s*DeepSeek\s*$/, "").trim(),
    extractedAt: new Date().toISOString(),
    items
  };
})()
"""


LOCATE_INPUT_JS = r"""
(() => {
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
  };
  const rectObj = (el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 };
  };
  const textarea = Array.from(document.querySelectorAll("textarea"))
    .filter(visible)
    .sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top)[0];
  if (!textarea) return { ok: false, error: "cannot find textarea" };
  const tr = textarea.getBoundingClientRect();
  const buttons = Array.from(document.querySelectorAll("[role='button'], button"))
    .filter(visible)
    .map((el) => ({ el, cls: String(el.className || ""), rect: el.getBoundingClientRect() }))
    .filter((x) => x.rect.top > tr.top - 30 && x.rect.left > tr.left)
    .sort((a, b) => b.rect.left - a.rect.left);
  const send = buttons.find((x) => !/disabled/.test(x.cls)) || buttons[0];
  return { ok: true, textarea: rectObj(textarea), send: send ? rectObj(send.el) : null };
})()
"""


def log(message):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), str(message), flush=True)


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
        raise RuntimeError("没有找到 DeepSeek Web 页面。请在 open_chrome_debug.bat 打开的 Chrome 里打开 https://chat.deepseek.com/")
    candidates.sort(key=lambda page: 0 if "chat.deepseek.com" in (page.get("url") or "") else 1)
    return candidates[0]


def cdp_call(ws_url, method, params=None, timeout=90):
    try:
        import websocket
    except Exception as exc:
        raise RuntimeError("缺少 websocket-client，请运行：python -m pip install websocket-client") from exc

    ws = websocket.create_connection(ws_url, timeout=timeout)
    try:
        message_id = 1
        ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") != message_id:
                continue
            result = msg.get("result", {})
            if "exceptionDetails" in result:
                raise RuntimeError(json.dumps(result["exceptionDetails"], ensure_ascii=False))
            if "error" in msg:
                raise RuntimeError(json.dumps(msg["error"], ensure_ascii=False))
            return result
    finally:
        ws.close()


def current_ws_url():
    page = find_deepseek_page()
    ws_url = page.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("DeepSeek 页面缺少 webSocketDebuggerUrl，请确认 Chrome 是用 open_chrome_debug.bat 打开的")
    return ws_url


def evaluate_js(expression, timeout=90):
    return cdp_call(
        current_ws_url(),
        "Runtime.evaluate",
        {"expression": expression, "awaitPromise": True, "returnByValue": True},
        timeout=timeout,
    ).get("result", {}).get("value")


def navigate(url, timeout=30):
    return cdp_call(current_ws_url(), "Page.navigate", {"url": url}, timeout=timeout)


def cdp_click(ws_url, x, y):
    cdp_call(ws_url, "Input.dispatchMouseEvent", {
        "type": "mousePressed",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1,
    }, timeout=10)
    cdp_call(ws_url, "Input.dispatchMouseEvent", {
        "type": "mouseReleased",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1,
    }, timeout=10)


def locate_input_and_send(ws_url):
    result = cdp_call(ws_url, "Runtime.evaluate", {
        "expression": LOCATE_INPUT_JS,
        "awaitPromise": True,
        "returnByValue": True,
    }, timeout=20).get("result", {}).get("value")
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError("定位 DeepSeek 输入框失败：" + json.dumps(result, ensure_ascii=False))
    if not result.get("send"):
        raise RuntimeError("定位 DeepSeek 发送按钮失败：" + json.dumps(result, ensure_ascii=False))
    return result


def open_new_chat():
    navigate("https://chat.deepseek.com/", timeout=20)
    time.sleep(3)


def send_question(question):
    ws_url = current_ws_url()
    loc = locate_input_and_send(ws_url)
    textarea = loc["textarea"]
    cdp_click(ws_url, textarea["cx"], textarea["cy"])
    time.sleep(0.4)
    cdp_call(ws_url, "Input.insertText", {"text": question}, timeout=20)
    time.sleep(0.8)
    loc = locate_input_and_send(ws_url)
    send = loc["send"]
    cdp_click(ws_url, send["cx"], send["cy"])
    time.sleep(1.5)
    return {"ok": True, "method": "cdp_input", "url": find_deepseek_page().get("url")}


def wait_answer_ready(timeout=120, stable_seconds=8):
    start = time.time()
    stable_since = None
    last_count = -1
    last_snapshot = None
    while time.time() - start < timeout:
        time.sleep(2)
        snapshot = evaluate_js(WAIT_READY_JS, timeout=20)
        last_snapshot = snapshot
        count = int(snapshot.get("linkCount") or 0)
        log(f"waiting answer: read={snapshot.get('hasRead')} links={count} url={snapshot.get('url')}")
        if snapshot.get("hasRead") and count > 0:
            if count == last_count:
                stable_since = stable_since or time.time()
                if time.time() - stable_since >= stable_seconds:
                    return snapshot
            else:
                stable_since = None
                last_count = count
    raise RuntimeError("等待 DeepSeek Web 回答超时：" + json.dumps(last_snapshot, ensure_ascii=False))


def collect_refs(question):
    payload = evaluate_js(COLLECT_REFS_JS, timeout=90)
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise RuntimeError("DeepSeek Web 抓取失败：" + json.dumps(payload, ensure_ascii=False))
    if payload.get("count", 0) <= 0:
        raise RuntimeError("DeepSeek Web 没有抓到引用链接：" + json.dumps(payload, ensure_ascii=False))
    payload["question"] = question
    if not payload.get("extractedAt"):
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


def run_round(question, timeout, stable_seconds):
    open_new_chat()
    log("send question: " + question)
    send_question(question)
    wait_answer_ready(timeout=timeout, stable_seconds=stable_seconds)
    payload = collect_refs(question)
    save_result = save_payload(payload)
    log(json.dumps({
        "ok": True,
        "count": payload.get("count"),
        "expectedCount": payload.get("expectedCount"),
        "question": payload.get("question"),
        "save": save_result,
    }, ensure_ascii=False))
    return payload


def load_questions(args):
    if args.questions_file:
        with open(args.questions_file, "r", encoding="utf-8-sig") as f:
            questions = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    elif args.questions:
        questions = [item.strip() for item in args.questions.split("|||") if item.strip()]
    else:
        questions = [args.question.strip() or DEFAULT_QUESTION]
    if not questions:
        raise RuntimeError("问题列表为空")
    return questions


def run_loop(questions, rounds_per_question, timeout, stable_seconds):
    total = len(questions) * rounds_per_question
    done = 0
    for question_index, question in enumerate(questions, 1):
        log(f"question {question_index}/{len(questions)}: {question}")
        for round_index in range(1, rounds_per_question + 1):
            done += 1
            log(f"round {done}/{total} question_round {round_index}/{rounds_per_question}")
            run_round(question, timeout=timeout, stable_seconds=stable_seconds)
    open_new_chat()
    log("DeepSeek Web monitor loop done")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--questions", default="", help="多个问题用 ||| 分隔")
    parser.add_argument("--questions-file", default="", help="每行一个问题")
    parser.add_argument("--rounds", type=int, default=30, help="兼容旧参数：单问题总轮数")
    parser.add_argument("--rounds-per-question", type=int, default=0, help="每个问题跑多少轮，优先于 --rounds")
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--stable-seconds", type=int, default=8)
    args = parser.parse_args()

    try:
        questions = load_questions(args)
        rounds_per_question = args.rounds_per_question or args.rounds
        run_loop(questions, rounds_per_question, args.timeout, args.stable_seconds)
        print(json.dumps({"ok": True}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        raise


if __name__ == "__main__":
    main()
