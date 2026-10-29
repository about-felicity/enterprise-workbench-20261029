"""Create a clean second Android; copy only the signed APK, never user data."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess
from pathlib import Path

def run(*args):
    return subprocess.check_output(args,text=True).strip()

name='doubao-hpe14-account2'
volume='doubao-hpe14-account2-data'
root=Path('/home/user/redroid-doubao/account2')
root.mkdir(exist_ok=True)
if name in run('docker','ps','-a','--format','{{.Names}}').splitlines():
    raise SystemExit('Container already exists; inspect before making changes')
if volume in run('docker','volume','ls','--format','{{.Name}}').splitlines():
    raise SystemExit('Volume already exists; inspect before making changes')
apk_path=run('docker','exec','doubao-hpe14-13-test','pm','path','com.larus.nova')
if len(apk_path.splitlines())!=1 or not apk_path.startswith('package:'):
    raise SystemExit('Unexpected APK layout')
subprocess.run(['docker','cp','doubao-hpe14-13-test:'+apk_path.removeprefix('package:'),str(root/'doubao-15.2.0.apk')],check=True)
print(run('docker','volume','create',volume))
print(run('docker','run','-d','--name',name,'--restart','unless-stopped','--privileged','--cpus','2','--memory','3g',
    '-p','127.0.0.1:5558:5555','-v',volume+':/data','doubao/redroid:13-hpe14-com1.3',
    'ro.enable.native.bridge.exec64=1','ro.dalvik.vm.native.bridge=libhoudini.so','androidboot.use_memfd=1',
    'androidboot.redroid_gpu_mode=guest','androidboot.redroid_width=720','androidboot.redroid_height=1280',
    'androidboot.redroid_dpi=320','androidboot.redroid_net_ndns=2','androidboot.redroid_net_dns1=223.5.5.5',
    'androidboot.redroid_net_dns2=119.29.29.29'))
