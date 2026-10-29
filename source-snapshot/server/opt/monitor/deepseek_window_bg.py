import argparse
import ctypes
import subprocess
import time
from ctypes import wintypes


USER32 = ctypes.windll.user32
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
VK_CONTROL = 0x11
VK_V = 0x56
MK_LBUTTON = 0x0001


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


def find_androws_deepseek():
    matches = []

    def callback(hwnd, _lparam):
        if not USER32.IsWindowVisible(hwnd):
            return True
        length = USER32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        pid = window_pid(hwnd)
        pname = process_name_by_pid(pid)
        if pname.lower() == "androws" and title.lower() == "deepseek":
            matches.insert(0, (hwnd, title, pname))
        elif pname.lower() == "androws" and "deepseek" in title.lower():
            matches.append((hwnd, title, pname))
        return True

    USER32.EnumWindows(EnumWindowsProc(callback), 0)
    if not matches:
        raise RuntimeError("找不到桌面模拟器 DeepSeek 窗口（Androws / DeepSeek）")
    return matches[0]


def client_size(hwnd):
    rect = RECT()
    if not USER32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetClientRect failed")
    return rect.right - rect.left, rect.bottom - rect.top


def lparam(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def post_click(hwnd, x, y, label="", logger=print):
    logger("post click %s %s %s" % (label, int(x), int(y)))
    lp = lparam(x, y)
    USER32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
    time.sleep(0.08)
    USER32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lp)
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


def post_ctrl_v(hwnd, logger=print):
    logger("post ctrl+v")
    USER32.PostMessageW(hwnd, WM_KEYDOWN, VK_CONTROL, 0)
    time.sleep(0.05)
    USER32.PostMessageW(hwnd, WM_KEYDOWN, VK_V, 0)
    time.sleep(0.05)
    USER32.PostMessageW(hwnd, WM_KEYUP, VK_V, 0)
    time.sleep(0.05)
    USER32.PostMessageW(hwnd, WM_KEYUP, VK_CONTROL, 0)
    time.sleep(0.5)


def post_chars(hwnd, text, logger=print):
    logger("post chars length=%s" % len(text))
    for ch in text:
        USER32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        time.sleep(0.02)
    time.sleep(0.4)


def ask_once(hwnd, question, logger=print, char_fallback=False):
    width, height = client_size(hwnd)
    logger("client size: %sx%s" % (width, height))
    post_click(hwnd, width * 0.28, height * 0.89, "input", logger=logger)
    set_clipboard_text(question)
    post_ctrl_v(hwnd, logger=logger)
    if char_fallback:
        post_chars(hwnd, question, logger=logger)
    post_click(hwnd, width * 0.925, height * 0.93, "send", logger=logger)


def new_chat(hwnd, logger=print):
    width, height = client_size(hwnd)
    post_click(hwnd, width * 0.95, height * 0.065, "new chat", logger=logger)
    time.sleep(1.5)


def run_loop(question, rounds, wait_seconds=25, logger=print, char_fallback=False):
    hwnd, title, pname = find_androws_deepseek()
    logger("window: %s %s %s" % (title, pname, hwnd))
    for index in range(1, rounds + 1):
        logger("round %s/%s" % (index, rounds))
        ask_once(hwnd, question, logger=logger, char_fallback=char_fallback)
        logger("wait %ss" % wait_seconds)
        time.sleep(wait_seconds)
        if index < rounds:
            new_chat(hwnd, logger=logger)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="推荐一款染发剂")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--wait-seconds", type=int, default=25)
    parser.add_argument("--char-fallback", action="store_true")
    args = parser.parse_args()
    run_loop(args.question, args.rounds, wait_seconds=args.wait_seconds, char_fallback=args.char_fallback)


if __name__ == "__main__":
    main()
