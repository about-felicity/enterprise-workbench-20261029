import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pyautogui

import deepseek_app_demo as controller


class DeepSeekLoopGui:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek 自动循环")
        self.root.geometry("760x560")
        self.root.minsize(680, 500)

        self.log_queue = queue.Queue()
        self.worker = None
        self.stop_event = threading.Event()

        self.question_var = tk.StringVar(value="推荐一款染发剂")
        self.rounds_var = tk.StringVar(value="10")
        self.min_wait_var = tk.StringVar(value="10")
        self.stable_var = tk.StringVar(value="5")
        self.timeout_var = tk.StringVar(value="90")
        self.status_var = tk.StringVar(value="就绪")

        self.build_ui()
        self.root.after(150, self.drain_log_queue)

    def build_ui(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 15, "bold"))
        style.configure("Status.TLabel", foreground="#0f766e")

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="DeepSeek 自动循环控制台", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="独立运行，不依赖影刀。开始后会控制 DeepSeek 窗口：输入、发送、等待稳定、新建对话、继续下一轮。",
            foreground="#666",
        ).pack(anchor="w", pady=(6, 14))

        form = ttk.Frame(outer)
        form.pack(fill=tk.X)

        ttk.Label(form, text="问题").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.question_var).grid(row=0, column=1, columnspan=5, sticky="ew", padx=(10, 0), pady=6)

        fields = [
            ("轮数", self.rounds_var),
            ("最少等待秒", self.min_wait_var),
            ("稳定秒数", self.stable_var),
            ("单轮超时秒", self.timeout_var),
        ]
        for index, (label, var) in enumerate(fields):
            col = index * 2
            ttk.Label(form, text=label).grid(row=1, column=col, sticky="w", pady=6)
            ttk.Entry(form, textvariable=var, width=9).grid(row=1, column=col + 1, sticky="w", padx=(8, 16), pady=6)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.columnconfigure(5, weight=1)

        button_row = ttk.Frame(outer)
        button_row.pack(fill=tk.X, pady=(12, 8))

        self.check_button = ttk.Button(button_row, text="检测窗口", command=self.check_window)
        self.check_button.pack(side=tk.LEFT)
        self.start_button = ttk.Button(button_row, text="开始循环", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=8)
        self.stop_button = ttk.Button(button_row, text="停止", command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)

        ttk.Label(button_row, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.RIGHT)

        tips = ttk.Label(
            outer,
            text="安全提示：如果鼠标失控，把鼠标快速移到屏幕左上角会触发 pyautogui 安全停止。",
            foreground="#9a6b00",
        )
        tips.pack(anchor="w", pady=(0, 8))

        log_frame = ttk.LabelFrame(outer, text="运行日志")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=16, wrap="word", font=("Consolas", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

    def log(self, message):
        self.log_queue.put(str(message))

    def drain_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(150, self.drain_log_queue)

    def check_window(self):
        try:
            hwnd, title, pname = controller.find_window("DeepSeek")
            rect = controller.window_rect(hwnd)
            self.status_var.set("已找到窗口")
            self.log("找到窗口：%s / %s / %s / rect=%s" % (title, pname, hwnd, rect))
        except Exception as exc:
            self.status_var.set("未找到窗口")
            messagebox.showerror("检测失败", str(exc))

    def parse_int(self, var, name, minimum=1):
        try:
            value = int(var.get().strip())
        except Exception:
            raise ValueError(name + " 必须是整数")
        if value < minimum:
            raise ValueError(name + " 不能小于 %s" % minimum)
        return value

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            question = self.question_var.get().strip()
            if not question:
                raise ValueError("问题不能为空")
            rounds = self.parse_int(self.rounds_var, "轮数")
            min_wait = self.parse_int(self.min_wait_var, "最少等待秒")
            stable_seconds = self.parse_int(self.stable_var, "稳定秒数")
            timeout = self.parse_int(self.timeout_var, "单轮超时秒")
        except Exception as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.stop_event.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.check_button.configure(state=tk.DISABLED)
        self.status_var.set("运行中")
        self.log("开始：rounds=%s question=%s" % (rounds, question))

        self.worker = threading.Thread(
            target=self.run_worker,
            args=(question, rounds, min_wait, stable_seconds, timeout),
            daemon=True,
        )
        self.worker.start()

    def run_worker(self, question, rounds, min_wait, stable_seconds, timeout):
        try:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            controller.run_loop(
                question,
                rounds,
                min_wait=min_wait,
                stable_seconds=stable_seconds,
                timeout=timeout,
                stop_event=self.stop_event,
                logger=self.log,
            )
            if self.stop_event.is_set():
                self.log("已停止")
                self.root.after(0, lambda: self.status_var.set("已停止"))
            else:
                self.log("全部完成")
                self.root.after(0, lambda: self.status_var.set("完成"))
        except Exception as exc:
            self.log("错误：" + repr(exc))
            self.root.after(0, lambda: self.status_var.set("出错"))
            self.root.after(0, lambda: messagebox.showerror("运行出错", str(exc)))
        finally:
            self.root.after(0, self.finish_run)

    def finish_run(self):
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.check_button.configure(state=tk.NORMAL)

    def stop(self):
        self.stop_event.set()
        self.status_var.set("正在停止")
        self.log("收到停止请求，将在当前等待/当前轮结束前停止")


def main():
    root = tk.Tk()
    DeepSeekLoopGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
