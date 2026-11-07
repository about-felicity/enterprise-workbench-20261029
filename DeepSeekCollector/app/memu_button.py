"""Windows companion button for explicit user-triggered DeepSeek capture."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from queue import Empty, SimpleQueue
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
import traceback

from memu_capture import CaptureError, MEmu, capture
from remote_sync import RemoteSync


def diagnostic_logger(root):
    logger = logging.getLogger('memu')
    if not logger.handlers:
        try:
            root.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(root / 'diagnostics.log', maxBytes=128_000, backupCount=1,
                                          encoding='utf-8')
        except OSError:
            handler = logging.NullHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
    return logger


def run_operation(operation, output, logger, failure_message):
    try:
        output.put(operation())
    except CaptureError as exc:
        logger.warning('%s: capture rejected (%s)', operation.__name__, type(exc.__cause__ or exc).__name__)
        output.put((None, 0, str(exc)))
    except Exception as exc:
        frames = traceback.extract_tb(exc.__traceback__)
        location = ' > '.join(f'{Path(frame.filename).name}:{frame.lineno}:{frame.name}' for frame in frames)
        logger.error('%s: %s [%s]', operation.__name__, type(exc).__name__, location)
        output.put((None, 0, failure_message))


def find_adb(override):
    if override:
        return override
    for drive in ('C:', 'D:', 'E:'):
        for folder in ('Program Files', 'Program Files (x86)'):
            path = Path(f'{drive}/{folder}/Microvirt/MEmu/adb.exe')
            if path.is_file():
                return path
    if os.name == 'nt':
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                 '[Console]::OutputEncoding=[Text.Encoding]::UTF8;'
                 '(Get-Process MEmu, MEmuConsole -ErrorAction SilentlyContinue).Path'],
                capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8',
            )
            for line in result.stdout.splitlines():
                if line.strip():
                    path = Path(line.strip()).with_name('adb.exe')
                    if path.is_file():
                        return path
        except (OSError, subprocess.SubprocessError):
            pass
    return shutil.which('adb')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--adb', default=os.environ.get('MEMU_ADB'))
    parser.add_argument('--serial', default=os.environ.get('MEMU_SERIAL'))
    parser.add_argument('--check', action='store_true', help='read the visible turn without uploading')
    args = parser.parse_args()
    if args.check:
        adb = find_adb(args.adb)
        if not adb:
            parser.error('未找到逍遥 adb.exe，请用 --adb 指定路径。')
        try:
            record = capture(MEmu(adb, args.serial))
        except CaptureError as exc:
            parser.error(str(exc))
        print(f'本地检查通过：正文 {len(record["reply"])} 字符，信源 {len(record["sources"])} 条。')
        return

    window = tk.Tk()
    window.title('DeepSeek · 逍遥回传')
    window.resizable(False, False)
    window.attributes('-topmost', True)
    window.geometry(f'+{max(0, window.winfo_screenwidth() - 370)}+100')
    frame = ttk.Frame(window, padding=14)
    frame.pack(fill='both', expand=True)
    status = tk.StringVar(value='在逍遥里手动提问，等回答结束后滚到末尾。')
    ttk.Label(frame, textvariable=status, wraplength=315, justify='left').pack(anchor='w', pady=(0, 10))
    output = SimpleQueue()
    uploader = None
    last_request = None
    root = Path(os.environ['LOCALAPPDATA']) / 'DeepSeekCollector' / 'App'
    logger = diagnostic_logger(root / 'memu-data')

    def open_uploader():
        nonlocal uploader
        package = Path(__file__).resolve().parent.parent
        config = root / 'config'
        config.mkdir(parents=True, exist_ok=True)
        public = config / 'public_upload.json'
        if not public.exists():
            shutil.copyfile(package / 'config/public_upload.json', public)
        private = config / 'deepseek_sync.json'
        os.environ['DEEPSEEK_REMOTE_SYNC_CONFIG'] = str(private)
        os.environ['DEEPSEEK_REMOTE_DEVICE'] = 'deepseek-browser-extension'
        if not private.is_file():
            from enrollment import prepare
            prepare(root)
        uploader = RemoteSync(root / 'memu-data', lambda event: event,
                              capture_mode='android_memu_manual',
                              capture_label='DeepSeek 逍遥模拟器手动回传')

    def collect():
        adb = find_adb(args.adb)
        if not adb:
            raise CaptureError('未找到逍遥 adb.exe，请设置 MEMU_ADB 或用 --adb 指定。')
        record = capture(MEmu(adb, args.serial))
        if uploader is None:
            open_uploader()
        result = uploader.enqueue(record)
        if not result.get('enabled'):
            raise CaptureError('回传配置不可用，请检查分发包中的设备登记配置。')
        if not uploader.thread or not uploader.thread.is_alive():
            uploader.start()
        return result['request_id'], len(record['sources']), None

    def resume():
        open_uploader()
        uploader.start()
        return None, 0, '正在继续回传本地待确认记录，可以采集新的回答。'

    def launch(operation, failure_message):
        button.state(['disabled'])
        try:
            threading.Thread(target=run_operation, args=(operation, output, logger, failure_message),
                             daemon=True).start()
        except RuntimeError:
            logger.warning('could not start %s', operation.__name__)
            output.put((None, 0, failure_message))

    def clicked():
        nonlocal last_request
        last_request = None
        status.set('正在核对当前问答及全部信源…')
        launch(collect, '这次回传未完成，请重试。若反复出现，请提供本机 diagnostics.log。')

    def refresh():
        nonlocal last_request
        try:
            request, count, error = output.get_nowait()
        except Empty:
            pass
        else:
            button.state(['!disabled'])
            if error:
                status.set(error)
            else:
                last_request = (request, count)
        if last_request:
            request, count = last_request
            if (uploader.sent / f'{request}.json').is_file():
                status.set(f'已入库 · {count} 条信源')
                last_request = None
            else:
                status.set(f'已保存到本地队列 · {count} 条信源，等待工作台确认。')
        window.after(450, refresh)

    button = ttk.Button(frame, text='回传当前会话', command=clicked)
    button.pack(fill='x')
    if any((root / 'memu-data/remote_sync/outbox').glob('*.json')):
        status.set('正在恢复上次的回传队列…')
        launch(resume, '旧记录仍在本地队列，点击回传可重新连接。')
    window.after(450, refresh)
    window.mainloop()


if __name__ == '__main__':
    main()
