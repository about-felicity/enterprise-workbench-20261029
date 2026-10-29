"""Build and self-test a reversible account2-only MappingFile open workaround."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from pathlib import Path
import subprocess, struct, hashlib, json, os
from elftools.elf.elffile import ELFFile
os.umask(0o077)
base=Path('/home/user/redroid-doubao/account2')
asm=Path('/home/user/redroid-doubao/keva_openat_workaround.S')
c='doubao-hpe14-account2'
def run(*args): subprocess.run(args,check=True)
run('aarch64-linux-gnu-as',str(asm),'-o',str(base/'workaround.o'))
run('aarch64-linux-gnu-ld','-Ttext=0x5ec00','--defsym=original_open=0x20230','--defsym=get_errno=0x20610',str(base/'workaround.o'),'-o',str(base/'workaround.elf'))
run('aarch64-linux-gnu-objcopy','-O','binary','--only-section=.text',str(base/'workaround.elf'),str(base/'workaround.bin'))
code=(base/'workaround.bin').read_bytes()
original=(base/'libkeva.so').read_bytes()
data=bytearray(original)
assert struct.unpack_from('<I',data,0x32904)[0]==0x97ffb64b
assert len(code)<0x400 and not any(data[0x5ec00:0x5ec00+len(code)])
data[0x5ec00:0x5ec00+len(code)]=code
struct.pack_into('<I',data,0x32904,0x94000000|((0x5ec00-0x32904)//4))
with (base/'libkeva.so').open('rb') as f:
    e=ELFFile(f)
    first=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD')
    assert first['p_offset']==0 and first['p_vaddr']==0 and first['p_filesz']==0x5eb88
    ph=e['e_phoff']
struct.pack_into('<QQ',data,ph+32,0x5f000,0x5f000)
(base/'libkeva-openat.so').write_bytes(data)
# Test the exact wrapper code on Houdini, without loading or altering the App.
directory='/data/local/tmp/keva-openat-test/'+('d'*111)
run('docker','exec',c,'mkdir','-p',directory)
test='.global original_open, get_errno\n.global _start\n.text\n_start:\n'
for suffix in ('.blk','.chk'):
    test+='adr x0, path_'+suffix[1:]+'\nmov x1, #66\nmov x2, #384\nbl keva_open\ncmp x0, #0\nb.lt failed\nmov x8, #57\nsvc #0\n'
test+='mov x0, #0\nb exit\nfailed:\nmov x0, #1\nexit:\nmov x8, #94\nsvc #0\noriginal_open:\nmov x3, x2\nmov x2, x1\nmov x1, x0\nmov x0, #-100\nmov x8, #56\nsvc #0\nret\nget_errno:\nadr x0, err\nret\n'
for suffix in ('.blk','.chk'):
    test+='path_'+suffix[1:]+':\n.asciz '+json.dumps(directory+'/'+('f'*111)+suffix)+'\n'
test+='.balign 8\nerr: .quad 0\n'
(base/'workaround-test.S').write_text(test)
run('aarch64-linux-gnu-as',str(base/'workaround-test.S'),'-o',str(base/'workaround-test.o'))
run('aarch64-linux-gnu-ld','-pie','--dynamic-linker','/system/bin/linker64',str(base/'workaround-test.o'),str(base/'workaround.o'),'-o',str(base/'workaround-test'))
run('docker','cp',str(base/'workaround-test'),c+':/data/local/tmp/keva-openat-test/test')
run('docker','exec',c,'chmod','755','/data/local/tmp/keva-openat-test/test')
run('docker','exec',c,'/system/bin/houdini64','/data/local/tmp/keva-openat-test/test')
files=subprocess.check_output(['docker','exec',c,'find',directory,'-type','f'],text=True).splitlines()
assert set(files)=={directory+'/'+('f'*111)+s for s in ('.blk','.chk')},files
report={'original_sha256':hashlib.sha256(original).hexdigest(),'patched_sha256':hashlib.sha256(data).hexdigest(),'callsite':'0x32904','wrapper':'0x5ec00','wrapper_bytes':len(code),'test_path_length':len(files[0]),'distinct_full_files':len(files)}
(base/'workaround-build.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))

