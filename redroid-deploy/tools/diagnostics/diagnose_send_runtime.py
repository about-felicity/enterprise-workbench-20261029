"""Read-only runtime comparison; omit credentials and raw app storage."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess, json, re, collections

def run(*args):
    return subprocess.check_output(args, text=True, errors='replace', timeout=20).strip()

for name in ('doubao-hpe14-13-test', 'doubao-hpe14-account2'):
    def android(*args):
        return run('docker', 'exec', name, *args)
    info=json.loads(run('docker','inspect',name))[0]
    for line in android('dumpsys','connectivity').splitlines():
        if 'NetworkAgentInfo{' in line:
            print(name, line.strip())
    for key in ('captive_portal_mode','captive_portal_http_url','captive_portal_https_url','private_dns_mode'):
        print(name,key,android('settings','get','global',key))
    print(json.dumps({'container':name,'args':info['Args'],'oom':info['State']['OOMKilled'],
        'date':android('date','-u'), 'android_id':android('settings','get','secure','android_id'),
        'serial':android('getprop','ro.serialno')},ensure_ascii=False))
    if name.endswith('account2'):
        logs=android('logcat','-d','-t','4000','-v','brief')
        tags=collections.Counter(re.findall(r'^[VDIWEF]/([^ (]+)', logs, re.M))
        print('tags',tags.most_common(25))
        for line in logs.splitlines():
            if re.search(r'(?i)(send.*(fail|error)|auth.*(fail|error)|unauthoriz|SSLHandshake|certificate|connection.*(refused|reset|timed)|UnknownHost|network.*(error|fail))',line):
                line=re.sub(r'https?://\S+','[URL]',line)
                line=re.sub(r'(?i)(token|cookie|authorization|sessionid)[=: ]+\S+',r'\1=[REDACTED]',line)
                print(line[:600])
