import subprocess,json,re
raw=subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','cat','/data/tombstones/tombstone_31'],timeout=20).decode(errors='replace')
lines=[]
for line in raw.splitlines():
    if re.match(r'^(Timestamp:|Cmdline:|signal |Cause:)',line) or re.match(r'\s*#\d+ pc ',line):lines.append(line)
print(json.dumps({'crash_metadata':lines[:40]}))
