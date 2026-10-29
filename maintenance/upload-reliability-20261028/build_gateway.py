import subprocess,json
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028');stage=base/'stage'
def run(*args):return subprocess.check_output(args,text=True,timeout=600).strip()
image=run('docker','inspect','monitor-dashboard','--format','{{.Image}}')
run('docker','tag',image,'monitor-dashboard:before-upload-reliability-20261028')
(base/'dashboard-before.json').write_text(json.dumps({'image':image}))
(stage/'Dockerfile').write_text('FROM monitor-dashboard:before-upload-reliability-20261028\nCOPY route.ts /dashboard/app/api/geo-creation/[...path]/route.ts\nCOPY creation-gateway.test.mjs /dashboard/tests/creation-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/creation-gateway.test.mjs tests/capture-gateway.test.mjs\nRUN npm run build\n')
r=subprocess.run(['docker','build','-t','monitor-dashboard:upload-reliability-20261028',str(stage)],capture_output=True,text=True,timeout=600)
(base/'build.log').write_text(r.stdout+r.stderr);print((r.stdout+r.stderr)[-6500:]);raise SystemExit(r.returncode)
