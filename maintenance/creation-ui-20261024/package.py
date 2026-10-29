from pathlib import Path
import zipfile
W=Path(__file__).resolve().parents[2];R=W/'geo-monitor-deploy/creation'
p=R/'studio.py';s=p.read_text('utf8')
s=s.replace("j.get('day',{}).get('status')!='complete' for j in js", "j.get('day',{}).get('status') not in TERMINAL_JOBS for j in js")
s=s.replace("  elif p.get('task_type')=='capture_only' and all(v['completed']>=target for v in progress):state='complete'\n",'')
p.write_bytes(s.encode('utf8'))
with zipfile.ZipFile(Path(__file__).with_name('changes.zip'),'w',zipfile.ZIP_DEFLATED) as z:
 for n in ['panel.html','studio.py','runtime.py','test_task_controls.py']:
  p=R/n;raw=p.read_text('utf8');base=W/'source-snapshot/local/geo-monitor-deploy/creation'/n
  newline='\r\n' if base.exists() and b'\r\n' in base.read_bytes() else '\n'
  p.write_bytes(raw.replace('\n',newline).encode('utf8'));z.write(p,'creation/'+n)
