from pathlib import Path
import subprocess,re,json,html
from urllib.parse import unquote,urlsplit,parse_qsl
for n in (3,4):
 c=f'doubao-hpe14-account{n}';r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict')
 payload=json.loads(next((r/'outbox').glob('*.json')).read_text())['payload'];s=subprocess.check_output(['docker','exec',c,'logcat','-d','-t','4000'],text=True,errors='replace')
 for i in range(2):s=unquote(s)
 for i,item in enumerate(payload['items'],1):
  url=item['url'];hits=[line for line in s.splitlines() if url in line]
  if hits:print(n,i,'url log hits',len(hits),[l[:110] for l in hits[-2:]])
 print(n,'activities',subprocess.check_output(['docker','exec',c,'dumpsys','activity','activities'],text=True,errors='replace').split('mResumedActivity')[-1][:120])
 print(n,'devtools', [l.split()[-1] for l in subprocess.check_output(['docker','exec',c,'cat','/proc/net/unix'],text=True).splitlines() if 'devtools_remote' in l][-10:])
