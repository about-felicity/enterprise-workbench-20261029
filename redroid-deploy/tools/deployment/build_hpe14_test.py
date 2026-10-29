
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
#!/usr/bin/env python3
import pathlib,tarfile,hashlib,subprocess,json,shutil
root=pathlib.Path('/home/user/redroid-doubao'); archive=root/'houdini-hpe14.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b945959d027128f98a4f1913b84337ab6b415852ed3b350570f38b71fbfb864d'
work=root/'hpe14-build'; work.mkdir(exist_ok=True)
with tarfile.open(archive) as t:
 for m in t.getmembers():
  bits=pathlib.PurePosixPath(m.name).parts
  if len(bits)<3 or bits[1]!='prebuilts' or not m.isfile():continue
  dest=work/'system'/pathlib.Path(*bits[2:])
  assert dest.resolve().is_relative_to(work.resolve())
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(t.extractfile(m).read());dest.chmod(0o755 if bits[2]=='bin' else 0o644)
(work/'Dockerfile').write_text('FROM erstt/redroid:15.0.0_ndk_AVD\nCOPY system/ /system/\n')
subprocess.run(['docker','build','--network=none','-t','doubao/redroid:15-hpe14-com1.3',str(work)],check=True)
orig='doubao-redroid-redroid-1'; vol='doubao-hpe14-android15-data'
if subprocess.run(['docker','volume','inspect',vol],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
 subprocess.run(['docker','volume','create',vol],check=True)
 info=json.loads(subprocess.check_output(['docker','inspect',orig]))[0]
 src=next(x['Source'] for x in info['Mounts'] if x['Destination']=='/data')
 dst=json.loads(subprocess.check_output(['docker','volume','inspect',vol]))[0]['Mountpoint']
 subprocess.run(['docker','stop','-t','20',orig],check=True)
 try: subprocess.run(['cp','-a',src+'/.',dst+'/'],check=True)
 finally:subprocess.run(['docker','start',orig],check=True)
if subprocess.run(['docker','inspect','doubao-hpe14-test'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
 subprocess.run(['docker','run','-d','--name','doubao-hpe14-test','--privileged','--cpus','2','--memory','3g','-p','127.0.0.1:5556:5555','-v',vol+':/data','doubao/redroid:15-hpe14-com1.3','ro.enable.native.bridge.exec64=1','ro.dalvik.vm.native.bridge=libhoudini.so','androidboot.use_memfd=1','androidboot.redroid_gpu_mode=guest','androidboot.redroid_width=720','androidboot.redroid_height=1280','androidboot.redroid_dpi=320','androidboot.redroid_net_ndns=2','androidboot.redroid_net_dns1=223.5.5.5','androidboot.redroid_net_dns2=119.29.29.29'],check=True)
print('Test environment built; original volume preserved.')
