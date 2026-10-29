import json,hashlib,shutil,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-content/engine')
from geo_source_cards.runtime import process_lock
release=json.loads(Path('/tmp/source-fix-manifest.json').read_text())
backup=Path('/opt/monitor/geo-content/maintenance/source-parser-20261026');backup.mkdir(exist_ok=True)
lock=Path('/opt/monitor/geo-content/studio/capture/plan-29b4419dda224fbd913ae1d9a385497e/profiles/search/wenxin_card/browser.lock')
with process_lock(lock):
 for r in release['files']:
  assert hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['before'],r['name']
  assert hashlib.sha256(Path('/tmp/source-fix',r['name']).read_bytes()).hexdigest()==r['sha256'],r['name']
 for r in release['files']:
  target=Path(r['server']);shutil.copy2(target,backup/r['name']);tmp=target.with_name(target.name+'.source-fix')
  shutil.copy2(Path('/tmp/source-fix',r['name']),tmp);os.chmod(tmp,target.stat().st_mode);os.chown(tmp,target.stat().st_uid,target.stat().st_gid);os.replace(tmp,target)
  assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256']
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
release.update(tests=34,real_article_characters=6141,backup=str(backup))
(backup/'release.json').write_text(json.dumps(release));print(json.dumps(release))
