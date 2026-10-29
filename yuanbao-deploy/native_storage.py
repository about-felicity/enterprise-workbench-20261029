"""Read-only Yuanbao native store discovery; never modifies App databases."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess

CONTAINER = 'yuanbao-hpe14-android13'
PACKAGE = 'com.tencent.hunyuan.app.chat'
REQUIRED = {
    'ChatMessages': {'message_id','conversation_id','speaker','status','raw_data'},
    'ChatMessagesContecnt': {'message_id','conversation_id','content_id','trace_id'},
    'ChatMessageEntities': {'message_id','conversation_id','content_id','type','object_json'},
    'ChatConversationDetail': {'conversation_id','stop_generating','end_conv'},
}

class StorageError(RuntimeError):
    pass


def history_stores(conversation_id,directory=None):
    groups=[]
    for path in (directory or app_directory()).glob('files/dtmp/Users/*/Database/history_conversation.db'):
        with open_readonly(path) as db:
            columns={r['name'] for r in db.execute('pragma table_info(conversation_list)')}
            if not {'id','title','deleted_at','top_time','last_replied_at'}.issubset(columns):raise StorageError('Native history schema changed')
            rows=[dict(r) for r in db.execute('select id,title from conversation_list where coalesce(deleted_at,0)=0 order by coalesce(top_time,0) desc,last_replied_at desc,id')]
            if any(r['id']==conversation_id for r in rows):groups.append(rows)
    return groups

def app_directory():
    info = json.loads(subprocess.check_output(['docker','inspect',CONTAINER], timeout=15))[0]
    if info['Config'].get('Labels',{}).get('geo.collector') != 'yuanbao':
        raise StorageError('Wrong container ownership')
    mount = next(m for m in info['Mounts'] if m['Destination']=='/data')
    if mount.get('Name') != 'yuanbao-hpe14-android13-data':
        raise StorageError('Unexpected Android volume')
    return Path(mount['Source'])/'data'/PACKAGE

def open_readonly(path):
    connection = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('pragma query_only=on')
    return connection

def schema(connection):
    tables = {r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
    if not REQUIRED.keys() <= tables:
        return False
    for table, expected in REQUIRED.items():
        columns = {r[1] for r in connection.execute('pragma table_info("'+table+'")')}
        if not expected <= columns:
            raise StorageError('Yuanbao native schema changed: '+table)
    return True

def databases(directory=None):
    directory = directory or app_directory()
    found = []
    for path in directory.rglob('*.db'):
        try:
            with path.open('rb') as stream:
                if stream.read(16) != b'SQLite format 3\0':
                    continue
            with closing(open_readonly(path)) as db:
                if schema(db):
                    found.append(path)
        except (OSError,sqlite3.Error):
            continue
    if not found:
        raise StorageError('No compatible native chat store found')
    return sorted(found)

def inspection():
    result = []
    for path in databases():
        with closing(open_readonly(path)) as db:
            result.append({'schema_compatible':True,
                'counts':{table:db.execute('select count(*) from "'+table+'"').fetchone()[0]
                          for table in REQUIRED}})
    return {'stores':result,'read_only':True,'capture_enabled':False,
            'note':'Native capture and completeness still require authenticated sample validation.'}

if __name__ == '__main__':
    print(json.dumps(inspection(),ensure_ascii=False))
