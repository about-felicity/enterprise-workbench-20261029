"""Inspect only the copied chat database schema; never query account databases."""
import sqlite3
import json
from pathlib import Path
path = Path('/home/user/redroid-doubao/chat-store-snapshot/chat.db')
print('SQLite header:', path.open('rb').read(16) == b'SQLite format 3\x00')
db = sqlite3.connect(str(path))
db.row_factory = sqlite3.Row
for row in db.execute("select content,fts_content,reference_info from im_message where fts_content like '%官方地址%' or content like '%官方地址%' order by create_time desc limit 2"):
    print(json.dumps(dict(row), ensure_ascii=False))
