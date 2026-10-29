"""Read-only class/method metadata and conversation sync code from official APK."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import zipfile,sys
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
apk='/home/user/redroid-doubao/account2/doubao-15.2.0.apk'
with zipfile.ZipFile(apk) as z:
    for name in ('classes22.dex','classes24.dex'):
        d=DEX(z.read(name))
        for cls in d.get_classes():
            if cls.get_name().startswith('Lcom/larus/im/') and any(s.lower() in cls.get_name().lower() for s in ('conversation','Omni','ImService','Session','Sync')):
                if len(sys.argv)==1:
                    print(cls.get_name(),[(m.get_name(),m.get_descriptor()) for m in cls.get_methods() if any(s in m.get_name().lower() for s in ('sync','pull','init','native','conversation'))][:40])
                elif sys.argv[1] in cls.get_name():
                    for m in cls.get_methods():
                        print(m.get_class_name(),m.get_name(),m.get_descriptor())
                        if m.get_code():
                            for ins in m.get_instructions():print(ins.get_name(),ins.get_output())
