import json,re,subprocess
from pathlib import Path
from urllib.parse import urlsplit
base=Path('/home/user/redroid-yuanbao/diagnostics/wechat-after-scan-20261015')
raw=subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','logcat','-d','-t','25000'],timeout=30)
(base/'latest-private.txt').write_bytes(raw);(base/'latest-private.txt').chmod(0o600)
routes=set()
for source in [base/'logcat-private.txt',base/'latest-private.txt']:
    for line in source.read_text(errors='replace').splitlines():
        if not any(x in line.lower() for x in ['webactivity','loadurl','login','face','verify','security']):continue
        for match in re.finditer(r'(?:https?|weixin)://[^\s<>"\x27]+',line):
            try:
                u=urlsplit(match[0]);host=u.hostname or ''
                # Never print query values, authorization IDs or long path tokens.
                path='/'.join(p if len(p)<32 and not re.search(r'[0-9]{6}',p) else '[redacted]' for p in u.path.split('/'))
                routes.add((u.scheme,host,path))
            except ValueError:pass
print(json.dumps({'routes':[{'scheme':s,'host':h,'path':p} for s,h,p in sorted(routes)]}))
crashes=[]
for line in raw.decode(errors='replace').splitlines():
    if any(x in line for x in ['FATAL EXCEPTION','Fatal signal','ANR in com.tencent.hunyuan','Process com.tencent.hunyuan.app.chat (pid']):
        kind='java_fatal' if 'FATAL EXCEPTION' in line else 'native_fatal' if 'Fatal signal' in line else 'anr' if 'ANR in' in line else 'app_exit'
        crashes.append({'time':line[:18],'kind':kind})
print(json.dumps({'process_events':crashes[-20:]}))
