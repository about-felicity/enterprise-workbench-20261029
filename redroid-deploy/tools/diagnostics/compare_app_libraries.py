
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,collections,re
def run(*args): return subprocess.check_output(args,text=True,errors='replace',timeout=20).strip()
sets=[]
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    pid=run('docker','exec',name,'pidof','com.larus.nova')
    maps=run('docker','exec',name,'cat','/proc/'+pid+'/maps')
    libs=set(re.findall(r'/([^/\s]+\.so)(?:\s|$)',maps))
    sets.append(libs)
    print(name,'library_count',len(libs))
    logs=run('docker','exec',name,'logcat','-d','--pid='+pid,'-t','1500','-v','brief')
    for line in logs.splitlines():
        if re.search(r'(?i)(dlopen failed|cannot locate symbol|UnsatisfiedLink|exception|Connect failed|native loader)',line):
            line=re.sub(r'https?://\S+','[URL]',line)
            if re.search(r'(?i)token|cookie|authorization',line): continue
            print(line[:350])
print('only_first',sorted(sets[0]-sets[1]))
print('only_second',sorted(sets[1]-sets[0]))
