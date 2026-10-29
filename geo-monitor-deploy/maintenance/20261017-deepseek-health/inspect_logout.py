"""Read-only bounded diagnostics. Never output tokens or raw Android logs."""
import collections
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess

def cmd(*a):return subprocess.check_output(a,text=True,errors='replace',timeout=30)
container='deepseek-hpe14-android13'
info=json.loads(cmd('docker','inspect',container))[0]
begin=datetime(2026,10,17,6,35,tzinfo=timezone.utc).timestamp()
end=datetime(2026,10,17,6,55,tzinfo=timezone.utc).timestamp()
logs=cmd('docker','exec',container,'logcat','-d','-v','epoch','-t','20000')
times=[];window=[];signals=collections.Counter()
patterns={
 'http_401':r'\b(?:HTTP(?:/\S+)?\s+|response\s*code\s*[:=]?\s*)401\b',
 'http_403':r'\b(?:HTTP(?:/\S+)?\s+|response\s*code\s*[:=]?\s*)403\b',
 'expired_token_or_session':r'(?:token|session).{0,30}(?:expir|invalid)|(?:expir|invalid).{0,30}(?:token|session)',
 'explicit_logged_out':r'logout|logged.?out|session.{0,20}revok|kicked|登录过期|账号在其他|会话失效',
}
for line in logs.splitlines():
 m=re.match(r'\s*(\d{10}\.\d+)',line)
 if not m:continue
 at=float(m[1]);times.append(at)
 if begin<=at<=end:
  window.append(at)
  for name,pattern in patterns.items():
   if re.search(pattern,line,re.I):signals[name]+=1
exit_info=cmd('docker','exec',container,'dumpsys','activity','exit-info','com.deepseek.chat')
exit_reasons=re.findall(r'reason=([^\n]+)',exit_info)
kernel=cmd('journalctl','-k','--since','2026-10-17 06:35:00 UTC','--until','2026-10-17 06:55:00 UTC','--no-pager','-o','cat')
report={
 'checked_at':datetime.now(timezone.utc).isoformat(),
 'logout_detected_beijing':'2026-10-17 14:46:13',
 'container_started_at':info['State']['StartedAt'],
 'container_restarts':info['RestartCount'],'container_oom_killed':info['State']['OOMKilled'],
 'data_mounts':[{'type':m['Type'],'name':m.get('Name'),'destination':m['Destination'],'rw':m['RW']} for m in info['Mounts'] if m['Destination']=='/data'],
 'bounded_logcat_rows':len(times),
 'bounded_logcat_earliest_utc':datetime.fromtimestamp(min(times),timezone.utc).isoformat() if times else None,
 'bounded_logcat_latest_utc':datetime.fromtimestamp(max(times),timezone.utc).isoformat() if times else None,
 'logout_window_log_rows':len(window),'auth_signal_counts':dict(signals),
 'app_exit_reasons':[r[:100] for r in exit_reasons],
 'kernel_oom_events_in_window':sum(bool(re.search(r'out of memory|oom-kill|killed process',l,re.I)) for l in kernel.splitlines()),
 'conclusion':'No server-side logout reason is inferred from missing client logs; raw logs and tokens are not exported.'
}
root=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-health');root.mkdir(exist_ok=True,parents=True)
(root/'logout-diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
Path('/tmp/deepseek-logout-diagnostics-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
