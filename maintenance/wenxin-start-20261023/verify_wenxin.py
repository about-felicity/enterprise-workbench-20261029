"""Read-only live verification of Wenxin; not a daily-task completion receipt."""
import sys,time,json
from pathlib import Path
B=Path('/opt/monitor/geo-capture');D=B/'maintenance/20261023-wenxin-start'
sys.path.insert(0,str(B))
from geo_source_cards import cli
from geo_source_cards.runtime import process_lock,atomic_json
from wenxin_monitor.controller import WenxinWebCollector
source=B/'batches/geo-panel-wenxin-card-20261022-111529-d2ac1183/collector/profiles/baidu/scrapling_profile'
with process_lock(D/'wenxin-diagnostic.lock',blocking=True):
 c=WenxinWebCollector(profile=source);rate=B/'search_last_start.json'
 try:
  cli.wait_for_search_slot(rate,60)
  value=cli.collect_with_completion_fence(c,'wenxin_card','推荐一款染发剂',rate)
  atomic_json(D/'wenxin-live-result.json',{'at':time.time(),'diagnostic_only':True,'daily_count_not_modified':True,'result':value})
  c.page.page.screenshot(path=str(D/'wenxin-live.png'),full_page=True)
  print(json.dumps({k:v for k,v in value.items() if k not in ('body','page_body','sources','citations','source_entries')},ensure_ascii=False),flush=True)
 finally:c.close()
