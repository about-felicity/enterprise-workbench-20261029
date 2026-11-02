import subprocess, json,urllib.request
for u in ['geo-monitor-status','geo-daily-control','geo-daily-dispatch.timer']:
 print(u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','ExecStart','-p','MainPID'],capture_output=True,text=True).stdout[:600])
print(subprocess.run(['ss','-ltnp','sport = :8803'],capture_output=True,text=True).stdout)
try:
 v=json.load(urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=15));print(v.keys(),[m['id'] for m in v['models']])
except Exception as e:print(type(e).__name__,str(e))
