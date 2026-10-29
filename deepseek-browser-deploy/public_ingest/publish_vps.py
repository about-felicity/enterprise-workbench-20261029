import sys
from pathlib import Path
sys.path.insert(0,'/tmp')
from vps_geo_access import vps_python
block=Path('/tmp/ds-public-nginx-location.conf').read_text(encoding='utf-8-sig');code=Path('/tmp/ds-public-configure-vps.py').read_text(encoding='utf-8-sig')
print(vps_python('from pathlib import Path\nPath("/tmp/deepseek-ingest-location.conf").write_text('+repr(block)+')\n'+code))
