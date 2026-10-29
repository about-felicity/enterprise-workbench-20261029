import hashlib,shutil,json,tarfile,time,py_compile
from pathlib import Path
base=Path('/opt/monitor/geo-content/creation');backup=Path('/opt/monitor/maintenance/automatic-supplement-20261028/deploy');backup.mkdir(parents=True,exist_ok=True)
expected={'materials.py':'2f0d0b9f8047c2fcff391559c78f1da87d31009c5be7e6f359cf1e63a6b6423f','studio.py':'45b40e2a00c7439e8a81abbf44c4f5cf6b1cb772b54bce3f48ab27ee64597754','search_capture.py':'90cc8b54c0051653a6fe4ada3ec4a1f87f124c1485b027f306303863ebcee21e','panel.html':'c32c1cf0bdaccde4569438dfc97b1ffb0d5d953aa22f64414c425b590360fca3'}
for n,h in expected.items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
names=[*expected,'supplement.py']
for n in names:
 src=Path('/tmp/supplement28-stage/creation')/n
 if n.endswith('.py'):py_compile.compile(str(src),doraise=True)
for n in names:
 if (base/n).exists():shutil.copy2(base/n,backup/n)
 shutil.copy2(Path('/tmp/supplement28-stage/creation')/n,base/n)
policy=Path('/opt/monitor/geo-content/runtime/supplement_policy.json')
if policy.exists():shutil.copy2(policy,backup/'supplement_policy.json')
policy.write_text(json.dumps({'enabled':True,'start_date':'2026-10-28','include_days':['plan-0d57811d9b2543eab75d181badec6d9e--2026-10-26'],'enabled_at':time.time()}))
files=[{'source':'geo-monitor-deploy/creation/'+n,'server':str(base/n),'sha256':hashlib.sha256((base/n).read_bytes()).hexdigest()} for n in names]
(backup/'release.json').write_text(json.dumps({'files':files},indent=2));print(json.dumps({'files':files}))
