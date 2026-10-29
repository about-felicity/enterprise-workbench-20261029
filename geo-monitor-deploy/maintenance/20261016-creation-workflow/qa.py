"""Staging exercises real APIs on isolated storage; production browser writes are fixtures."""
import base64,copy,io,json,sys,tempfile,threading,zipfile
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-workflow')
preview=len(sys.argv)>1 and sys.argv[1]=='preview';temp=tempfile.TemporaryDirectory()
if preview:
 sys.path[:0]=[str(R/'stage'),'/opt/monitor/geo-content/engine']
 from creation import studio,runtime,materials
 studio.ROOT=Path(temp.name)/'studio';runtime.BASE=Path(temp.name)/'jobs';materials.ROOT=Path(temp.name)/'materials'
 runtime.atomic_json(materials.ROOT/'settings.json',runtime.read('/opt/monitor/geo-content/materials/settings.json'))
 studio.initialize()
 runtime.balance=lambda:(_ for _ in ()).throw(AssertionError('No real paid jobs in UI QA'))
 from creation.service import Handler,ThreadingHTTPServer
 server=ThreadingHTTPServer(('127.0.0.1',8805),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+('8805' if preview else '3000');api='/api/' if preview else '/api/geo-creation/'
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:
 z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>测试知识库规格200ml</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>测试成分说明由用户提供</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 writes=[]
 if preview:
  def proxy(route):
   writes.append(route.request.url.split('/control/')[-1]);r=route.fetch(headers={**route.request.headers,'Origin':'http://127.0.0.1:8804'});route.fulfill(response=r)
  page.route('**/api/control/**',proxy)
 else:
  def fixture(route):
   name=route.request.url.split('/control/')[-1];writes.append(name)
   if name=='kb_import':result={'import_id':'upload-'+'a'*32,'text':'测试知识库规格200ml\n测试成分说明由用户提供','filename':'知识库.docx','paragraphs':2}
   else:result={'message':'UI verification only','product_id':page.evaluate('kbId'),'plan_id':page.evaluate('planId')}
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'result':result}))
  page.route('**/api/geo-creation/control/**',fixture)
 page.goto(base+('/' if preview else api+'ui'));page.wait_for_function("studioLoaded && document.querySelector('#kbName').value.length>0")
 assert page.locator('#planCapture').input_value()=='01:00'
 assert not page.locator('#planEnabled').is_checked()
 assert page.locator('#planQuestions').input_value().count('\n')==15
 assert page.locator('#totalArticles').inner_text()==('82' if preview else '94')
 page.locator('#kbNew').click();page.locator('#kbWord').set_input_files({'name':'知识库.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()})
 page.locator('#kbImport').click();page.wait_for_function("document.querySelector('#kbFacts').value.includes('规格200ml')")
 page.locator('#kbName').fill('UI测试产品');page.locator('#kbBrand').fill('UI测试品牌');page.locator('#kbSave').click();page.wait_for_function('!busy')
 if preview:
  assert page.locator('#kbName').input_value()=='UI测试产品'
  page.locator('#planNew').click();page.locator('#planQuestions').fill('测试问题甲\n测试问题乙')
  tomorrow=(datetime.now(ZoneInfo('Asia/Shanghai')).date()+timedelta(days=1)).isoformat();page.locator('#planStart').fill(tomorrow)
  page.locator('#planWriting').fill('04:30');page.locator('#planEnable').click();page.wait_for_function('!busy')
  st=page.request.get(base+api+'panel').json()['studio'];new=next(v for v in st['plans'] if v['product']['name']=='UI测试产品')
  assert new['enabled'] and new['writing_time']=='04:30' and new['questions']==['测试问题甲','测试问题乙']
  page.locator('#dateFilter').select_option(tomorrow)
  card=page.locator('#dailyCards .job').filter(has=page.get_by_role('heading',name='UI测试产品',exact=True))
  assert card.count()==1
  card.get_by_role('button',name='暂停当日任务').click();page.wait_for_function('!busy');assert '已手动暂停' in card.inner_text()
  card.get_by_role('button',name='继续当日任务').click();page.wait_for_function('!busy');assert '等待定时' in card.inner_text()
  page.evaluate('refresh()');page.wait_for_function('!refreshing');assert page.locator('#planWriting').input_value()=='04:30'
  assert not list(runtime.BASE.glob('runs/*/job.json'))
 else:
  page.evaluate("kbDirty=false;loadKnowledge(data.studio.products[0].product_id);loadPlan(data.studio.plans[0].plan_id)")
  page.locator('#planSave').click();page.wait_for_function('!busy')
  page.locator('#planEnable').click();page.wait_for_function('!busy')
 for width in [1500,1280,390]:
  page.set_viewport_size({'width':width,'height':1000});page.evaluate('window.scrollTo(0,0)')
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
  page.screenshot(path=str(R/f'{"preview" if preview else "production"}-{width}.png'),full_page=True)
 assert not errors,errors
 if not preview:
  page.goto(base+'/#creation');page.wait_for_selector('iframe[src*="geo-creation/ui"]')
  frame=page.frame_locator('iframe[src*="geo-creation/ui"]');frame.locator('#kbWord').wait_for()
  frame.locator('#planSave').wait_for();frame.locator('#dailyMetrics').wait_for()
  assert page.locator('iframe[src*="geo-creation/ui"]').evaluate('(e)=>e.clientHeight')>=2500
 browser.close()
report={'passed':True,'word_import_previewed':True,'knowledge_saved':True,'daily_plan_enabled_in_isolated_staging':preview,'daily_pause_resume_tested':preview,'actual_production_writes':0,'browser_errors':errors,'tested_widths':[1500,1280,390],'actions':writes}
(R/('qa-preview.json' if preview else 'qa-production.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
