import argparse
import base64
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk


ADB_CANDIDATES = [
    r"C:\Program Files\Netease\MuMu\nx_main\adb.exe",
    r"C:\Program Files\Netease\MuMu\nx_device\15.0\shell\adb.exe",
    r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
    r"C:\Program Files\Tencent\Androws\Application\5.10.6300.6028\adb.exe",
]
ADB = next((path for path in ADB_CANDIDATES if os.path.exists(path)), ADB_CANDIDATES[0])
MUMU_SERIAL = "127.0.0.1:7555"
PACKAGE = "com.deepseek.chat"
ACTIVITY = ".MainActivity"
UNICODE_IME = "io.appium.settings/.UnicodeIME"
APPIUM_IME = "io.appium.settings/.AppiumIME"


def run_adb(args, timeout=20, check=True, serial=None):
    cmd = [ADB]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    p = subprocess.run(cmd, encoding="utf-8", errors="ignore", capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("ADB failed: %s\nstdout=%s\nstderr=%s" % (" ".join(cmd), p.stdout, p.stderr))
    return p.stdout.strip()


def ensure_mumu_connected(serial=MUMU_SERIAL):
    run_adb(["connect", serial], timeout=10, check=False)
    devices = run_adb(["devices", "-l"], timeout=10, check=False)
    lowered = devices.lower()
    if serial.lower() not in lowered or (serial.lower() + "         device") not in lowered:
        raise RuntimeError("MuMu ADB 未连接或未在线，请确认端口 %s：\n%s" % (serial, devices))
    return devices


def shell(command, timeout=20, check=True, serial=MUMU_SERIAL):
    return run_adb(["shell", command], timeout=timeout, check=check, serial=serial)


def get_size():
    out = shell("wm size")
    # Physical size: 1260x2720
    text = out.split(":")[-1].strip()
    width, height = text.split("x")
    return int(width), int(height)


def tap(x, y):
    shell("input tap %d %d" % (int(x), int(y)), timeout=10)


def keyevent(code):
    shell("input keyevent %s" % code, timeout=10)


def start_deepseek():
    shell("am start -n %s/%s" % (PACKAGE, ACTIVITY), timeout=15, check=False)
    time.sleep(1.2)


def set_ime(ime):
    shell("ime set %s" % ime, timeout=10, check=False)
    time.sleep(0.2)


def input_unicode_text(text, logger=print):
    # Appium UnicodeIME variants used by different builds.
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    attempts = [
        "am broadcast -a ADB_INPUT_B64 --es msg %s" % encoded,
        "am broadcast -a ADB_INPUT_TEXT --es msg '%s'" % text.replace("'", "\\'"),
        "am broadcast -a io.appium.settings.unicode --es text %s" % encoded,
        "am broadcast -a io.appium.settings.unicode --es text '%s'" % text.replace("'", "\\'"),
    ]
    for command in attempts:
        out = shell(command, timeout=10, check=False)
        logger("input broadcast: %s => %s" % (command.split(" ")[3] if len(command.split(" ")) > 3 else command, out))
        time.sleep(0.4)


def click_input(width, height, logger=print):
    x = width * 0.28
    y = height * 0.91
    logger("tap input %d %d" % (x, y))
    tap(x, y)
    time.sleep(0.5)


def click_send(width, height, logger=print):
    x = width * 0.925
    y = height * 0.93
    logger("tap send %d %d" % (x, y))
    tap(x, y)
    time.sleep(0.5)


def click_new_chat(width, height, logger=print):
    x = width * 0.95
    y = height * 0.055
    logger("tap new chat %d %d" % (x, y))
    tap(x, y)
    time.sleep(1.5)


def screenshot_bytes(serial=MUMU_SERIAL):
    p = subprocess.run([ADB, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=20)
    if p.returncode != 0:
        return b""
    return p.stdout


def wait_stable(min_wait=10, stable_seconds=5, timeout=90, stop_event=None, logger=print):
    logger("wait loading...")
    start = time.time()
    last = b""
    stable_since = None
    while time.time() - start < timeout:
        if stop_event is not None and stop_event.is_set():
            logger("stopped while waiting")
            return False
        time.sleep(1)
        current = screenshot_bytes()
        if time.time() - start < min_wait:
            last = current
            stable_since = None
            continue
        if current and current == last:
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


def ask_once(question, width, height, logger=print):
    click_input(width, height, logger=logger)
    set_ime(UNICODE_IME)
    input_unicode_text(question, logger=logger)
    time.sleep(0.5)
    click_send(width, height, logger=logger)


def run_loop(question, rounds, min_wait=10, stable_seconds=5, timeout=90, stop_event=None, logger=print, serial=MUMU_SERIAL):
    if not os.path.exists(ADB):
        raise RuntimeError("找不到 ADB：" + ADB)
    devices = ensure_mumu_connected(serial)
    logger(devices)
    logger("using adb: " + ADB)
    start_deepseek()
    width, height = get_size()
    logger("screen: %sx%s" % (width, height))

    for index in range(1, rounds + 1):
        if stop_event is not None and stop_event.is_set():
            break
        logger("round %s/%s" % (index, rounds))
        ask_once(question, width, height, logger=logger)
        wait_stable(min_wait=min_wait, stable_seconds=stable_seconds, timeout=timeout, stop_event=stop_event, logger=logger)
        if index < rounds:
            click_new_chat(width, height, logger=logger)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek ADB 后台循环")
        self.root.geometry("780x560")
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None

        self.question = tk.StringVar(value="推荐一款染发剂")
        self.rounds = tk.StringVar(value="10")
        self.min_wait = tk.StringVar(value="10")
        self.stable = tk.StringVar(value="5")
        self.timeout = tk.StringVar(value="90")
        self.status = tk.StringVar(value="就绪")

        self.build()
        self.root.after(150, self.drain)

    def build(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text="DeepSeek ADB 后台循环", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(main, text="通过 ADB 操作安卓容器，不占用鼠标。DeepSeek 窗口可以不在前台，但应用宝/Androws 不能关闭。", foreground="#666").pack(anchor="w", pady=(6, 14))

        form = ttk.Frame(main)
        form.pack(fill=tk.X)
        ttk.Label(form, text="问题").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.question).grid(row=0, column=1, columnspan=7, sticky="ew", padx=(8, 0), pady=6)

        items = [("轮数", self.rounds), ("最少等待", self.min_wait), ("稳定秒", self.stable), ("超时秒", self.timeout)]
        for i, (label, var) in enumerate(items):
            ttk.Label(form, text=label).grid(row=1, column=i * 2, sticky="w", pady=6)
            ttk.Entry(form, textvariable=var, width=8).grid(row=1, column=i * 2 + 1, sticky="w", padx=(8, 16), pady=6)
        form.columnconfigure(1, weight=1)

        row = ttk.Frame(main)
        row.pack(fill=tk.X, pady=(10, 8))
        self.check_btn = ttk.Button(row, text="检测 ADB", command=self.check_adb)
        self.check_btn.pack(side=tk.LEFT)
        self.start_btn = ttk.Button(row, text="开始后台循环", command=self.start)
        self.start_btn.pack(side=tk.LEFT, padx=8)
        self.stop_btn = ttk.Button(row, text="停止", command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        ttk.Label(row, textvariable=self.status, foreground="#0f766e").pack(side=tk.RIGHT)

        self.log_text = tk.Text(main, font=("Consolas", 10), wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.queue.put(str(message))

    def drain(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(150, self.drain)

    def check_adb(self):
        try:
            self.log(run_adb(["devices"]))
            self.log("size: " + shell("wm size"))
            self.log("focus: " + shell("dumpsys window | grep mCurrentFocus", check=False))
            self.status.set("ADB 正常")
        except Exception as exc:
            messagebox.showerror("ADB 检测失败", str(exc))
            self.status.set("ADB 失败")

    def to_int(self, var, name):
        try:
            return int(var.get().strip())
        except Exception:
            raise ValueError(name + " 必须是整数")

    def start(self):
        try:
            question = self.question.get().strip()
            if not question:
                raise ValueError("问题不能为空")
            rounds = self.to_int(self.rounds, "轮数")
            min_wait = self.to_int(self.min_wait, "最少等待")
            stable = self.to_int(self.stable, "稳定秒")
            timeout = self.to_int(self.timeout, "超时秒")
        except Exception as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.stop_event.clear()
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.check_btn.configure(state=tk.DISABLED)
        self.status.set("运行中")
        self.worker = threading.Thread(target=self.worker_main, args=(question, rounds, min_wait, stable, timeout), daemon=True)
        self.worker.start()

    def worker_main(self, question, rounds, min_wait, stable, timeout):
        try:
            run_loop(question, rounds, min_wait=min_wait, stable_seconds=stable, timeout=timeout, stop_event=self.stop_event, logger=self.log)
            self.root.after(0, lambda: self.status.set("已停止" if self.stop_event.is_set() else "完成"))
        except Exception as exc:
            self.log("错误：" + repr(exc))
            self.root.after(0, lambda: self.status.set("出错"))
            self.root.after(0, lambda: messagebox.showerror("运行出错", str(exc)))
        finally:
            self.root.after(0, self.finish)

    def finish(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.check_btn.configure(state=tk.NORMAL)

    def stop(self):
        self.stop_event.set()
        self.status.set("正在停止")
        self.log("收到停止请求")


def gui_main():
    root = tk.Tk()
    App(root)
    root.mainloop()


def cli_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="推荐一款染发剂")
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--min-wait", type=int, default=10)
    parser.add_argument("--stable-seconds", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    if args.gui:
        gui_main()
    else:
        run_loop(args.question, args.rounds, min_wait=args.min_wait, stable_seconds=args.stable_seconds, timeout=args.timeout)


if __name__ == "__main__":
    cli_main()
