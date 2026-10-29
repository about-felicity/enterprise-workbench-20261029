import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_SCRIPT = os.path.join(BASE_DIR, "deepseek_web_monitor_loop.py")
DASHBOARD_SCRIPT = os.path.join(BASE_DIR, "deepseek_dashboard_server.py")
DATA_FILES = [
    os.path.join(BASE_DIR, "deepseek_refs_result.csv"),
    os.path.join(BASE_DIR, "deepseek_refs_result.xlsx"),
    os.path.join(BASE_DIR, "deepseek_api_check.json"),
]

DEFAULT_QUESTIONS = [
    "帮我推荐一款防过敏的白发染发剂",
    "推荐一款温和不刺激的染发剂",
    "推荐一款适合敏感头皮的遮白染发剂",
    "推荐一款家用泡泡染发剂",
    "推荐一款不伤发的植物染发剂",
]


class DeepSeekMonitorGui:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek 多问题监控启动器")
        self.root.geometry("980x720")
        self.queue = queue.Queue()
        self.monitor_proc = None
        self.dashboard_proc = None
        self.questions_file = ""

        self.rounds_per_question = tk.StringVar(value="200")
        self.timeout = tk.StringVar(value="150")
        self.stable = tk.StringVar(value="8")
        self.status = tk.StringVar(value="就绪")

        self.build()
        self.root.after(200, self.drain)
        self.root.after(1000, self.refresh_status)

    def build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="DeepSeek 多问题监控启动器", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="每天把问题写在下面，一行一个；启动后会按问题逐个跑，并在面板里按问题统计信源。",
            foreground="#566",
        ).pack(anchor="w", pady=(6, 14))

        question_box_frame = ttk.LabelFrame(outer, text="问题列表（一行一个）", padding=10)
        question_box_frame.pack(fill=tk.BOTH, expand=False)
        self.questions_text = tk.Text(question_box_frame, height=8, font=("Microsoft YaHei UI", 10), wrap="word")
        self.questions_text.pack(fill=tk.BOTH, expand=True)
        self.questions_text.insert("1.0", "\n".join(DEFAULT_QUESTIONS))

        form = ttk.Frame(outer)
        form.pack(fill=tk.X, pady=(14, 8))
        fields = [("每个问题轮数", self.rounds_per_question), ("单轮超时秒", self.timeout), ("链接稳定秒", self.stable)]
        for i, (label, var) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=i * 2, sticky="w", pady=7)
            ttk.Entry(form, textvariable=var, width=12).grid(row=0, column=i * 2 + 1, sticky="w", padx=(8, 24), pady=7)
        form.columnconfigure(7, weight=1)

        buttons = ttk.Frame(outer)
        buttons.pack(fill=tk.X, pady=(4, 12))
        ttk.Button(buttons, text="启动 DeepSeek 面板", command=self.start_dashboard).pack(side=tk.LEFT)
        ttk.Button(buttons, text="打开 DeepSeek 面板", command=lambda: webbrowser.open("http://127.0.0.1:8766/")).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="打开豆包面板", command=lambda: webbrowser.open("http://127.0.0.1:8765/")).pack(side=tk.LEFT)
        ttk.Button(buttons, text="清空 DeepSeek 数据", command=self.clear_data).pack(side=tk.LEFT, padx=(8, 0))
        self.start_btn = ttk.Button(buttons, text="开始多问题监控", command=self.start_monitor)
        self.start_btn.pack(side=tk.LEFT, padx=(20, 8))
        self.stop_btn = ttk.Button(buttons, text="停止监控", command=self.stop_monitor, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        ttk.Label(buttons, textvariable=self.status, foreground="#087f67").pack(side=tk.RIGHT)

        self.log_text = tk.Text(outer, font=("Consolas", 10), wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.queue.put(time.strftime("%H:%M:%S ") + str(message))

    def drain(self):
        try:
            while True:
                line = self.queue.get_nowait()
                self.log_text.insert(tk.END, line + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(200, self.drain)

    def to_int(self, var, name):
        try:
            value = int(var.get().strip())
            if value <= 0:
                raise ValueError
            return value
        except Exception:
            raise ValueError(name + "必须是正整数")

    def get_questions(self):
        raw = self.questions_text.get("1.0", tk.END)
        questions = [line.strip() for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]
        if not questions:
            raise ValueError("至少填写 1 个问题")
        return questions

    def write_questions_file(self, questions):
        path = os.path.join(BASE_DIR, "deepseek_questions_current.txt")
        with open(path, "w", encoding="utf-8") as f:
            for question in questions:
                f.write(question + "\n")
        self.questions_file = path
        return path

    def clear_data(self):
        if self.monitor_proc and self.monitor_proc.poll() is None:
            messagebox.showwarning("正在监控", "请先停止监控，再清空数据。")
            return
        if not messagebox.askyesno("确认清空", "确定删除 DeepSeek 已抓取的数据表吗？此操作不可撤回。"):
            return
        removed = []
        for path in DATA_FILES:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    removed.append(os.path.basename(path))
            except Exception as exc:
                self.log("删除失败 %s: %r" % (path, exc))
        self.log("已清空 DeepSeek 数据：" + (", ".join(removed) if removed else "没有可删除的数据文件"))

    def start_dashboard(self):
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            self.log("DeepSeek 面板服务已在运行")
            return
        self.dashboard_proc = subprocess.Popen(
            [sys.executable, DASHBOARD_SCRIPT],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        threading.Thread(target=self.pipe_output, args=(self.dashboard_proc, "dashboard"), daemon=True).start()
        self.log("DeepSeek 面板服务启动：http://127.0.0.1:8766/")

    def start_monitor(self):
        try:
            questions = self.get_questions()
            rounds = self.to_int(self.rounds_per_question, "每个问题轮数")
            timeout = self.to_int(self.timeout, "单轮超时秒")
            stable = self.to_int(self.stable, "链接稳定秒")
        except Exception as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        if self.monitor_proc and self.monitor_proc.poll() is None:
            messagebox.showinfo("正在运行", "DeepSeek 监控已经在运行")
            return

        self.start_dashboard()
        questions_file = self.write_questions_file(questions)
        total = len(questions) * rounds
        self.log(f"准备启动：{len(questions)} 个问题，每题 {rounds} 轮，共 {total} 轮")
        self.log("问题文件：" + questions_file)

        self.monitor_proc = subprocess.Popen(
            [
                sys.executable,
                MONITOR_SCRIPT,
                "--questions-file", questions_file,
                "--rounds-per-question", str(rounds),
                "--timeout", str(timeout),
                "--stable-seconds", str(stable),
            ],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        threading.Thread(target=self.pipe_output, args=(self.monitor_proc, "monitor"), daemon=True).start()
        self.status.set("监控运行中")
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        webbrowser.open("http://127.0.0.1:8766/")

    def pipe_output(self, proc, name):
        try:
            for line in proc.stdout:
                self.log("[%s] %s" % (name, line.rstrip()))
        except Exception as exc:
            self.log("[%s] output error: %r" % (name, exc))

    def stop_monitor(self):
        if self.monitor_proc and self.monitor_proc.poll() is None:
            self.monitor_proc.terminate()
            self.log("已发送停止请求")
        self.status.set("已停止")
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def refresh_status(self):
        if self.monitor_proc and self.monitor_proc.poll() is not None:
            self.start_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)
            self.status.set("监控已结束")
        self.root.after(1000, self.refresh_status)


def main():
    root = tk.Tk()
    DeepSeekMonitorGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
