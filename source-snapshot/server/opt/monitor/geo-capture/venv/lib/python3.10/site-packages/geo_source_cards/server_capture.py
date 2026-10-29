"""Daily Linux capture batch, with persistent ten-minute DeepSeek spacing."""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .daily_editorial import DEFAULT_MEDIA, prepare_day
from .article_fetch import MediaScopedFetcher, ScraplingArticleFetcher
from .editorial_pipeline import prepare as fetch_articles
from .runtime import atomic_json, atomic_write, process_lock
from .staged_editorial import read
from .pipeline_control import ensure_running, event, pause, settings, state


def run_batch(root, questions, product, date, *, batch_label="daily", subset=None):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(
        r"[a-zA-Z0-9_-]{1,60}", batch_label
    ):
        raise ValueError("Unsafe capture date or batch label")
    root = Path(root).resolve()
    ensure_running(root)
    capture = root / "captures" / date / batch_label
    capture.mkdir(parents=True, exist_ok=True)
    with process_lock(root / "capture_batch.lock"):
        config_path = capture / "settings.json"
        config = read(config_path) if config_path.exists() else settings(root)
        atomic_json(config_path, config)
        event(root, "capture", "开始或继续每日采集；每题每平台一轮", date=date)

        def collect(model):
            if state(root).get("paused"):
                return 2
            runtime = (
                root / "collectors" / ("deepseek" if model == "deepseek" else "baidu")
            )
            output = capture / (model + ".jsonl")
            command = [
                sys.executable,
                "-m",
                "geo_source_cards.cli",
                "--model",
                model,
                "--runtime-dir",
                str(runtime),
                "--questions-file",
                str(questions),
                "--output",
                str(output),
                "--batch",
                f"{date}-{batch_label}-{model}",
                "--require-sources",
                "--require-complete-sources",
                "--min-deepseek-interval",
                str(config["deepseek_interval"]),
                "--min-search-interval",
                str(config["search_interval"]),
                "--rounds",
                "1",
            ]
            env = {
                **os.environ,
                "GEO_DEEPSEEK_PORT": "9414",
                "GEO_PIPELINE_ROOT": str(root),
                "PYTHONUNBUFFERED": "1",
            }
            if model == "baidu_ai":
                command.append("--optional-baidu")
            if model in {"baidu_ai", "wenxin_card"}:
                command.append("--bounded-search-recovery")
            with (capture / (model + ".log")).open("a", encoding="utf8") as stream:
                result = subprocess.run(
                    command, env=env, stdout=stream, stderr=subprocess.STDOUT
                )
            atomic_json(
                capture / (model + "_status.json"),
                {"returncode": result.returncode, "output": str(output)},
            )
            return result.returncode

        # One DeepSeek browser and one Baidu browser; Baidu and Wenxin share a serial lane.
        models = subset or ["deepseek", "baidu_ai", "wenxin_card"]
        results = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(collect, "deepseek") if "deepseek" in models else None
            # Required Wenxin data must get the shared browser before the
            # optional Baidu supplement and its bounded retries.
            for model in ("wenxin_card", "baidu_ai"):
                if model in models:
                    results[model] = collect(model)
            if future:
                results["deepseek"] = future.result()
        if any(results.values()):
            if not state(root).get("paused"):
                pause(
                    root,
                    "capture_incomplete",
                    "采集未完成，详见日志；已完成题目不会重跑，失败题须核对",
                )
            atomic_json(
                capture / "status.json",
                {"status": "blocked_capture_incomplete", "platforms": results},
            )
            return {"status": "blocked_capture_incomplete", "platforms": results}
        rows = []
        for model in models:
            rows.extend(
                json.loads(line)
                for line in (capture / (model + ".jsonl"))
                .read_text(encoding="utf8")
                .splitlines()
                if line.strip()
                and json.loads(line).get("availability") != "supplement_unavailable"
            )
        atomic_write(
            capture / "observations.jsonl",
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        )
        ensure_running(root)
        event(
            root,
            "source_fetch",
            "采集完成，开始抓取信源文章正文",
            date=date,
            observations=len(rows),
        )
        fetched = fetch_articles(
            capture / "observations.jsonl",
            product,
            capture / "source_analysis",
            date,
            fetcher=MediaScopedFetcher(ScraplingArticleFetcher(), DEFAULT_MEDIA),
        )
        if fetched["status"] == "blocked_no_article_text":
            return fetched
        result = prepare_day(
            root,
            capture / "source_analysis/articles.jsonl",
            product,
            date,
            max_per_category=config["max_per_category"],
        )
        event(
            root,
            "analysis",
            "信源抓取结束，准备分类与写作",
            date=date,
            state=result.get("status"),
        )
        atomic_json(capture / "status.json", result)
        return result


def seed_session(root, seed):
    from web_collectors.collector import BrowserCollector

    root, seed = Path(root), Path(seed)
    state = read(seed)
    os.environ["GEO_COLLECTOR_RUNTIME"] = str(root / "collectors/deepseek")
    os.environ["GEO_DEEPSEEK_PORT"] = "9414"
    os.environ["MONITOR_DEEPSEEK_COOKIES_JSON"] = json.dumps(state["cookies"])
    os.environ["MONITOR_DEEPSEEK_STORAGE_JSON"] = json.dumps(state["storage"])
    with process_lock(root / "collectors/deepseek/collector.lock"):
        collector = BrowserCollector("deepseek", headless=True)
        try:
            collector.page.call("Page.navigate", {"url": "https://chat.deepseek.com/"})
            result = collector.check_ready()
            atomic_json(
                root / "session_migration.json",
                {"ok": bool(result.get("ok")), "status": result.get("status")},
            )
            if result.get("ok"):
                seed.unlink()
            return {"ok": bool(result.get("ok")), "status": result.get("status")}
        finally:
            collector.close()
            os.environ.pop("MONITOR_DEEPSEEK_COOKIES_JSON", None)
            os.environ.pop("MONITOR_DEEPSEEK_STORAGE_JSON", None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--seed", type=Path)
    parser.add_argument("--questions", type=Path)
    parser.add_argument("--product", type=Path)
    parser.add_argument(
        "--date", default=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    )
    parser.add_argument("--batch-label", default="daily")
    parser.add_argument(
        "--model", action="append", choices=["deepseek", "baidu_ai", "wenxin_card"]
    )
    args = parser.parse_args(argv)
    if args.seed:
        result = seed_session(args.root, args.seed)
    else:
        if not args.questions or not args.product:
            parser.error("Questions and product are required")
        result = run_batch(
            args.root,
            args.questions,
            args.product,
            args.date,
            batch_label=args.batch_label,
            subset=args.model,
        )
    print(json.dumps(result, ensure_ascii=False))
    return (
        2
        if result.get("status", "").startswith("blocked") or result.get("ok") is False
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
