
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from pathlib import Path
import sys
p=Path('/home/user/redroid-doubao/account2/libkeva.so')
with p.open('rb') as f:
    elf=ELFFile(f);data=p.read_bytes();cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    symbols=elf.get_section_by_name('.dynsym')
    for s in symbols.iter_symbols():
        if any(x in s.name for x in ('KevaBlockFileC2','KevaChunkFileC2','StringPrintf','StringFormat','PrintFormat')):
            a=s['st_value'];print('FUNCTION',s.name,hex(a),s['st_size'])
            for i in cs.disasm(data[a:a+s['st_size']],a):print(hex(i.address),i.mnemonic,i.op_str)
    if len(sys.argv)>1:
        a=int(sys.argv[1],16);size=int(sys.argv[2],16)
        for i in cs.disasm(data[a:a+size],a):print(hex(i.address),i.mnemonic,i.op_str)
