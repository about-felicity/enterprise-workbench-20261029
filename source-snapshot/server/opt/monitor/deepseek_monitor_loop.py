import argparse
import json
import os
import subprocess
import sys
import time

import mumu_deepseek_demo as mumu


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAB_SCRIPT = os.path.join(BASE_DIR, "run_deepseek_latest_grab.py")
DEFAULT_QUESTION = "帮我推荐一款防过敏的白发染发剂"


def log(message):
    text = str(message)
    print(time.strftime("%Y-%m-%d %H:%M:%S"), text, flush=True)


def start_deepseek_app():
    # Keep this lightweight: if the app is already open, Android just brings it forward.
    mumu.adb("shell", "monkey", "-p", mumu.DEEPSEEK_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1", check=False)
    time.sleep(2)


def grab_latest_with_retry(retries=5, delay=6):
    last_stdout = ""
    last_stderr = ""
    for attempt in range(1, retries + 1):
        log(f"grab latest from DeepSeek Web attempt {attempt}/{retries}")
        p = subprocess.run(
            [sys.executable, GRAB_SCRIPT],
            cwd=BASE_DIR,
            encoding="utf-8",
            errors="ignore",
            capture_output=True,
            text=True,
        )
        last_stdout = p.stdout or ""
        last_stderr = p.stderr or ""
        if p.returncode == 0:
            log(last_stdout.strip())
            return True
        log("grab failed: " + (last_stdout.strip() or last_stderr.strip()))
        if attempt < retries:
            time.sleep(delay)
    raise RuntimeError("DeepSeek Web 抓取失败：\n" + last_stdout + "\n" + last_stderr)


def run_round(question, wait_seconds, grab_retries, grab_retry_delay, new_chat=True):
    log("send question: " + question)
    mumu.focus_input()
    mumu.clear_input()
    mumu.input_text(question)
    mumu.click_send()

    log(f"wait answer {wait_seconds}s")
    time.sleep(wait_seconds)

    grab_latest_with_retry(retries=grab_retries, delay=grab_retry_delay)

    if new_chat:
        log("open new chat in MuMu")
        mumu.click_new_chat()
        time.sleep(1.5)


def run_loop(question, rounds, wait_seconds, grab_retries, grab_retry_delay):
    if not os.path.exists(mumu.ADB):
        raise RuntimeError("找不到 MuMu ADB：" + mumu.ADB)
    if not os.path.exists(GRAB_SCRIPT):
        raise RuntimeError("找不到抓取脚本：" + GRAB_SCRIPT)

    mumu.connect()
    start_deepseek_app()

    for index in range(1, rounds + 1):
        log(f"round {index}/{rounds}")
        run_round(
            question=question,
            wait_seconds=wait_seconds,
            grab_retries=grab_retries,
            grab_retry_delay=grab_retry_delay,
            new_chat=index < rounds,
        )
    log("monitor loop done")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--wait", type=int, default=45, help="每轮发送后等待 DeepSeek App/Web 同步的秒数")
    parser.add_argument("--grab-retries", type=int, default=6)
    parser.add_argument("--grab-retry-delay", type=int, default=8)
    args = parser.parse_args()

    try:
        run_loop(
            question=args.question,
            rounds=args.rounds,
            wait_seconds=args.wait,
            grab_retries=args.grab_retries,
            grab_retry_delay=args.grab_retry_delay,
        )
        print(json.dumps({"ok": True}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        raise


if __name__ == "__main__":
    main()
