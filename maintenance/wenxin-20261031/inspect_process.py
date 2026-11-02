import json,subprocess
from pathlib import Path
root=Path('/opt/monitor/geo-capture/batches/geo-panel-baidu-ai-20261031-090001-88a32968')
print('capture_log', (root/'capture.log').read_text(errors='replace')[-9000:])
print('locks',subprocess.run(['lslocks','--notruncate','--output','PID,COMMAND,TYPE,MODE,BLOCKER,PATH'],capture_output=True,text=True).stdout[-6500:])
print('processes')
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  if any(s in args for s in ['geo_source_cards.cli','capture_bridge','flock -x /opt/monitor/geo-capture/search_browser.lock']):
   print(p.name, (p/'wchan').read_text().strip(),args[:1050])
 except OSError:pass
print('daily',subprocess.run(['journalctl','-u','geo-daily-control','--since','today','-n','15','--no-pager'],capture_output=True,text=True).stdout[-2500:])
