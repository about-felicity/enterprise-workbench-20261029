"""Read the latest visible DeepSeek Android turn through MEmu's local ADB."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


class CaptureError(ValueError):
    pass


class MEmu:
    def __init__(self, adb, serial=None):
        self.adb = str(adb)
        self.serial = serial

    def call(self, *args, device=True, destination=None):
        command = [self.adb, *(['-s', self.serial] if device and self.serial else []), *args]
        try:
            return subprocess.run(command, stdout=destination if destination is not None else subprocess.PIPE,
                                  stderr=subprocess.PIPE, check=True, timeout=20,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            raise CaptureError('无法读取逍遥模拟器，请检查模拟器和 ADB 连接。') from exc

    def select(self):
        devices = [line.split()[0] for line in self.call('devices', device=False).decode().splitlines()
                   if len(line.split()) == 2 and line.split()[1] == 'device']
        if self.serial:
            if self.serial not in devices:
                raise CaptureError('指定的逍遥模拟器实例未连接。')
        elif len(devices) == 1:
            self.serial = devices[0]
        else:
            raise CaptureError('请连接一个模拟器实例，或启动时用 --serial 指定设备。')

    def view(self):
        foreground = self.call('shell', 'dumpsys activity activities').decode(errors='replace')
        if not re.search(r'(?:mResumedActivity|topResumedActivity):[^\r\n]* com\.deepseek\.chat/', foreground):
            raise CaptureError('请在逍遥模拟器里打开 DeepSeek 的目标会话。')
        # UI Automator appends a status line after the XML on this Android build.
        closing_tag = b'</hierarchy>'
        for _ in range(2):
            output = self.call('exec-out', 'uiautomator dump /proc/self/fd/1')
            start = output.find(b'<hierarchy')
            end = output.rfind(closing_tag)
            if start >= 0 and end > start:
                try:
                    root = ET.fromstring(output[start:end + len(closing_tag)])
                except ET.ParseError:
                    continue
                return visible_turn(root)
        raise CaptureError('未读到完整界面，请等回答完全结束后再点回传。')

    @contextmanager
    def databases(self):
        with tempfile.TemporaryFile() as snapshot:
            self.call('exec-out', 'cd /data/data/com.deepseek.chat/databases && '
                      'tar cf - deepseek_chat_*.db deepseek_chat_*.db-wal', destination=snapshot)
            snapshot.seek(0)
            yield snapshot


def bounds(node):
    return tuple(map(int, re.findall(r'-?\d+', node.get('bounds', ''))))


def normalized(value):
    value = re.sub(r'\[citation:\d+\]', '', value)
    return ''.join(character for character in value.casefold() if character.isalnum())


def visible_turn(root):
    nodes = [node for node in root.iter('node') if node.get('package') == 'com.deepseek.chat'
             and len(bounds(node)) == 4]
    if any(node.get('text') == '搜索结果' for node in nodes):
        raise CaptureError('请先关闭「搜索结果」面板，回到回答末尾。')
    if any('停止生成' in (node.get('content-desc', '') + node.get('text', '')) for node in nodes):
        raise CaptureError('DeepSeek 还在生成，请等待回答结束。')
    sidebar = [bounds(node) for node in nodes if node.get('content-desc') == '打开侧边栏']
    if len(sidebar) != 1:
        raise CaptureError('无法确认当前会话，请回到 DeepSeek 会话正文。')
    left, top, right, bottom = sidebar[0]
    titles = [node.get('text') for node in nodes if node.get('text') and bounds(node)[0] >= right
              and bounds(node)[1] >= top - 5 and bounds(node)[3] <= bottom + 5]
    sources = [(node, re.fullmatch(r'\s*(\d+)\s*个网页\s*', node.get('text', '')))
               for node in nodes]
    sources = [(node, match) for node, match in sources if match]
    if len(titles) != 1 or not sources:
        raise CaptureError('请滚到最新回答末尾，确认可见「N 个网页」和回答操作按钮。')
    source, count = max(sources, key=lambda item: bounds(item[0])[1])
    source_y = bounds(source)[1]
    if not any(node.get('content-desc') == '复制' and bounds(node)[1] >= source_y for node in nodes):
        raise CaptureError('最新回答的完成按钮不可见，请滚到回答末尾。')
    texts = sorted(((bounds(node)[3], normalized(node.get('text', ''))) for node in nodes
                    if bottom < bounds(node)[3] <= source_y), reverse=True)
    anchors = tuple(value for _, value in texts if len(value) >= 12)[:4]
    if not anchors:
        raise CaptureError('请让回答末段和「N 个网页」同时显示后重试。')
    return titles[0], int(count.group(1)), anchors


def fragments(message):
    parts = json.loads(message['fragments'])
    if not isinstance(parts, list) or not all(isinstance(part, dict) for part in parts):
        raise CaptureError('DeepSeek 会话格式发生变化。')
    return parts


def normalize_turn(session_id, user, answer, expected_count, anchors):
    if answer['role'] != 'ASSISTANT' or answer['status'] != 'FINISHED' or user['role'] != 'USER':
        return None
    prompt = '\n'.join(part['content'] for part in fragments(user)
                       if part.get('type') == 'REQUEST' and isinstance(part.get('content'), str)).strip()
    parts = fragments(answer)
    reply = '\n\n'.join(part['content'] for part in parts
                        if part.get('type') == 'RESPONSE' and isinstance(part.get('content'), str)).strip()
    if not any(anchor in normalized(reply)[-2500:] for anchor in anchors):
        return None
    searches = [part for part in parts if part.get('type') == 'SEARCH']
    if not searches or any(part.get('status') != 'FINISHED' or not isinstance(part.get('results'), list)
                           for part in searches):
        return None
    sources = []
    for part in searches:
        for item in part['results']:
            if not isinstance(item, dict) or not isinstance(item.get('url'), str):
                return None
            url = item['url'].strip()
            parsed = urlsplit(url)
            if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
                return None
            source = {key: item[key] for key in ('title', 'snippet', 'cite_index', 'published_at', 'site_name')
                      if item.get(key) is not None}
            source.update(url=url, domain=parsed.hostname, title=source.get('title') or url)
            sources.append(source)
    if not prompt or not sources or len(sources) != expected_count:
        return None
    if len(reply) < 60 or len(prompt) > 2000:
        raise CaptureError('当前工作台要求正文至少 60 字符，问题最多 2000 字符。')
    identity = hashlib.sha256(f'memu:{session_id}:{answer["message_id"]}'.encode()).hexdigest()
    return {
        'result_id': identity, 'run_id': 'deepseek-memu-' + identity[:20], 'round': 1,
        'prompt': prompt, 'reply': reply, 'status': 'success', 'detected_model': 'deepseek',
        'finished_at': datetime.fromtimestamp(answer['inserted_at'], timezone.utc).isoformat(),
        'sources': sources, 'expected_source_count': expected_count,
        'source_capture_complete': True, 'body_capture_complete': True,
    }


def matching_records(snapshot, view):
    title, count, anchors = view
    records = []
    with tempfile.TemporaryDirectory(prefix='ds-memu-') as directory:
        root = Path(directory)
        with tarfile.open(fileobj=snapshot, mode='r|') as archive:
            for entry in archive:
                if not entry.isfile() or not re.fullmatch(r'deepseek_chat_[\w-]+\.db(?:-wal)?', entry.name):
                    raise CaptureError('模拟器返回了非预期的会话文件。')
                with archive.extractfile(entry) as source, (root / entry.name).open('wb') as target:
                    shutil.copyfileobj(source, target, length=256 * 1024)
        for path in root.glob('*.db'):
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                db.row_factory = sqlite3.Row
                for session in db.execute('select id,current_message_id from chat_session_list where title=?', (title,)):
                    session_id = session['id']
                    if not isinstance(session_id, str) or not re.fullmatch(r'[\w-]+', session_id):
                        continue
                    table = f'"chat_session_messages_{session_id}"'
                    if not db.execute("select 1 from sqlite_master where type='table' and name=?",
                                      ('chat_session_messages_' + session_id,)).fetchone():
                        continue
                    statement = f'select * from {table} where message_id=?'
                    answer = db.execute(statement, (session['current_message_id'],)).fetchone()
                    if answer is None or answer['parent_id'] is None:
                        continue
                    user = db.execute(statement, (answer['parent_id'],)).fetchone()
                    if user is not None:
                        record = normalize_turn(session_id, user, answer, count, anchors)
                        if record is not None:
                            records.append(record)
    return records


def capture(device):
    device.select()
    try:
        view = device.view()
        with device.databases() as snapshot:
            first = matching_records(snapshot, view)
        if len(first) != 1:
            raise CaptureError('未能唯一确认当前最新问答及完整信源，请等待回答结束并滚到末尾。')
        if device.view() != view:
            raise CaptureError('会话内容发生变化，请停在同一回答末尾再点回传。')
        with device.databases() as snapshot:
            if matching_records(snapshot, view) != first:
                raise CaptureError('会话内容发生变化，请停在同一回答末尾再点回传。')
    except (sqlite3.Error, tarfile.TarError, UnicodeError, ValueError, KeyError) as exc:
        if isinstance(exc, CaptureError):
            raise
        raise CaptureError('会话数据暂时无法确认，请稍后重试。') from exc
    return first[0]
