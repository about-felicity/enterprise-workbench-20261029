import hashlib,json
from pathlib import Path
D=Path(__file__).parent;W=D.parents[1]
mapping={'geo-monitor-deploy/wenxin_retry.py':'/opt/monitor/geo-capture/wenxin_retry.py','geo-monitor-deploy/wenxin_readiness_probe.py':'/opt/monitor/geo-capture/wenxin_readiness_probe.py','geo-monitor-deploy/systemd/geo-wenxin-retry.service':'/etc/systemd/system/geo-wenxin-retry.service','geo-monitor-deploy/systemd/geo-wenxin-retry.timer':'/etc/systemd/system/geo-wenxin-retry.timer'}
(D/'verification/release.json').write_text(json.dumps({'files':[{'source':s,'server':p,'sha256':hashlib.sha256((W/s).read_bytes()).hexdigest()} for s,p in mapping.items()]},indent=2))
