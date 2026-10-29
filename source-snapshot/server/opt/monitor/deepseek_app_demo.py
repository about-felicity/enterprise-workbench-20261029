import argparse
import ctypes
import subprocess
import time
from ctypes import wintypes

import pyautogui


USER32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def window_pid(hwnd):
    pid = wintypes.DWORD()
    USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def process_name_by_pid(pid):
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-Process -Id %d).ProcessName" % pid],
            encoding="utf-8",
            errors="ignore",
        )
        return out.strip()
    except Exception:
        return ""


def find_window(title_keyword="DeepSeek"):
    matches = []

    def callback(hwnd, _lparam):
        if not USER32.IsWindowVisible(hwnd):
            return True
        length = USER32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        pid = window_pid(hwnd)
        pname = process_name_by_pid(pid)
        if title.strip().lower() == title_keyword.lower() and pname.lower() == "androws":
            matches.insert(0, (hwnd, title, pname))
        elif title_keyword.lower() in title.lower() and pname.lower() == "androws":
            matches.append((hwnd, title, pname))
        return True

    USER32.EnumWindows(EnumWindowsProc(callback), 0)
    if not matches:
        raise RuntimeError("找不到窗口：" + title_keyword)
    return matches[0]


def window_rect(hwnd):
    rect = RECT()
    if not USER32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("获取窗口位置失败")
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def activate_window(hwnd):
    USER32.ShowWindow(hwnd, 9)
    USER32.SetForegroundWindow(hwnd)
    time.sleep(0.6)


def point(rect, rx, ry):
    left, top, width, height = rect
    return int(left + width * rx), int(top + height * ry)


def click_rel(rect, rx, ry, label="", logger=print):
    x, y = point(rect, rx, ry)
    logger("click %s %s %s" % (label, x, y))
    pyautogui.click(x, y)
    time.sleep(0.35)


def set_clipboard_text(text):
    cf_unicode_text = 13
    gmem_moveable = 0x0002
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

    data = (text + "\0").encode("utf-16le")
    h_global = kernel32.GlobalAlloc(gmem_moveable, len(data))
    if not h_global:
        raise RuntimeError("GlobalAlloc failed")
    locked = kernel32.GlobalLock(h_global)
    if not locked:
        raise RuntimeError("GlobalLock failed")
    ctypes.memmove(locked, data, len(data))
    kernel32.GlobalUnlock(h_global)

    if not user32.OpenClipboard(None):
        raise RuntimeError("OpenClipboard failed")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(cf_unicode_text, h_global):
            raise RuntimeError("SetClipboardData failed")
    finally:
        user32.CloseClipboard()


def screenshot_checksum(rect):
    left, top, width, height = rect
    region = (left + int(width * 0.03), top + int(height * 0.12), int(width * 0.88), int(height * 0.70))
    img = pyautogui.screenshot(region=region)
    small = img.resize((64, 96))
    return hash(small.tobytes())


def wait_until_stable(rect, min_wait=10, stable_seconds=5, timeout=90, stop_event=None, logger=print):
    logger("wait loading...")
    start = time.time()
    last = None
    stable_since = None
    while time.time() - start < timeout:
        if stop_event is not None and stop_event.is_set():
            logger("stopped while waiting")
            return False
        time.sleep(1)
        current = screenshot_checksum(rect)
        if time.time() - start < min_wait:
            last = current
            stable_since = None
            continue
        if current == last:
            if stable_since is None:
                stable_since = time.time()
            if time.time() - stable_since >= stable_seconds:
                logger("page stable")
                return True
        else:
            stable_since = None
            last = current
    logger("wait timeout, continue")
    return False


def ask_once(rect, text, logger=print):
    click_rel(rect, 0.28, 0.885, "input", logger=logger)
    set_clipboard_text(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.4)
    click_rel(rect, 0.925, 0.93, "send", logger=logger)


def new_chat(rect, logger=print):
    click_rel(rect, 0.95, 0.065, "new chat", logger=logger)
    time.sleep(1.5)


def run_loop(question, rounds, min_wait=10, stable_seconds=5, timeout=90, stop_event=None, logger=print):
    hwnd, title, pname = find_window("DeepSeek")
    logger("window: %s %s %s" % (title, pname, hwnd))
    activate_window(hwnd)
    rect = window_rect(hwnd)
    logger("rect: %s" % (rect,))

    for index in range(1, rounds + 1):
        if stop_event is not None and stop_event.is_set():
            logger("stopped before round %s" % index)
            break
        logger("round %s/%s" % (index, rounds))
        ask_once(rect, question, logger=logger)
        wait_until_stable(
            rect,
            min_wait=min_wait,
            stable_seconds=stable_seconds,
            timeout=timeout,
            stop_event=stop_event,
            logger=logger,
        )
        if index < rounds:
            if stop_event is not None and stop_event.is_set():
                logger("stopped before new chat")
                break
            new_chat(rect, logger=logger)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="推荐一款染发剂")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--min-wait", type=int, default=10)
    parser.add_argument("--stable-seconds", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    run_loop(args.question, args.rounds, min_wait=args.min_wait, stable_seconds=args.stable_seconds, timeout=args.timeout)


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    main()
