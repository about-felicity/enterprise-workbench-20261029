"""Persistent daily server scheduler. No auto-resume after an operator gate."""

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

from .pipeline_control import (
    BEIJING,
    PipelinePaused,
    ensure_running,
    event,
    load,
    pause,
    settings,
    state,
)
from .runtime import atomic_json, process_lock
from .server_capture import run_batch


def due(root, now):
    root = Path(root)
    control = state(root)
    if control.get("paused"):
        return None
    last = load(root / "scheduler.json")
    # Resumes stay attached to the original batch even across midnight.
    if last.get("status") in {"running", "paused", "blocked"}:
        if control.get("resume_requested") and control.get(
            "resumed_epoch", 0
        ) > last.get("attempt_epoch", 0):
            return last["date"]
        return None
    today = now.date().isoformat()
    if last.get("date") == today:
        return None
    return today if now.strftime("%H:%M") >= settings(root)["start_time"] else None


def once(root, now=None):
    root = Path(root)
    now = now or datetime.now(BEIJING)
    date = due(root, now)
    if not date:
        return
    attempted = time.time()
    atomic_json(
        root / "scheduler.json",
        {"date": date, "status": "running", "attempt_epoch": attempted},
    )
    try:
        ensure_running(root)
        # No paid request: a live page login check plus the balance endpoint.
        from .pipeline_control import recheck

        check = recheck(root, root.parent / "secrets/deepseek.key")
        if not check["ok"]:
            pause(
                root, "environment", "开始采集前环境检测未通过，请处理后重新检测并继续"
            )
            raise PipelinePaused()
        result = run_batch(root, root / "questions.txt", root / "product.json", date)
        status = (
            "completed"
            if result.get("status") in {"waiting_taxonomy", "producing", "completed"}
            else "blocked"
        )
        if status == "blocked" and not state(root).get("paused"):
            pause(
                root,
                "capture_incomplete",
                "当日采集或信源正文不完整，停止后续 API 消费",
            )
    except PipelinePaused:
        status = "paused"
    except Exception as error:  # noqa: BLE001 -- latch operational failures instead of silently restarting capture
        status = "blocked"
        pause(
            root,
            "capture_error",
            "采集流程停止：" + type(error).__name__ + "；详见日志",
        )
        event(
            root,
            "error",
            "调度未完成，须检查后手动继续",
            error_type=type(error).__name__,
        )
    atomic_json(
        root / "scheduler.json",
        {
            "date": date,
            "status": status,
            "attempt_epoch": attempted,
            "checked_epoch": time.time(),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    os.environ["GEO_PIPELINE_ROOT"] = str(args.root.resolve())
    with process_lock(args.root / "scheduler.lock"):
        previous = load(args.root / "scheduler.json")
        if previous.get("status") == "running":
            pause(
                args.root,
                "interrupted",
                "上次采集被中断；需核对发送状态后重新检测并继续",
            )
        while True:
            once(args.root)
            time.sleep(15)


if __name__ == "__main__":
    main()
