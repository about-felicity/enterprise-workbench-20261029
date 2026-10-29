"""Real collector uid regression; no browser, question or API request."""
import os,pwd,subprocess,tempfile,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['/opt/monitor/geo-content/maintenance/20261017-creation-permissions/stage','/opt/monitor/geo-content/engine']
from creation import materials
owner=pwd.getpwnam('user')
with tempfile.TemporaryDirectory() as temp:
 parent=Path(temp);parent.chmod(0o711);base=parent/'content';base.mkdir(mode=0o700)
 private=base/'materials';private.mkdir(mode=0o700);os.chown(private,owner.pw_uid,owner.pw_gid)
 days=private/'days';days.mkdir(mode=0o700)
 runtime=days/'2099-01-01'/'deepseek'/'collector'
 unrelated=base/'runtime';unrelated.mkdir(mode=0o700);(unrelated/'private.json').write_text('private')
 with patch.object(materials,'ROOT',private),patch.object(materials,'CONTENT_BASE',base):
  materials.collector_directory(runtime,owner)
  command=['/usr/sbin/runuser','-u','user','--','python3','-c','from pathlib import Path;import sys;p=Path(sys.argv[1]);(p/"probe").write_text("ok");assert (p/"probe").read_text()=="ok"',str(runtime)]
  subprocess.run(command,check=True)
  assert subprocess.run(['/usr/sbin/runuser','-u','user','--','test','-r',str(base)]).returncode!=0
  assert subprocess.run(['/usr/sbin/runuser','-u','user','--','test','-r',str(unrelated/'private.json')]).returncode!=0
  try:materials.collector_directory(parent/'outside',owner);raise AssertionError('Must reject escaping path')
  except ValueError:pass
  assert all((p.stat().st_mode&0o777)==0o700 for p in [private,days,runtime.parent.parent,runtime.parent,runtime])
print(json.dumps({'passed':True,'actual_collector_uid':owner.pw_uid,'collector_can_write':True,'parent_listing_denied':True,'unrelated_private_data_unreadable':True,'no_browser_or_paid_calls':True}))
