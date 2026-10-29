"""Read static IM error constants from the unchanged installed APK's DEX."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import zipfile,struct
def inspect(raw,name):
    def u32(pos):return struct.unpack_from('<I',raw,pos)[0]
    def uleb(pos):
        value=shift=0
        while True:
            b=raw[pos];pos+=1;value|=(b&127)<<shift
            if b<128:return value,pos
            shift+=7
    count,offset=struct.unpack_from('<II',raw,56)
    strings=[]
    for i in range(count):
        pos=u32(offset+i*4);_,pos=uleb(pos)
        strings.append(raw[pos:raw.index(b'\0',pos)].decode('utf-8','replace'))
    count,offset=struct.unpack_from('<II',raw,64)
    types=[strings[u32(offset+i*4)] for i in range(count)]
    count,offset=struct.unpack_from('<II',raw,80)
    fields=[(types[a],types[b],strings[c]) for a,b,c in (struct.unpack_from('<HHI',raw,offset+i*8) for i in range(count))]
    count,offset=struct.unpack_from('<II',raw,96)
    for i in range(count):
        values=struct.unpack_from('<8I',raw,offset+i*32)
        cls=types[values[0]]
        if not (cls.startswith('Lcom/larus/im/') and ('ErrorCode' in cls or 'ErrorConst' in cls)):continue
        print('CLASS',name,cls)
        pos=values[6]
        if not pos:continue
        ns,pos=uleb(pos);ni,pos=uleb(pos);nd,pos=uleb(pos);nv,pos=uleb(pos)
        static=[];idx=0
        for _ in range(ns):
            diff,pos=uleb(pos);access,pos=uleb(pos);idx+=diff
            static.append(fields[idx])
        pos=values[7]
        if not pos:print('no encoded static values');continue
        size,pos=uleb(pos)
        for field in static[:size]:
            head=raw[pos];pos+=1;kind=head&31;length=(head>>5)+1
            if kind in (0,2,3,4,6,16,17,23,24,25,26,27):
                b=raw[pos:pos+length];pos+=length
                value=int.from_bytes(b,'little',signed=kind in (0,2,4,6))
                if kind==23:value=strings[value]
            elif kind==30:value=None
            elif kind==31:value=bool(head>>5)
            else:print('complex encoded value; stopping');break
            print(field[2],value)
with zipfile.ZipFile('/home/user/redroid-doubao/account2/doubao-15.2.0.apk') as z:
    for n in ('classes22.dex','classes24.dex'):
        inspect(z.read(n),n)
