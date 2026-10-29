"""Credential-free ARM64 syscall probe, isolated to account2 /data/local/tmp."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import struct, subprocess, json, os
from pathlib import Path
os.umask(0o077)
c='doubao-hpe14-account2'
base=Path('/home/user/redroid-doubao/account2/path-probe')
base.mkdir(exist_ok=True)
def elf(path):
    assembly='.global _start\n.text\n_start:\n mov x0, #-100\n adr x1, pathname\n mov x2, #66\n mov x3, #384\n mov x8, #56\n svc #0\n mov x0, #0\n mov x8, #94\n svc #0\npathname:\n.asciz '+json.dumps(path)+'\n'
    (base/'probe.s').write_text(assembly)
    subprocess.run(['aarch64-linux-gnu-as',str(base/'probe.s'),'-o',str(base/'probe.o')],check=True)
    subprocess.run(['aarch64-linux-gnu-ld','-pie','--dynamic-linker','/system/bin/linker64',str(base/'probe.o'),'-o',str(base/'probe.elf')],check=True)
    return (base/'probe.elf').read_bytes()
for length in (240,255,256,270):
    directory='/data/local/tmp/path-probe/'+('d'*100)
    stem='f'*(length-len(directory)-1-4)
    subprocess.run(['docker','exec',c,'mkdir','-p',directory],check=True)
    for suffix in ('.blk','.chk'):
        path=directory+'/'+stem+suffix
        p=base/('probe-'+str(length)+suffix)
        p.write_bytes(elf(path)); p.chmod(0o755)
        subprocess.run(['docker','cp',str(p),c+':/data/local/tmp/path-probe/probe'],check=True)
        result=subprocess.run(['docker','exec',c,'/system/bin/houdini64','/data/local/tmp/path-probe/probe'],capture_output=True,text=True,timeout=10)
        print(json.dumps({'input_length':len(path),'suffix':suffix,'exit':result.returncode,'output':result.stdout[:100],'error':result.stderr[:200]}),flush=True)
out=subprocess.check_output(['docker','exec',c,'find','/data/local/tmp/path-probe','-type','f'],text=True)
print('created',[(len(p),len(Path(p).name),Path(p).suffix) for p in out.splitlines()])
init=json.loads(subprocess.check_output(['docker','inspect',c]))[0]['State']['Pid']
trace=base/'syscall.trace'
subprocess.run(['strace','-f','-s','1024','-e','trace=openat','-o',str(trace),
    'nsenter','-t',str(init),'-m','-p','-r','-w','/system/bin/houdini64','/data/local/tmp/path-probe/probe'],check=True,timeout=10)
for line in trace.read_text().splitlines():
    if '/data/local/tmp/path-probe/' in line: print('syscall',line)
subprocess.run(['docker','exec',c,'touch',path],check=True)
out=subprocess.check_output(['docker','exec',c,'find','/data/local/tmp/path-probe','-type','f'],text=True)
print('native_x86_full_path_exists',path in out.splitlines())



