"""Verify Chinese browser context and network language before changing production."""
import os,sys,time,json
from pathlib import Path
from unittest.mock import patch
B=Path('/opt/monitor/geo-capture');D=B/'maintenance/20261023-wenxin-start';R=B/'batches/geo-panel-baidu-ai-20261023-090003-1a1735de'
os.environ['GEO_COLLECTOR_RUNTIME']=str(R/'collector');sys.path.insert(0,str(B))
from geo_source_cards import cli
from geo_source_cards.runtime import process_lock,atomic_json
from wenxin_monitor.controller import BAIDU_AI_SNAPSHOT_JS
from scrapling.fetchers import StealthySession
with process_lock(B/'search_browser.lock',blocking=True):
 with patch('scrapling.fetchers.StealthySession',side_effect=lambda **kw:StealthySession(**{**kw,'additional_args':{'locale':'zh-CN'}})):
  c=cli.create_collector('baidu_ai')
 rate=B/'search_last_start.json'
 try:
  language=c.page.evaluate('({language:navigator.language,languages:navigator.languages,locale:Intl.DateTimeFormat().resolvedOptions().locale,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})')
  print(json.dumps({'browser_language':language},ensure_ascii=False),flush=True)
  cli.wait_for_search_slot(rate,60)
  try:result=cli.collect_with_completion_fence(c,'baidu_ai','推荐一款染发剂',rate)
  except Exception as e:result={'error':str(e)}
  atomic_json(D/'locale-result.json',{'language':language,'result':result})
  (D/'locale-probe.html').write_text(c.page.page.content())
  c.page.page.screenshot(path=str(D/'locale-probe.png'),full_page=True)
  s=c.page.evaluate(BAIDU_AI_SNAPSHOT_JS);print(json.dumps({'language':language,'snapshot':s,'result':{k:v for k,v in result.items() if k not in ('body','sources','absence_evidence')}},ensure_ascii=False),flush=True)
 finally:c.close()
