"""Read-only live UI QA. All browser writes are intercepted before reaching API."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright

port=int(sys.argv[1]) if len(sys.argv)>1 else 3001
base=f'http://127.0.0.1:{port}'
root=Path('/opt/monitor/geo-content/maintenance/20261016-creation-studio')
report={'passed':False,'port':port}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1500,'height':1000})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 panel=context.request.get(base+'/api/geo-creation/panel').json()
 catalog=context.request.get(base+'/api/geo-creation/catalog').json()
 assert len(catalog['dedicated']['questions'])==16
 assert panel['materials']['settings']['time']=='01:00'
 assert panel['materials']['settings']['start_date']=='2026-10-17'
 assert panel['materials']['geo_ingest_enabled'] is False
 all_articles=[(j['job_id'],a) for j in panel['jobs'] for a in j['articles']]+[('legacy-original',a) for a in panel['legacy_articles']]
 assert len(all_articles)>=94 and len(panel['legacy_articles'])==82
 page.goto(base+'/api/geo-creation/ui');page.wait_for_function("document.querySelector('#totalArticles').textContent==='"+str(len(all_articles))+"' && document.querySelector('#question').options.length===16")
 assert page.locator('#source').input_value()=='dedicated'
 assert not page.locator('#retryAction').is_visible()
 assert page.locator('#materialTime').input_value()=='01:00'
 assert len(page.locator('#materialQuestions').input_value().splitlines())==16
 page.locator('.preview').first.click();page.wait_for_function("document.querySelector('#previewText').textContent.length>200")
 assert page.locator('#preview').evaluate('(e)=>e.open')
 page.get_by_role('button',name='关闭',exact=True).click()
 page.locator('#outputFilter').select_option('legacy-original');assert page.locator('.output').count()==82
 page.locator('#search').fill('__no_such_article__');assert page.locator('.output').count()==0
 page.locator('#search').fill('');page.locator('#outputFilter').select_option('all')
 page.locator('#source').select_option('geo');assert page.locator('#question option').count()==len(catalog['geo']['questions'])
 page.locator('#source').select_option('dedicated')
 writes=[]
 def intercept(route):
  if route.request.method=='POST':
   writes.append({'path':route.request.url.split('/control/')[-1],'body':route.request.post_data_json})
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'result':{'message':'QA intercepted'}}))
  else:route.continue_()
 page.route('**/api/geo-creation/control/**',intercept)
 page.locator('#new').click();page.wait_for_function("!document.querySelector('#new').disabled")
 assert writes[-1]['path']=='new' and writes[-1]['body']['material_source']=='dedicated'
 assert writes[-1]['body']['product']['facts']==catalog['product']['facts']
 page.locator('#materialSave').click();page.wait_for_function("!document.querySelector('#materialSave').disabled")
 assert writes[-1]['path']=='materials_settings' and writes[-1]['body']['time']=='01:00' and len(writes[-1]['body']['questions'])==16
 page.locator('#materialPause').click();page.wait_for_function("!document.querySelector('#materialPause').disabled")
 page.locator('#materialResume').click();page.wait_for_function("!document.querySelector('#materialResume').disabled")
 assert [w['path'] for w in writes]==['new','materials_settings','materials_pause','materials_resume']
 for width in [1500,1280,390]:
  page.set_viewport_size({'width':width,'height':1000});page.evaluate('window.scrollTo(0,0)')
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),width
  page.screenshot(path=str(root/f'ui-{port}-{width}.png'),full_page=True)
 assert not errors,errors
 bundle=context.request.get(base+'/api/geo-creation/download?job=all-approved&kind=bundle')
 assert bundle.ok and hashlib.sha256(bundle.body()).hexdigest()==bundle.headers['x-content-sha256']
 archive=zipfile.ZipFile(io.BytesIO(bundle.body()))
 words=[n for n in archive.namelist() if n.endswith('.docx')]
 assert len(words)==len(all_articles)
 bundle_hashes={hashlib.sha256(archive.read(n)).hexdigest() for n in words}
 for identity,a in all_articles:
  response=context.request.get(base+'/api/geo-creation/download?'+urlencode({'job':identity,'article':a['id'],'kind':'word'}))
  assert response.ok
  digest=hashlib.sha256(response.body()).hexdigest()
  assert digest==response.headers['x-content-sha256'] and digest in bundle_hashes
  assert digest==a['receipt']['files']['article.docx']
  assert zipfile.is_zipfile(io.BytesIO(response.body()))
 page.goto(base+'/#creation');frame=page.frame_locator('iframe[title="GEO 内容创作控制台"]')
 # Embedded dashboard uses the same tested source; find its frame without assumptions about title spacing.
 page.wait_for_selector('iframe[src*="geo-creation/ui"]',timeout=30000)
 embedded=page.frame_locator('iframe[src*="geo-creation/ui"]')
 embedded.locator('#totalArticles').get_by_text(str(len(all_articles)),exact=True).wait_for()
 report.update(passed=True,approved_articles=len(all_articles),legacy_articles=82,private_questions=16,time='01:00',writes_intercepted=len(writes),verified_word_downloads=len(all_articles),bundle_entries=len(archive.namelist()),browser_errors=errors)
 browser.close()
(root/('qa-preview.json' if port==3001 else 'qa-production.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
