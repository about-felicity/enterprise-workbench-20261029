"""Cooperative DeepSeek session checks and local login notifications."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable

from .runtime import atomic_json, process_lock, runtime_root


class LoginRequiredError(RuntimeError):
    """An explicit logged-out page was observed; never replay a submission."""


def desktop_notify(status: str, message: str) -> None:
    """Best-effort desktop notice; console and health/event files are primary."""
    title = (
        "内容任务已暂停"
        if status == "pipeline_paused"
        else "DeepSeek 登录提醒"
        if status == "login_required"
        else "DeepSeek 登录已恢复"
    )
    try:
        if os.name == "nt":
            # A separate hidden helper avoids blocking the worker on a dialog.
            code = (
                "import ctypes,sys\n"
                "from ctypes import wintypes\n"
                "kernel=ctypes.windll.kernel32\n"
                "kernel.CreateMutexW.restype=wintypes.HANDLE\n"
                "kernel.CloseHandle.argtypes=[wintypes.HANDLE]\n"
                "handle=kernel.CreateMutexW(None,False,r'Local\\GeoDeepSeekSessionNotice')\n"
                "existing=kernel.GetLastError()==183\n"
                "if not existing: ctypes.windll.user32.MessageBoxW(0,sys.argv[2],sys.argv[1],0x40|0x40000)\n"
                "if handle: kernel.CloseHandle(handle)\n"
            )
            subprocess.Popen(
                [sys.executable, "-c", code, title, message],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif shutil.which("notify-send"):
            subprocess.run(
                ["notify-send", title, message],
                timeout=5,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except (OSError, subprocess.SubprocessError):
        # Desktop notifications may be unavailable on servers or locked sessions.
        pass


class SessionReporter:
    def __init__(
        self,
        root: Path | None = None,
        *,
        reminder_seconds: int = 900,
        notify: Callable[[str, str], None] | None = desktop_notify,
        clock: Callable[[], float] = time.time,
    ):
        self.root = root or runtime_root()
        self.reminder_seconds = reminder_seconds
        self.notify = notify
        self.clock = clock

    def publish(self, observation: dict) -> dict:
        status = observation.get("status", "unknown")
        if status not in {"ready", "login_required", "unknown"}:
            status = "unknown"
        if status == "login_required" and os.environ.get("GEO_PIPELINE_ROOT"):
            from .pipeline_control import pause

            pause(
                os.environ["GEO_PIPELINE_ROOT"],
                "login_required",
                "DeepSeek 登录失效；登录后重新检测环境，再由用户继续任务",
            )
        with process_lock(self.root / "deepseek_session.lock"):
            path = self.root / "deepseek_session.json"
            try:
                old = json.loads(path.read_text(encoding="utf8"))
                if not isinstance(old, dict):
                    old = {}
            except (OSError, ValueError):
                old = {}
            now = self.clock()
            since = old.get("login_required_since")
            last_alert = old.get("last_login_alert_at")
            event = None
            if status == "login_required":
                since = since if since is not None else now
                if last_alert is None or now - last_alert >= self.reminder_seconds:
                    event = "login_required"
                    last_alert = now
            elif status == "ready":
                if since is not None:
                    event = "login_restored"
                since = last_alert = None
            state = {
                "status": status,
                "checked_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "checked_epoch": now,
                "message": observation.get("message", ""),
                "login_required_since": since,
                "last_login_alert_at": last_alert,
            }
            atomic_json(path, state)
            if event or old.get("status") != status:
                self.root.mkdir(parents=True, exist_ok=True)
                with (self.root / "deepseek_session_events.jsonl").open(
                    "a", encoding="utf8"
                ) as stream:
                    stream.write(
                        json.dumps(
                            {**state, "event": event or "status_changed"},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
        if event:
            message = (
                (
                    "DeepSeek 登录已失效，请停止当前采集后执行：\n"
                    "python -m geo_source_cards.cli --model deepseek --login\n"
                    "请使用原来的 --runtime-dir。发送结果不明的任务须人工核对。"
                )
                if event == "login_required"
                else "DeepSeek 网页登录已恢复；任务仍暂停，请点击重新检测环境，再点击继续任务。"
            )
            print(
                json.dumps({"event": event, "message": message}, ensure_ascii=False),
                flush=True,
            )
            if self.notify:
                try:
                    self.notify(
                        "login_required" if event == "login_required" else "ready",
                        message,
                    )
                except Exception as exc:
                    print(
                        json.dumps(
                            {
                                "event": "notification_failed",
                                "error_type": type(exc).__name__,
                            }
                        ),
                        file=sys.stderr,
                        flush=True,
                    )
        return state


def check_once(root: Path, reporter: SessionReporter, *, factory=None) -> dict:
    """Open the profile only while idle; never attach to an active collector."""
    if factory is None:
        from .cli import create_collector

        factory = create_collector
    lock = process_lock(root / "collector.lock")
    try:
        lock.__enter__()
    except RuntimeError:
        state = {
            "status": "check_skipped",
            "reason": "collector_or_login_active",
            "checked_epoch": time.time(),
        }
        atomic_json(root / "deepseek_watch.json", state)
        return state
    collector = None
    try:
        try:
            collector = factory("deepseek", show_browser=False)
            collector.session_reporter = reporter
            observation = collector.check_ready()
        except Exception as exc:
            observation = {
                "status": "unknown",
                "message": f"浏览器检查失败（{type(exc).__name__}），无法核验登录状态",
            }
        result = reporter.publish(observation)
    finally:
        try:
            if collector is not None:
                try:
                    collector.close()
                except Exception as exc:
                    result = reporter.publish(
                        {
                            "status": "unknown",
                            "message": f"浏览器清理失败（{type(exc).__name__}），请检查进程",
                        }
                    )
        finally:
            lock.__exit__(None, None, None)
    atomic_json(root / "deepseek_watch.json", result)
    return result


def watch(
    root: Path,
    *,
    interval: int = 180,
    reporter: SessionReporter | None = None,
    stop: Event | None = None,
) -> None:
    reporter = reporter or SessionReporter(root)
    stop = stop or Event()
    with process_lock(root / "deepseek_watch.lock"):
        while not stop.is_set():
            state = check_once(root, reporter)
            print(
                json.dumps({"watch": state["status"]}, ensure_ascii=False), flush=True
            )
            if stop.wait(interval):
                break


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="DeepSeek login watcher; no questions are sent"
    )
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--interval", type=int, default=180)
    parser.add_argument("--reminder-interval", type=int, default=900)
    parser.add_argument("--no-desktop", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.interval < 30 or args.reminder_interval < args.interval:
        parser.error(
            "Check interval must be >=30 seconds; reminder interval must be >= check interval"
        )
    if args.runtime_dir:
        os.environ["GEO_COLLECTOR_RUNTIME"] = str(args.runtime_dir.resolve())
    root = runtime_root()
    reporter = SessionReporter(
        root,
        reminder_seconds=args.reminder_interval,
        notify=None if args.no_desktop else desktop_notify,
    )
    if args.once:
        result = check_once(root, reporter)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return {"ready": 0, "login_required": 2}.get(result["status"], 3)
    try:
        watch(root, interval=args.interval, reporter=reporter)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
