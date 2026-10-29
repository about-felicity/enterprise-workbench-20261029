import base64,json,re
from pathlib import Path
import requests
source=Path('/opt/monitor/yuanbao_monitor/dashboard/app/ModelIcon.tsx').read_text()
logos={}
for name,key in [('DeepSeek','deepseek'),('Doubao','doubao'),('Wenxin','wenxin_card'),('Yuanbao','yuanbao')]:
 section=source.split('export function '+name+'Icon',1)[1].split('</IconFrame>',1)[0]
 inner=re.search(r'<IconFrame[^>]*>(.*)',section,re.S).group(1)
 svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'+inner.replace('stopColor','stop-color')+'</svg>'
 logos[key]='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
r=requests.get('https://www.baidu.com/favicon.ico',timeout=20);r.raise_for_status()
assert r.content[:4] in (b'\x00\x00\x01\x00',b'\x89PNG')
logos['baidu_ai']='data:image/x-icon;base64,'+base64.b64encode(r.content).decode()
Path('/tmp/geo-model-logos.json').write_text(json.dumps(logos,ensure_ascii=False))
print(json.dumps({'logos':list(logos),'baidu_asset_bytes':len(r.content)}))
