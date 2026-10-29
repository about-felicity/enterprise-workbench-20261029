"""Read-only rendered DOM diagnosis on the original browser profile."""
import os,sys,time,json
from pathlib import Path
B=Path('/opt/monitor/geo-capture');D=B/'maintenance/20261023-wenxin-start'
R=B/'batches'/('geo-panel-baidu-ai-20261022-090004-2041e20f' if '--previous-profile' in sys.argv else 'geo-panel-baidu-ai-20261023-090003-1a1735de')
label='previous-' if '--previous-profile' in sys.argv else ''
os.environ['GEO_COLLECTOR_RUNTIME']=str(R/'collector')
sys.path.insert(0,str(B))
from geo_source_cards import cli
from geo_source_cards.runtime import process_lock,atomic_json
from wenxin_monitor.controller import BAIDU_AI_SNAPSHOT_JS
with process_lock(B/'search_browser.lock',blocking=True):
 c=cli.create_collector('baidu_ai');rate=B/'search_last_start.json'
 try:
  cli.wait_for_search_slot(rate,60)
  try:result=cli.collect_with_completion_fence(c,'baidu_ai','推荐一款染发剂',rate)
  except Exception as e:result={'error':str(e)}
  atomic_json(D/(label+'probe-result.json'),result)
  for i in range(3):
   c.page.evaluate('window.scrollTo(0,document.body.scrollHeight*'+str(i/2)+')')
   time.sleep(3)
   snap=c.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
   details=c.page.evaluate(r'''(()=>({url:location.href,ready:document.readyState,aiEntries:[...document.querySelectorAll('.ai-entry')].map(e=>({tag:e.tagName,cls:e.className,ancestors:[...function*(x){for(let i=0;x&&i<5;i++,x=x.parentElement)yield {tag:x.tagName,id:x.id,cls:x.className,tpl:x.getAttribute('tpl')}}(e)],text:e.innerText.slice(0,250)})),markdown:document.querySelectorAll('.cosd-markdown-content').length,templates:[...document.querySelectorAll('[tpl]')].map(e=>({tpl:e.getAttribute('tpl'),id:e.id,cls:e.className,text:e.innerText.slice(0,80)})),text:document.body.innerText.slice(-12000)}))()''')
   atomic_json(D/f'{label}probe-dom-{i}.json',{'snapshot':snap,'details':details})
  (D/(label+'probe.html')).write_text(c.page.page.content())
  c.page.page.screenshot(path=str(D/(label+'probe.png')),full_page=True)
  print(json.dumps({'result':{k:v for k,v in result.items() if k not in ('absence_evidence','sources','body','page_body')},'snapshot':snap,'details':details},ensure_ascii=False),flush=True)
 finally:c.close()
