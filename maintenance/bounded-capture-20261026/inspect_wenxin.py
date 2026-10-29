import json,time
from pathlib import Path
from wenxin_monitor.controller import ScraplingStealthPage,WENXIN_SEARCH_SNAPSHOT_JS
from geo_source_cards.runtime import process_lock
root=Path('/opt/monitor/geo-content/studio/capture/plan-29b4419dda224fbd913ae1d9a385497e')
out=Path('/tmp/wenxin-inspection');out.mkdir(exist_ok=True)
with process_lock(root/'profiles/search/wenxin_card/browser.lock'):
 p=ScraplingStealthPage(root/'profiles/search/wenxin_card/scrapling_profile')
 try:
  for ident in ['8778482832223612206','9763825690304271987','9098643275349346774']:
   p.call('Page.navigate',{'url':'https://wenxin.baidu.com/search/'+ident+'?enter_type=unknown'})
   time.sleep(8)
   v=p.evaluate(WENXIN_SEARCH_SNAPSHOT_JS)
   (out/(ident+'.json')).write_text(json.dumps(v,ensure_ascii=False))
   (out/(ident+'.html')).write_text(p.page.content())
   print(json.dumps({'id':ident,'url':v.get('url'),'text':p.page.inner_text('body')[-12000:],'sources':v.get('sources')},ensure_ascii=False),flush=True)
 finally:p.close()
