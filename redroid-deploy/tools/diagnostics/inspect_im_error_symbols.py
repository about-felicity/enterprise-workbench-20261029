"""Inspect shipped error strings, without reading user data or changing APK."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import zipfile,re
apk='/home/user/redroid-doubao/account2/doubao-15.2.0.apk'
with zipfile.ZipFile(apk) as z:
    print('native_libraries',[n for n in z.namelist() if n.endswith('.so') and re.search('im|omni|chat',n,re.I)])
    for n in z.namelist():
        if not re.fullmatch(r'classes\d*\.dex',n):continue
        raw=z.read(n)
        matches=set()
        for s in re.findall(rb'[ -~]{8,250}',raw):
            text=s.decode()
            if re.search(r'Lcom/(?:larus/(?:im|chat)|bytedance/(?:im|omni))[^;]*(?:Error|Exception)[^;]*;',text):matches.add(text)
        if matches:print(n,sorted(matches))
    raw=z.read('lib/arm64-v8a/libomnisdk.so')
    matches=set()
    for s in re.findall(rb'[ -~]{8,240}',raw):
        t=s.decode()
        if re.search(r'(?i)(not initialized|im.*init.*fail|sdk.*not.*init|imerror|im_error|IM_NOT|IM_SDK_NOT)',t):matches.add(t)
    print('native_error_strings',sorted(matches)[:100])
