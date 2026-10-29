import collections
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
def sql(query):
 return subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query],text=True,timeout=40).strip()
before=json.loads((ROOT/'today-before.json').read_text())
after=json.loads(sql("select coalesce(json_agg(t),'[]') from (select model_id,run_id,answer,payload->>'product_review_status' review from monitor_runs where day='2026-10-17')t"))
keyed={(r['model_id'],r['run_id']):r for r in after}
unrelated=0;clean=0;tokens=collections.Counter()
for row in before:
 found=keyed[(row['model_id'],row['run_id'])]
 if row['model_id']!='yuanbao':
  assert found['answer']==row['answer'];unrelated+=1
 else:
  assert '@mark_underline' not in found['answer'] and '@replace' not in found['answer'];clean+=1
 tokens.update(re.findall(r'@([A-Za-z_0-9]+)(?=[=&])',found['answer'] or ''))
params=urllib.parse.urlencode({'question':'眉毛增长液推荐','date':'2026-10-17','model':'yuanbao','view':'overview'})
with urllib.request.urlopen('http://127.0.0.1:8765/api/analytics?'+params,timeout=60) as response:analytics=json.load(response)
board=analytics.get('owned_product_daily') or analytics.get('data',{}).get('owned_product_daily') or []
report={'unrelated_model_bodies_unchanged':unrelated,'today_yuanbao_cleaned':clean,
 'remaining_internal_token_types':tokens,'board':board,'api_keys':list(analytics)}
(ROOT/'projection-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
