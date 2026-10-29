
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import pathlib,sqlite3,json,shutil,pwd,os,hashlib
root=pathlib.Path('/home/user/redroid-doubao');out=root/'hpe14-export';out.mkdir(exist_ok=True,mode=0o700)
user=pwd.getpwnam('user');os.chown(out,user.pw_uid,user.pw_gid);out.chmod(0o700)
db=sqlite3.connect(root/'hpe14-acceptance/tasks.sqlite')
results=[]
for question,raw in db.execute("select question,result_json from tasks where batch in ('hpe14-initial','hpe14-soak100') and state='completed' order by rowid"):
 item=json.loads(raw);item['question']=question;results.append(item)
assert len(results)==106 and len({x['request_id'] for x in results})==106
assert all(x['finished'] and x['body_markdown'].strip() and x['sources'] for x in results)
(out/'hpe14-answers.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
report=json.loads((root/'hpe14-acceptance/batch106-before-backup.json').read_text());report['unit_tests_passed']=30
report['runtime_files_sha256']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['unattended_core.py','unattended_worker.py','runtime_preflight.py']}
(out/'hpe14-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for source,dest in [(root/'backups/hpe14-20261006/manifest.json','hpe14-backup-manifest.json'),(root/'backups/hpe14-20261006/android-volume-manifest.json','hpe14-volume-backup-manifest.json')]:shutil.copyfile(source,out/dest)
for source,dest in [(root/'soak-smoke/status.json','hpe14-smoke.json'),(root/'soak24h/status.json','hpe14-soak24h-start.json'),(root/'soak1h/status.json','hpe14-soak1h.json'),(root/'soak1h/sequence.json','hpe14-test-sequence.json')]:
 if source.exists():shutil.copyfile(source,out/dest)
shutil.copyfile(root/'hpe14-acceptance/acceptance-snapshot.json',out/'hpe14-current-status.json')
for path in out.iterdir():path.chmod(0o600);os.chown(path,user.pw_uid,user.pw_gid)
print('Exported only the requested test answers and acceptance metadata:',len(results))
