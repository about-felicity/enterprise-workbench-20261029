import sys
sys.path.insert(0,'/tmp')
from vps_geo_access import vps_python
print(vps_python("from pathlib import Path; s=Path('/etc/nginx/nginx.conf').read_text(); print('\\n'.join(l for l in s.splitlines() if 'geo_monitor' in l or 'http {' in l or 'limit_req_zone' in l)); import socket; x=socket.socket(); print('bridge_port_status', x.connect_ex(('127.0.0.1',18811))); x.close()"))
