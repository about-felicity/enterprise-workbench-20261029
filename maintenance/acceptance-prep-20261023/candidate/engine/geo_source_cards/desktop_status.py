"""Read-only status endpoint for the native desktop application; no browser starts."""

import argparse
import json
import os
import sqlite3
import subprocess
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None
    except (ValueError, OSError):
        return {"status": "unreadable", "file": Path(path).name}


def snapshot(root):
    root = Path(root).resolve()
    days = [
        load(path) for path in sorted((root / "days").glob("*/day.json"), reverse=True)
    ]
    tickets = [load(path) for path in (root / "queue").glob("*/ticket.json")]
    attention = [
        {
            "ticket": item.get("id"),
            "stage": item.get("stage"),
            "date": item.get("meta", {}).get("date"),
            "category": item.get("meta", {}).get("category"),
            "number": item.get("meta", {}).get("number"),
            "state": item.get("state"),
            "error": item.get("error", ""),
        }
        for item in tickets
        if item and item.get("state") == "needs_attention"
    ]
    services = {}
    for name in (
        "geo-editorial-coordinator.service",
        "geo-editorial-session-watch.service",
        "geo-editorial-api-worker.service",
        "geo-editorial-scheduler.service",
    ):
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "show",
                    name,
                    "--property=ActiveState,NRestarts,MemoryCurrent,LoadState",
                    "--no-pager",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            services[name] = dict(
                line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
            )
        except (OSError, subprocess.TimeoutExpired):
            services[name] = {"ActiveState": "unknown"}
    captures = {}
    capture_attention = []
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    for model, directory in (
        ("deepseek", "deepseek"),
        ("baidu_ai", "baidu"),
        ("wenxin_card", "baidu"),
    ):
        database = root / "collectors" / directory / "tasks.sqlite"
        if not database.exists():
            continue
        try:
            with sqlite3.connect(
                database.as_uri() + "?mode=ro", uri=True, timeout=3
            ) as connection:
                captures[model] = dict(
                    connection.execute(
                        "select state,count(*) from captures where model=? and batch like ? group by state",
                        (model, today + "-%"),
                    )
                )
                capture_attention.extend(
                    {"model": model, "question": row[0], "error": row[1], "batch": row[2]}
                    for row in connection.execute(
                        "select question,error,batch from captures where model=? and state='needs_attention' order by started desc limit 20",
                        (model,),
                    )
                )
        except sqlite3.Error:
            captures[model] = {"status": "unreadable"}
    memory = {}
    try:
        memory = {
            line.split(":")[0]: int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith(("MemTotal:", "MemAvailable:"))
        }
    except (OSError, ValueError):
        pass
    from .api_budget import Budget
    from .pipeline_control import settings, state

    budget = Budget(root)
    try:
        costs = budget.summary()
    finally:
        budget.close()
    logs = []
    for path in sorted((root / "logs").glob("*.jsonl"))[-2:]:
        with path.open(encoding="utf8") as stream:
            for line in deque(stream, maxlen=150):
                try:
                    logs.append(json.loads(line))
                except ValueError:
                    pass
    return {
        "checked_epoch": time.time(),
        "today": datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
        "health": load(root / "health.json"),
        "days": days,
        "attention": attention,
        "deepseek": load(root / "collectors/deepseek/deepseek_session.json"),
        "services": services,
        "captures": captures,
        "capture_attention": capture_attention,
        "memory": memory,
        "load": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
        "api": load(root / "api/health.json"),
        "settings": settings(root),
        "control": state(root),
        "environment_check": load(root / "environment_check.json"),
        "costs": costs,
        "historical_cost_audit": load(root / "historical_cost_audit.json"),
        "balance": load(root / "api/balance.json"),
        "runtime_logs": logs[-150:],
        "scheduler": load(root / "scheduler.json"),
        "schedule": load(root / "schedule_state.json")
        or {
            "status": "not_verified",
            "start_time": settings(root)["start_time"],
            "max_per_category": settings(root)["max_per_category"],
            "reason": "DeepSeek API 调度尚未核验",
        },
        "soak": load(root / "soak6h/status.json") or {"status": "not_started"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.root), ensure_ascii=False))


if __name__ == "__main__":
    main()
