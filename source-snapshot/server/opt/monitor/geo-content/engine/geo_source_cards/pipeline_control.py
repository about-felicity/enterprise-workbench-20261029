"""Durable operator pause/recheck/resume and validated daily settings."""

import argparse
import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .runtime import atomic_json, process_lock

BEIJING = timezone(timedelta(hours=8))
DEFAULTS = {
    "start_time": "05:00",
    "max_per_category": 10,
    "deepseek_interval": 600,
    "search_interval": 60,
    "article_budget_cny": 0.20,
    "daily_budget_cny": 10.0,
    "test_budget_cny": 0.50,
    "max_revisions": 1,
}


def load(path, default=None):
    try:
        return json.loads(Path(path).read_text("utf-8-sig"))
    except FileNotFoundError:
        return {} if default is None else default


def settings(root):
    return validate_settings({**DEFAULTS, **load(Path(root) / "settings.json")})


def validate_settings(value):
    if set(value) != set(DEFAULTS):
        raise ValueError("设置包含未知字段")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(value["start_time"])):
        raise ValueError("开始时间须为北京时间 HH:MM")
    for key, low, high in (
        ("max_per_category", 1, 100),
        ("deepseek_interval", 300, 600),
        ("search_interval", 60, 600),
        ("max_revisions", 0, 1),
    ):
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError(f"{key} 须在 {low} 至 {high} 之间")
    for key in ("article_budget_cny", "daily_budget_cny", "test_budget_cny"):
        if (
            type(value[key]) not in (int, float)
            or not math.isfinite(value[key])
            or not 0 < value[key] <= 1000
        ):
            raise ValueError("费用上限必须是 0 至 1000 元之间的有效数值")
    return value


def event(root, phase, message, **fields):
    """Only explicitly selected operational data; never raw provider responses."""
    root = Path(root)
    with process_lock(root / "events.lock", blocking=True):
        path = root / "logs" / (datetime.now(BEIJING).date().isoformat() + ".jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf8") as stream:
            stream.write(
                json.dumps(
                    {
                        "epoch": time.time(),
                        "phase": phase,
                        "message": message,
                        **fields,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def state(root):
    return load(Path(root) / "control.json", {"paused": False, "revision": 0})


def pause(root, reason, message):
    root = Path(root)
    with process_lock(root / "control.lock", blocking=True):
        old = state(root)
        if old.get("paused") and old.get("reason") == reason:
            return old
        result = {
            "paused": True,
            "reason": reason,
            "message": message,
            "revision": old.get("revision", 0) + 1,
            "paused_epoch": time.time(),
        }
        atomic_json(root / "control.json", result)
    event(root, "paused", message, reason=reason)
    return result


class PipelinePaused(RuntimeError):
    pass


def ensure_running(root=None):
    root = root or os.environ.get("GEO_PIPELINE_ROOT")
    if root and state(root).get("paused"):
        raise PipelinePaused(state(root).get("reason", "paused"))


def save_settings(root, changes):
    root = Path(root)
    with process_lock(root / "control.lock", blocking=True):
        current = validate_settings({**settings(root), **changes})
        atomic_json(root / "settings.json", current)
        old = state(root)
        atomic_json(
            root / "control.json", {**old, "revision": old.get("revision", 0) + 1}
        )
    event(root, "settings", "任务设置已保存；已开始的批次使用原快照", settings=current)
    return current


def recheck(root, key_file):
    from .deepseek_api import APIError, DeepSeekClient
    from .session_watch import SessionReporter, check_once

    root = Path(root)
    before = state(root)
    os.environ["GEO_PIPELINE_ROOT"] = str(root)
    os.environ["GEO_COLLECTOR_RUNTIME"] = str(root / "collectors/deepseek")
    os.environ["GEO_DEEPSEEK_PORT"] = "9414"
    session = check_once(
        root / "collectors/deepseek",
        SessionReporter(root / "collectors/deepseek", notify=None),
    )
    client = DeepSeekClient(key_file)
    try:
        balance = client.balance()
    except APIError as error:
        balance = {"is_available": False, "error_type": type(error).__name__}
    finally:
        client.close()
    if session.get("status") == "login_required":
        pause(
            root,
            "login_required",
            "DeepSeek 登录失效：登录后重新检测环境，再点击继续任务",
        )
    elif not balance.get("is_available"):
        pause(
            root,
            "api_unavailable",
            "API 余额或凭据不可用：处理后重新检测环境，再点击继续任务",
        )
    after = state(root)
    valid = (
        session.get("status") == "ready"
        and balance.get("is_available") is True
        and before.get("revision", 0) == after.get("revision", 0)
    )
    result = {
        "ok": valid,
        "checked_epoch": time.time(),
        "control_revision": after.get("revision", 0),
        "deepseek": session.get("status"),
        "balance": balance,
    }
    atomic_json(root / "environment_check.json", result)
    atomic_json(root / "api/balance.json", {**balance, "checked_epoch": result["checked_epoch"]})
    event(
        root,
        "environment",
        "环境检测通过；需手动继续" if valid else "环境检测未通过，保持暂停",
        result=result,
    )
    return result


def resume(root):
    root = Path(root)
    with process_lock(root / "control.lock", blocking=True):
        old, checked = state(root), load(root / "environment_check.json")
        age = time.time() - checked.get("checked_epoch", 0)
        if (
            not checked.get("ok")
            or not 0 <= age <= 300
            or checked.get("control_revision") != old.get("revision", 0)
        ):
            raise ValueError("请先点击重新检测环境，检测通过后五分钟内再继续")
        result = {
            "paused": False,
            "revision": old.get("revision", 0) + 1,
            "resumed_epoch": time.time(),
            "resume_requested": True,
        }
        atomic_json(root / "control.json", result)
    event(root, "resumed", "用户确认继续任务；已完成题目不会重发，未知发送状态仍须核对")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("action", choices=["pause", "recheck", "resume", "settings"])
    parser.add_argument("--json", default="{}")
    args = parser.parse_args()
    try:
        if args.action == "pause":
            result = pause(args.root, "operator", "用户暂停任务")
        elif args.action == "recheck":
            result = recheck(
                args.root, args.key_file or args.root.parent / "secrets/deepseek.key"
            )
        elif args.action == "resume":
            result = resume(args.root)
        else:
            result = save_settings(args.root, json.loads(args.json))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    except (ValueError, OSError, RuntimeError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(error)
                    if isinstance(error, ValueError)
                    else type(error).__name__,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
