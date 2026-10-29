"""Compile the observed failing INSERT without writes and compare schema."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,subprocess,sqlite3
from pathlib import Path
from active_database_accounts import current_uid
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
 info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
 app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
 uid=current_uid(name)
 db=sqlite3.connect((app/'databases'/('im_database_'+uid)).as_uri()+'?mode=ro',uri=True)
 print(name,'user_version',db.execute('pragma user_version').fetchone()[0],'integrity',db.execute('pragma quick_check').fetchone()[0])
 for row in db.execute("select type,name,sql from sqlite_master where tbl_name='im_conversation' or name like '%conversation%'"):
  print(row)
 columns=[r[1] for r in db.execute('pragma table_info(im_conversation)')]
 try:
  db.execute('EXPLAIN INSERT OR REPLACE INTO im_conversation('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[None]*len(columns)).fetchall()
  print('insert_compiles',True)
 except sqlite3.Error as e:print('insert_compile_error',str(e))
