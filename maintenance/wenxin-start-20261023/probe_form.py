"""Compare the site's normal search form against direct URL navigation."""
import os,sys,time,json
from pathlib import Path
B=Path('/opt/monitor/geo-capture');D=B/'maintenance/20261023-wenxin-start';R=B/'batches/geo-panel-baidu-ai-20261023-090003-1a1735de'
os.environ['GEO_COLLECTOR_RUNTIME']=str(R/'collector')
sys.path.insert(0,str(B))
from geo_source_cards import cli
from geo_source_cards.runtime import process_lock,atomic_json
from wenxin_monitor.controller import BAIDU_AI_SNAPSHOT_JS
with process_lock(B/'search_browser.lock',blocking=True):
 c=cli.create_collector('baidu_ai');rate=B/'search_last_start.json'
 try:
  c.page.call('Page.navigate',{'url':c.HOME});time.sleep(3)
  fields=c.page.evaluate(r'''(()=>({inputs:[...document.querySelectorAll('input,textarea,[contenteditable=true]')].map(e=>({tag:e.tagName,id:e.id,cls:e.className,placeholder:e.getAttribute('placeholder'),visible:!!e.getBoundingClientRect().height})),buttons:[...document.querySelectorAll('button,input[type=submit],[role=button]')].map(e=>({tag:e.tagName,id:e.id,cls:e.className,text:e.innerText||e.value,visible:!!e.getBoundingClientRect().height}))}))()''')
  atomic_json(D/'home-fields.json',fields);print(json.dumps(fields,ensure_ascii=False),flush=True)
  cli.wait_for_search_slot(rate,60)
  field=next(e for e in fields['inputs'] if e['visible'] and e['tag'] in ('INPUT','TEXTAREA') and e['id'])
  c.page.page.locator('#'+field['id']).fill('推荐一款染发剂',timeout=10000)
  c.page.page.locator('#'+field['id']).press('Enter',timeout=10000)
  c.page.page.wait_for_load_state('domcontentloaded',timeout=45000)
  for i in range(4):
   time.sleep(5)
   c.page.evaluate(f'window.scrollTo(0,{i*650})')
   snap=c.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
   details=c.page.evaluate(r'''(()=>({url:location.href,aiEntries:document.querySelectorAll('.ai-entry').length,markdown:document.querySelectorAll('.cosd-markdown-content').length,cardCandidates:[...document.querySelectorAll('[tpl]')].map(e=>({tpl:e.getAttribute('tpl'),text:e.innerText.slice(0,100)}))}))()''')
   atomic_json(D/f'form-dom-{i}.json',{'snapshot':snap,'details':details})
  (D/'form-probe.html').write_text(c.page.page.content())
  c.page.page.screenshot(path=str(D/'form-probe.png'),full_page=True)
  print(json.dumps({'snapshot':snap,'details':details},ensure_ascii=False),flush=True)
 finally:
  atomic_json(rate,{'last_search_epoch':time.time(),'fence':'diagnostic_search_finished'})
  c.close()
