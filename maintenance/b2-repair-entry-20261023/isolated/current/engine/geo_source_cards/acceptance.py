"""Continuous six-hour observation, gated by real capture and local delivery."""

import argparse
import json
import time
from pathlib import Path

from .daily_editorial import file_hash
from .desktop_status import snapshot
from .runtime import atomic_json, process_lock
from .staged_editorial import read


def prerequisites(root, date, now, state):
    root = Path(root)
    reasons = []
    if (state.get("control") or {}).get("paused"):
        reasons.append("任务处于人工恢复门控暂停状态")
    quality = (
        read(root / "quality_gate.json")
        if (root / "quality_gate.json").exists()
        else {}
    )
    if quality.get("status") != "reviewed" or not quality.get("sample_word_hashes"):
        reasons.append("文章内容与Word人工抽查尚未通过")
    capture = root / "captures" / date / "daily"
    expected = len(
        [
            line
            for line in (root / "questions.txt").read_text("utf8").splitlines()
            if line.strip()
        ]
    )
    for model in ("deepseek", "baidu_ai", "wenxin_card"):
        path = capture / (model + ".jsonl")
        rows = (
            [
                json.loads(line)
                for line in path.read_text("utf8").splitlines()
                if line.strip()
            ]
            if path.exists()
            else []
        )
        if (
            len(rows) != expected
            or len({row.get("task_id") for row in rows}) != expected
        ):
            reasons.append(f"{model} 当日采集未完整：{len(rows)}/{expected}")
        elif any(
            row.get("source_capture_complete") is not True
            or row.get("body_capture_complete") is not True
            for row in rows
            if not (
                model == "baidu_ai"
                and row.get("availability") == "supplement_unavailable"
            )
        ):
            reasons.append(model + " 存在未完成正文或信源")
        if model == "deepseek" and rows:
            urls = [row.get("url") for row in rows]
            if not all(urls) or len(set(urls)) != len(urls):
                reasons.append("DeepSeek 会话标识缺失或重复")
    day_file = root / "days" / date / "day.json"
    day = read(day_file) if day_file.exists() else {}
    if day.get("status") != "complete" or day.get("accepted_articles", 0) < 1:
        reasons.append("当日文章生产尚未全部完成")
    receipts = [
        read(path) for path in (root / "approved" / date).glob("*/*/receipt.json")
    ]
    expected_hashes = {r["word_sha256"] for r in receipts}
    if not expected_hashes or len(receipts) != day.get("accepted_articles"):
        reasons.append("服务端成品回执数量不匹配")
    for path in (root / "approved" / date).glob("*/*/receipt.json"):
        receipt = read(path)
        for name, digest in receipt.get("files", {}).items():
            artifact = path.parent / name
            if (
                Path(name).name != name
                or not artifact.is_file()
                or file_hash(artifact) != digest
            ):
                reasons.append("服务端成品文件校验失败")
                break
    acknowledgements = [
        read(path) for path in (root / "local_archive_ack").glob("*.json")
    ]
    delivered = any(
        0 <= now - float(ack.get("checked_epoch", 0)) <= 180
        and expected_hashes
        and expected_hashes <= set(ack.get("word_hashes", []))
        and ack.get("integrity") == "verified"
        for ack in acknowledgements
    )
    if not delivered:
        reasons.append("本地成品下载及哈希回执尚未核验或已过期")
    for name, service in state.get("services", {}).items():
        if service.get("ActiveState") != "active":
            reasons.append(name + " 未运行")
    if not state.get("services"):
        reasons.append("服务运行状态无法核验")
    session = state.get("deepseek") or {}
    if (
        session.get("status") != "ready"
        or not 0 <= now - float(session.get("checked_epoch", 0)) <= 420
    ):
        reasons.append("DeepSeek 登录未就绪或观测已过期")
    api = state.get("api") or {}
    if (
        api.get("status") in {"blocked", "needs_attention"}
        or not 0 <= now - float(api.get("checked_epoch", 0)) <= 600
    ):
        reasons.append("API 执行异常或观测已过期")
    if state.get("attention"):
        reasons.append("存在需要处理的文章票据")
    return list(dict.fromkeys(reasons))


def advance(previous, now, reasons, *, duration=21600):
    if previous.get("status") in {"passed", "failed"}:
        return previous
    started = previous.get("started_epoch")
    if started is not None:
        if (
            now < float(previous.get("checked_epoch", now))
            or now - float(previous.get("checked_epoch", now)) > 180
        ):
            reasons = [*reasons, "观测出现超过三分钟的缺口或时钟回退"]
        if reasons:
            return {
                **previous,
                "status": "failed",
                "checked_epoch": now,
                "reasons": reasons,
                "elapsed_seconds": max(0, now - started),
            }
        elapsed = now - started
        return {
            **previous,
            "status": "passed" if elapsed >= duration else "observing",
            "checked_epoch": now,
            "elapsed_seconds": elapsed,
            "reasons": [],
        }
    if reasons:
        return {
            "status": "waiting_prerequisites",
            "checked_epoch": now,
            "duration_seconds": duration,
            "elapsed_seconds": 0,
            "reasons": reasons,
        }
    return {
        "status": "observing",
        "started_epoch": now,
        "checked_epoch": now,
        "duration_seconds": duration,
        "elapsed_seconds": 0,
        "reasons": [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    import re

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        parser.error("Date must be YYYY-MM-DD")
    root = args.root.resolve()
    path = root / "soak6h/status.json"
    with process_lock(root / "soak6h/observer.lock"):
        while True:
            previous = read(path) if path.exists() else {}
            now = time.time()
            try:
                state = snapshot(root)
                reasons = prerequisites(root, args.date, now, state)
            except (OSError, ValueError, KeyError, TypeError) as error:
                reasons = ["无法核验验收条件：" + type(error).__name__]
            result = {**advance(previous, now, reasons), "date": args.date}
            atomic_json(path, result)
            if result.get("status") != previous.get("status") or result.get(
                "reasons"
            ) != previous.get("reasons"):
                with (path.parent / "events.jsonl").open(
                    "a", encoding="utf8"
                ) as stream:
                    stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(json.dumps(result, ensure_ascii=False), flush=True)
            if args.once or result["status"] in {"passed", "failed"}:
                return 2 if result["status"] == "failed" else 0
            time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
