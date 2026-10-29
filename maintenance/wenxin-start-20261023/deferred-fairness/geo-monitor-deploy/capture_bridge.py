"""Independent browser capture journals -> existing GEO PostgreSQL receiver.

Only confirmed completed captures enter the durable outbox. Network retries
reuse exactly the same envelope. Collector crashes never reset task states.
"""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlsplit

import requests
from geo_source_cards.runtime import atomic_json, process_lock
from runtime_reliability import DeliveryGate

MODEL = {"deepseek": "deepseek", "deepseek2": "deepseek", "wenxin_card": "wenxin", "baidu_ai": "wenxin"}
STOP = False


def stop_signal(*_):
    global STOP
    STOP = True


def load(path, default=None):
    try:
        return json.loads(Path(path).read_text("utf-8-sig"))
    except FileNotFoundError:
        return {} if default is None else default


def full_result(result):
    if result.get("availability") in {"no_card", "supplement_unavailable", "body_only"}:
        return False
    if not str(result.get("body") or "").strip():
        raise ValueError("empty_answer")
    if result.get("body_capture_complete") is not True or result.get("source_capture_complete") is not True:
        raise ValueError("unproven_completeness")
    sources = result.get("sources")
    if not sources:
        raise ValueError("missing_sources")
    for source in sources:
        parsed = urlsplit(source.get("url", ""))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not source.get("title", "").strip():
            raise ValueError("incomplete_source_metadata")
    return True


def duplicate_key(result):
    # Classify duplicates within a Beijing day. Every capture still receives
    # its own envelope/receipt; analytics deduplicates the daily sample later.
    captured = datetime.fromisoformat(result['captured_at'].replace('Z', '+00:00'))
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    day = captured.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    value = [day, result["question"], result["body"], result["sources"], result.get("source_entries", []),
             result.get("citations", []), result.get("expected_source_count")]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def envelope(row, result, config):
    if not full_result(result):
        raise ValueError("absence_is_not_a_full_answer")
    model, device = MODEL[config["model"]], config["device"]
    record = {
        "collector_model": model, "question": result["question"], "prompt": result["question"],
        "web_body": result["body"], "sources": result["sources"],
        "expected_source_count": len(result["sources"]), "source_capture_complete": True,
        "body_capture_complete": True, "source_list_present": True, "status": "success",
        "task_id": row["ordinal"] * config["rounds"] + row["round"],
        "capture_task_id": row["task_id"], "batch_id": row["batch"], "round": row["round"],
        "serial": device, "started_at": result["captured_at"], "finished_at": result["captured_at"],
        "capture_mode": result["capture_mode"], "url": result.get("url", ""),
        "capture_label": config.get('capture_label') or {"deepseek": "DeepSeek 网页", "deepseek2": "DeepSeek 2 安卓App", "wenxin_card": "文心卡片", "baidu_ai": "百度卡片"}[config["model"]],
        "citations": result.get("citations", []), "source_entries": result.get("source_entries", []),
        "capture_result": result,
    }
    if config.get('daily_target_rounds') and config['model']=='baidu_ai':
        record['daily_surface_target']=config['daily_target_rounds']
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    rid = hashlib.sha256(f"{model}\n{device}\n{raw}".encode()).hexdigest()
    return {"version": 1, "model": model, "source_device": device,
            "request_id": rid, "sent_at": row["finished"], "record": record}


def verify_receipt(receipt, item):
    analysis, record = receipt.get("analysis", {}), item["record"]
    expected = [{"title": s["title"].strip(), "href": s["url"].strip()} for s in record["sources"]]
    if (receipt.get("request_id") != item["request_id"] or receipt.get("model") != item["model"]
        or receipt.get("source_device") != item["source_device"] or not receipt.get("stored_run_id")
        or analysis.get("quarantined") or not analysis.get("answer_present")
        or analysis.get("answer_length") != len(record["web_body"].strip())
        or analysis.get("body_capture_complete") is not True
        or analysis.get("source_capture_complete") is not True
        or analysis.get("source_count") != len(expected) or analysis.get("sources") != expected):
        raise ValueError("receipt_mismatch_or_quarantine")


class Delivery:
    def __init__(self, root, config, receiver_root):
        self.root, self.config, self.receiver_root = root, config, receiver_root
        for folder in ("outbox", "receipts", "observations"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        receiver = load(receiver_root / "runtime/lan_result_receiver.json")
        self.url = "http://127.0.0.1:" + str(receiver["port"])
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["Authorization"] = "Bearer " + receiver["token"]
        self.last_post = {}
        self.gate = DeliveryGate(root, atomic_json)
        self.body_delivery = None
        if config['model'] == 'baidu_ai':
            from baidu_body_delivery import Delivery as BaiduBodyDelivery
            self.body_delivery = BaiduBodyDelivery(root, config, receiver_root)

    def sync(self, rows):
        result = {"captured": 0, "unique": 0, "processed": 0, "duplicates": 0, "unavailable": 0, "body_only_observations":0, "errors": []}
        unique, posted = {}, 0
        for row in rows:
            if row["state"] != "completed":
                continue
            value = json.loads(row["result"])
            try:
                if not full_result(value):
                    result["unavailable"] += 1
                    if value.get('availability')=='body_only':
                        result['body_only_observations']+=1
                    atomic_json(self.root / "observations" / (row["task_id"] + ".json"),
                                {"capture_task_id": row["task_id"], "status": value.get("availability"), "geo_processed": False,
                                 **({'body':value['body'],'body_capture_complete':True,'source_capture_complete':False,
                                     'source_exposure':value.get('source_exposure'),'capture_result':value} if value.get('availability')=='body_only' else {})})
                    continue
                result["captured"] += 1
                key = duplicate_key(value)
                duplicate = self.config["model"] == "baidu_ai" and key in unique
                item = envelope(row, value, self.config)
                if duplicate:
                    result["duplicates"] += 1
                else:
                    unique[key] = item
                    result["unique"] += 1
                rid = item["request_id"]
                outbox, receipt_path = self.root / "outbox" / (rid + ".json"), self.root / "receipts" / (rid + ".json")
                if not outbox.exists():
                    atomic_json(outbox, item)
                elif load(outbox) != item:
                    raise ValueError("outbox_identity_changed")
                if not receipt_path.exists() and self.gate.due(rid):
                    reply = self.session.get('http://127.0.0.1:8803/api/receipts/' + item['model'] + '/' + rid, timeout=5)
                    reply.raise_for_status()
                    state = reply.json()
                    if state.get('status') == 'processed':
                        receipt = state['receipt']
                        verify_receipt(receipt, item)
                        atomic_json(receipt_path, receipt)
                        self.gate.complete(rid)
                    elif posted < 4 and self.gate.may_post(rid):
                        response = self.session.post(self.url + "/api/v1/models/" + item["model"] + "/results", json=item, timeout=8)
                        response.raise_for_status()
                        ack = response.json()
                        if ack.get("request_id") != rid or not ack.get("ok"):
                            raise ValueError("invalid_receiver_ack")
                        self.last_post[rid], posted = time.time(), posted + 1
                        self.gate.waiting(rid, posted=True)
                    else:
                        self.gate.waiting(rid)
                elif not receipt_path.exists():
                    diagnostic=self.gate.diagnostic(rid)
                    if diagnostic.get('code')!='awaiting_processed':
                        result['errors'].append({'task_id': row['task_id'], **diagnostic})
                processed = receipt_path.exists()
                if processed:
                    verify_receipt(load(receipt_path), item)
                    self.gate.complete(rid)
                    result["processed"] += 1
                atomic_json(self.root / "observations" / (row["task_id"] + ".json"),
                            {"capture_task_id": row["task_id"], "request_id": rid,
                             "status": "duplicate" if duplicate else "unique", "geo_processed": processed})
            except (OSError, TypeError, ValueError, KeyError, requests.RequestException) as error:
                result["errors"].append({"task_id": row["task_id"], "kind": type(error).__name__,
                    **(self.gate.failed(rid,error) if isinstance(error,requests.RequestException) else {'code':'result_or_receipt_invalid','retryable':False})})
        result["unique_processed"] = result["processed"] - sum(
            1 for p in (self.root / "observations").glob("*.json")
            if (lambda v: v.get("status") == "duplicate" and v.get("geo_processed"))(load(p)))
        if self.body_delivery:
            result['body_only_delivery'] = self.body_delivery.sync(rows)
        return result


def read_rows(path, batch):
    if not path.exists():
        return []
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute("select * from captures where batch=? order by ordinal,round", (batch,))]


def run(config_path, base, receiver_root):
    config = load(config_path)
    if config['model']=='deepseek' and (base/'deepseek_backend.json').exists():
        # Preserve the web journal exactly; Android owns all new DeepSeek sends.
        print(json.dumps({'event':'legacy_deepseek_web_disabled','backend':'android'}),flush=True)
        return 0
    root = base / "batches" / config["batch"]
    root.mkdir(parents=True, exist_ok=True)
    runtime, child, last_exit = root / "collector", None, None
    delivery = Delivery(root, config, receiver_root)
    expected = len(config["questions"]) * config["rounds"]
    atomic_json(root / "manifest.json", config)
    (root / "questions.txt").write_text("\n".join(config["questions"]) + "\n", encoding="utf8")
    env = {**os.environ, "GEO_DEEPSEEK_PORT": "9514", "PYTHONUNBUFFERED": "1",'GEO_UNATTENDED':'1'}
    env.pop("GEO_PIPELINE_ROOT", None)
    env["GEO_SEARCH_RATE_STATE"] = str(base / "search_last_start.json")
    if config['model']=='deepseek':
        env['GEO_DEEPSEEK_RATE_STATE']=str(base/'deepseek_last_send.json')
        env['GEO_DEEPSEEK_SEED_ROOT']=str(base/'batches')
    env['GEO_CAPTURE_PAUSE_FILE']=str(root/'pause.json')
    env['GEO_CAPTURE_PROGRESS_FILE']=str(root/'collector_progress.json')
    command = [sys.executable, "-u", "-m", "geo_source_cards.cli", "--model", config["model"],
               "--runtime-dir", str(runtime), "--batch", config["batch"], "--questions-file", str(root / "questions.txt"),
               "--rounds", str(config["rounds"]), "--output", str(root / "results.jsonl"), "--require-sources",
               "--require-complete-sources", "--min-deepseek-interval", str(config.get('interval',600) if config['model']=='deepseek' else 600),
               "--min-search-interval", str(config.get('interval',60) if config['model']!='deepseek' else 60),
               "--max-new-captures", "1"]
    if config["model"] != "deepseek":
        command.extend(["--bounded-search-recovery","--max-search-attempts","2"])
        command = ["/usr/bin/flock", "-x", str(base / "search_browser.lock")] + command
    else:
        command = ['/usr/bin/flock','-x',str(base/'deepseek_account.lock')] + command
    if config["model"] == "baidu_ai":
        command.append("--optional-baidu")
    log = (root / "capture.log").open("a", encoding="utf8")
    health, code = {}, 1
    retry=load(root/'capture_retry.json',{'attempt':0,'next_at':0})
    with process_lock(root / "bridge.lock"):
        try:
            while not STOP:
                # Observe process exit first: CLI may finalize an exhausted
                # optional card while the previously sampled row still says
                # failed_deferred. Decisions must use the post-exit journal.
                exited = child is not None and child.poll() is not None
                if exited:
                    last_exit, child = child.returncode, None
                    if last_exit:
                        attempt=retry.get('attempt',0)+1
                        retry={'attempt':attempt,'next_at':time.time()+min(300,5*2**min(6,attempt-1)),'last_exit':last_exit}
                    else:retry={'attempt':0,'next_at':0}
                    atomic_json(root/'capture_retry.json',retry)
                rows = read_rows(runtime / "tasks.sqlite", config["batch"])
                counts = {}
                for row in rows:
                    counts[row["state"]] = counts.get(row["state"], 0) + 1
                summary = delivery.sync(rows)
                blocked = any(e['kind'] in {'ValueError','KeyError','TypeError'} for e in summary['errors'])
                auth_stop=(last_exit==77 or load(runtime/'search_recovery.json').get('blocked'))
                if auth_stop and child is None:
                    waiting='waiting_login' if config['model']=='deepseek' else 'waiting_verification'
                    health={**summary,'time':time.time(),'status':waiting,'model':config['model'],'batch':config['batch'],
                            'planned':expected,'tasks':counts,'progress':{'phase':waiting,'pending_delivery':0}}
                    code=77
                    return code
                completed = len(rows) == expected and counts.get("completed", 0) == expected
                delivered = summary["processed"] + summary["unavailable"] == expected
                body_delivery = summary.get('body_only_delivery', {})
                terminal = completed and delivered and not summary["errors"] and not body_delivery.get('pending_delivery') and not body_delivery.get('errors')
                backlog = summary['captured'] > summary['processed'] or bool(body_delivery.get('pending_delivery'))
                if any(e.get('retryable') is False for e in body_delivery.get('errors', [])):
                    blocked = True
                recovering=blocked or (child is None and (retry.get('attempt') or counts.get('needs_attention') or counts.get('failed_deferred')))
                status = "complete_with_unavailable" if terminal and summary["unavailable"] else "complete" if terminal else "running_delivery_backoff" if backlog else 'running_recovery' if recovering else "running"
                if any(e.get('retryable') is False for e in summary['errors']):status='running_delivery_backoff'
                # Keep a receiver outage from accumulating more model answers.
                drain_readback=bool(load(root/'pause.json').get('allow_original_readback') and counts.get('needs_attention'))
                if not terminal and not blocked and not backlog and child is None and not completed and time.time()>=retry.get('next_at',0) and (not (root / "pause.json").exists() or drain_readback):
                    child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                if (root / "pause.json").exists() and child is None and not blocked and summary["processed"] + summary["unavailable"] == counts.get("completed", 0):
                    status = "paused"
                health = {"time": time.time(), "heartbeat_expires_at": time.time() + 45, "bridge_pid": os.getpid(),
                          "model": config["model"], "batch": config["batch"], "planned": expected, "tasks": counts,
                          "status": status, "worker_exit": last_exit, "worker_pid": child.pid if child else None, **summary}
                health['progress'] = {'phase': 'delivery' if backlog else 'collecting' if child else status,
                                      'pending_delivery': max(0, summary['captured']-summary['processed']) + body_delivery.get('pending_delivery', 0)}
                if child and not backlog:
                    health['progress'].update(load(root/'collector_progress.json'))
                elif recovering and not backlog:
                    health['progress'].update(phase='automatic_backoff',attempt=retry.get('attempt',0),next_at=retry.get('next_at',0))
                atomic_json(root / "bridge_health.json", health)
                if terminal or status == "paused":
                    code = 0
                    return code
                time.sleep(3)
            code = 0
            return code
        finally:
            if child and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            health.update(time=time.time(), heartbeat_expires_at=None, bridge_pid=None, worker_pid=None)
            if health.get("status") not in {"complete", "complete_with_unavailable", "needs_attention", "paused",'waiting_login','waiting_verification'}:
                health["status"] = "stopped"
            atomic_json(root / "bridge_health.json", health)
            log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=Path("/opt/monitor/geo-capture"))
    parser.add_argument("--receiver-root", type=Path, default=Path("/opt/monitor"))
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    raise SystemExit(run(args.config, args.base, args.receiver_root))
