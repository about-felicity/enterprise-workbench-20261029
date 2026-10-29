"""Operate the logged-in Android app over ADB, without a display window."""
import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("ADBUTILS_ADB_PATH", str(ROOT / "artifacts/platform-tools/adb.exe"))
import uiautomator2 as u2

parser = argparse.ArgumentParser()
parser.add_argument("--serial", default="127.0.0.1:15555")
parser.add_argument("--questions", type=Path, default=ROOT / "test_questions.json")
parser.add_argument("--output", type=Path, default=ROOT / "artifacts/test-20261006")
parser.add_argument("--capture-current-first", action="store_true")
parser.add_argument("--timeout", type=int, default=180)
parser.add_argument("--source-mode", choices=['store','ui'], default='store')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
d = u2.connect(args.serial)
PREFIX = "com.larus.nova:id/"

def nodes():
    return list(ET.fromstring(d.dump_hierarchy()).iter("node"))

def find(ns, rid=None, text=None, desc=None):
    return next((n for n in ns if (rid is None or n.get("resource-id") == PREFIX + rid)
                 and (text is None or n.get("text") == text)
                 and (desc is None or n.get("content-desc") == desc)), None)

def wait_control(rid=None, text=None, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        n = find(nodes(), rid=rid, text=text)
        if n is not None:
            return n
        time.sleep(.7)
    raise RuntimeError(f"Android control did not appear: {rid or text}")

def bounds(n):
    return list(map(int, re.findall(r"\d+", n.get("bounds", ""))))

def tap(n):
    if n is None:
        raise RuntimeError("Required Android control is absent")
    x1, y1, x2, y2 = bounds(n)
    d.shell(["input", "tap", str((x1+x2)//2), str((y1+y2)//2)])
    time.sleep(.6)

def swipe(x1, y1, x2, y2, duration=450):
    d.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
    time.sleep(.6)

def back():
    d.shell(["input", "keyevent", "4"])
    time.sleep(.6)

def evidence(name):
    (args.output / (name + ".xml")).write_text(d.dump_hierarchy(), encoding="utf-8")
    d.screenshot().save(args.output / (name + ".png"))

def answer_nodes(ns):
    return [n for n in ns if n.get("class") == "android.widget.TextView"
            and not n.get("resource-id") and len(n.get("content-desc", "")) > 60]

def wait_answer():
    deadline = time.monotonic() + args.timeout
    previous = ""
    stable_since = time.monotonic()
    while time.monotonic() < deadline:
        ns = nodes()
        if find(ns, rid="phone_number") or find(ns, rid="tourist_text"):
            raise RuntimeError("Login required")
        candidates = answer_nodes(ns)
        current = candidates[-1].get("text", "") if candidates else ""
        generating = any((len(n.get("content-desc", "")) < 30 and "停止" in n.get("content-desc", ""))
                         or n.get("text", "").startswith("正在搜索") for n in ns)
        if current != previous:
            stable_since = time.monotonic()
            previous = current
        if current and not generating and time.monotonic() - stable_since > 12:
            return ns, candidates[-1]
        time.sleep(3)
    raise TimeoutError("Answer did not stabilize; no automatic resend")

def copy_body(n):
    x1, y1, x2, y2 = bounds(n)
    y = max(200, min(850, (max(180,y1)+min(920,y2))//2))
    marker = "doubao-body-pending-" + str(time.time_ns())
    d.set_clipboard(marker)
    swipe((x1+x2)//2, y, (x1+x2)//2, y, 900)
    tap(find(nodes(), text="复制"))
    body = d.clipboard
    if not body or body == marker:
        raise RuntimeError("Full-answer clipboard copy failed")
    return body

def normalize_url(raw):
    parts = urlsplit(raw)
    if parts.hostname == "seclink.bytedance.com":
        target = dict(parse_qsl(parts.query)).get("target")
        if target and re.match(r"https?://", target):
            return normalize_url(target)
    internal = {"use_xbridge3", "loader_name", "need_sec_link", "sec_link_scene", "theme"}
    query = urlencode([(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True) if k not in internal])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

def sources(ns, name):
    ref = find(ns, rid="tv_reference_title")
    if ref is None:
        # The reference header can be above the visible answer.
        swipe(350, 350, 350, 850)
        ref = find(nodes(), rid="tv_reference_title")
    if ref is None:
        return [], 0, "no_reference_panel"
    total_match = re.search(r"参考\s*(\d+)\s*篇", ref.get("text", ""))
    expected = int(total_match.group(1)) if total_match else None
    tap(ref)
    evidence(name + "-reference-panel")
    swipe(350, 760, 350, 230)
    checkpoint = args.output / (name + "-sources.json")
    found = {s["index"]:s for s in json.loads(checkpoint.read_text(encoding="utf-8"))} if checkpoint.exists() else {}
    stalled = 0
    for page in range(24):
        ns = nodes()
        indexes = [n for n in ns if n.get("resource-id") == PREFIX + "tv_reference_index"]
        titles = [n for n in ns if n.get("resource-id") == PREFIX + "tv_reference_content"]
        pending = []
        for idx, title in zip(indexes, titles):
            m = re.search(r"\d+", idx.get("text", ""))
            if not m:
                continue
            number = int(m.group())
            b = bounds(title)
            if number not in found and b[3]-b[1] >= 25 and b[3] < 1184:
                pending.append((number, title.get("text", "")))
        before = len(found)
        for number, title in pending:
            # Re-read after returning from each WebActivity.
            ns = nodes()
            title_node = find(ns, rid="tv_reference_content", text=title)
            tap(title_node)
            deadline = time.monotonic() + 15
            share = None
            while time.monotonic() < deadline:
                share = find(nodes(), rid="btn_share")
                if share is not None:
                    break
                time.sleep(1)
            tap(share)
            copy_link = None
            for retry in range(8):
                copy_link = find(nodes(), text="复制链接")
                if copy_link is not None:
                    break
                time.sleep(1)
                retry_share = find(nodes(), rid="btn_share")
                if retry_share is not None:
                    tap(retry_share)
            marker = "doubao-source-pending-" + str(time.time_ns())
            d.set_clipboard(marker)
            if copy_link is not None:
                tap(copy_link)
                raw = d.clipboard
                if not raw or not re.match(r"https?://", raw):
                    raise RuntimeError("Reference URL copy failed: " + str(number))
                found[number] = {"index": number, "title": title, "url": normalize_url(raw), "raw_url": raw,
                                 "extraction": "Android App reference -> share -> copy link"}
            else:
                found[number] = {"index": number, "title": title, "url": None, "raw_url": None,
                                 "error": "App source page reports sharing failed; URL unavailable through UI"}
            checkpoint.write_text(json.dumps(list(found.values()), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  Reference {number}: {found[number]['url'] or 'App sharing failed'}", flush=True)
            close = find(nodes(), rid="btn_back")
            if close is not None:
                tap(close)
            else:
                back()
            time.sleep(1)
            if find(nodes(), text="参考资料") is None:
                tap(find(nodes(), rid="tv_reference_title"))
                swipe(350, 760, 350, 230)
                # The app may dismiss the sheet when opening a source.
                # Restore its position without assuming the previous bounds.
                for _ in range(12):
                    visible_indexes = [int(re.search(r"\d+", n.get("text", "0")).group())
                                       for n in nodes() if n.get("resource-id") == PREFIX + "tv_reference_index"]
                    if visible_indexes and max(visible_indexes) >= number:
                        break
                    swipe(350,1110,350,550)
        if expected is not None and len(found) >= expected:
            break
        stalled = stalled + 1 if len(found) == before else 0
        if stalled >= 3:
            break
        swipe(350, 1110, 350, 550)
    back()
    return [found[k] for k in sorted(found)], expected, "complete" if len(found) == expected and all(s.get('url') for s in found.values()) else "partial"

def submit(question):
    ns = nodes()
    if find(ns, rid="larus_chat_top_left_create_new_cvs") is None:
        # Some completed answers remain stuck in the app's renderer while the
        # full data has already been committed. Preserve data/login and reopen.
        d.shell(['am','force-stop','com.larus.nova'])
        d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
        wait_control(rid='larus_chat_top_left_create_new_cvs', timeout=30)
        ns = nodes()
    tts = find(ns, desc='朗读已打开')
    if tts is not None:
        tap(tts)
        ns = nodes()
    tap(find(ns, rid="larus_chat_top_left_create_new_cvs"))
    ns = nodes()
    if find(ns, rid="input_text") is None:
        tap(find(ns, rid="action_input"))
    d(resourceId=PREFIX + "input_text").set_text(question)
    tap(find(nodes(), rid="action_send"))
    # Sending hides the keyboard automatically; do not issue an extra Back.

def read_store(question):
    from remote import connect
    client, password = connect()
    try:
        stdin, stdout, stderr = client.exec_command("sudo -S -p '' python3 /home/user/redroid-doubao/export_chat_store.py --questions /home/user/redroid-doubao/loop-questions.json --stdout", timeout=40)
        stdin.write(password + '\n')
        stdin.flush()
        stdin.channel.shutdown_write()
        data = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if stdout.channel.recv_exit_status():
            raise RuntimeError('Store extraction failed: ' + error)
        return next(r for r in json.loads(data) if r['question'] == question)
    finally:
        client.close()

questions = json.loads(args.questions.read_text(encoding="utf-8-sig"))
if not isinstance(questions, list) or not all(isinstance(q,str) and q.strip() for q in questions):
    raise ValueError("Questions must be a JSON list of non-empty strings")
if args.source_mode == 'store':
    from remote import connect
    client, _ = connect()
    try:
        with client.open_sftp() as sftp:
            sftp.put(str(args.questions), '/home/user/redroid-doubao/loop-questions.json')
    finally:
        client.close()
rows = []
for index, question in enumerate(questions, 1):
    print(f"Question {index}/{len(questions)}: {question}", flush=True)
    row = {"index": index, "question": question, "time": datetime.now().astimezone().isoformat(),
           "transport": "ADB", "app": "com.larus.nova", "headless": True}
    try:
        previous_request = read_store(question).get('request_time') if args.source_mode == 'store' else None
        if not (args.capture_current_first and index == 1):
            submit(question)
        if args.source_mode == 'store':
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                store = read_store(question)
                is_new = (args.capture_current_first and index == 1) or store.get('request_time') != previous_request
                if store.get('status') == 'ok' and store.get('finished') and is_new:
                    break
                time.sleep(3)
            else:
                raise TimeoutError('Database answer is absent, unfinished, or belongs to an earlier request')
            evidence(f"q{index}-answer")
            row['body'] = store['body_text']
            row['body_markdown'] = store['body_markdown']
            row['citations'] = store['citations']
            row['search_queries'] = store['search_queries']
            row['extraction'] = store['extraction']
            refs, expected, source_status = store['sources'], store['source_count'], 'complete'
        else:
            ns, answer = wait_answer()
            evidence(f"q{index}-answer")
            row["body_ui"] = answer.get("content-desc", "")
            row["body_with_citation_labels"] = answer.get("text", "")
            row["body"] = copy_body(answer)
            refs, expected, source_status = sources(nodes(), f"q{index}")
        row.update(sources=refs, expected_sources=expected, source_status=source_status, status="ok")
        row["body_urls"] = re.findall(r"https?://[^\s<>\[\]，。]+", row["body"])
        print(f"  Extracted {len(row['body'])} characters and {len(refs)}/{expected} references", flush=True)
    except Exception as exc:
        row.update(status="error", error=str(exc))
        try:
            evidence(f"q{index}-error")
        except Exception:
            pass
        print("  ERROR: " + str(exc), flush=True)
        traceback.print_exc()
    rows.append(row)
    with (args.output / "results.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output / f"q{index}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    if row["status"] == "error":
        break
    time.sleep(3)
with (args.output / "results.csv").open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=["index", "question", "body", "source_count", "source_urls", "status"])
    writer.writeheader()
    for row in rows:
        writer.writerow({"index":row["index"], "question":row["question"], "body":row.get("body", ""),
                         "source_count":len(row.get("sources", [])),
                         "source_urls":"\n".join(s["url"] for s in row.get("sources", []) if s.get('url')), "status":row["status"]})
print("Saved results:", args.output, flush=True)
raise SystemExit(0 if len(rows) == len(questions) and all(r["status"] == "ok" for r in rows) else 1)
