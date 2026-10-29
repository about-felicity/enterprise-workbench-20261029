import io,json,sys,threading,zipfile,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-filters')
preview=len(sys.argv)>1 and sys.argv[1]=='preview'
if preview:
 sys.path[:0]=[str(R/'stage'),'/opt/monitor/geo-content/engine']
 from creation.service import Handler,ThreadingHTTPServer
 server=ThreadingHTTPServer(('127.0.0.1',8805),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+('8805' if preview else '3000')
api='/api/' if preview else '/api/geo-creation/'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route('**/control/**',lambda route:route.abort())
 data=page.request.get(base+api+'panel').json()
 rows=[{**a,'job':j['job_id']} for j in data['jobs'] for a in j['articles']]+[{**a,'job':'legacy-original'} for a in data['legacy_articles']]
 assert len(rows)==94 and all(a.get('date') and a.get('product',{}).get('name') for a in rows)
 page.goto(base+('/' if preview else api+'ui'))
 page.wait_for_function("document.querySelector('#totalArticles').textContent==='94'")
 chosen=next(a for a in rows if a['job']=='legacy-original')
 page.locator('#productFilter').select_option(chosen['product']['id'])
 page.locator('#dateFilter').select_option(chosen['date'])
 page.locator('#outputFilter').select_option('legacy-original')
 expected=[a for a in rows if a['product']['id']==chosen['product']['id'] and a['date']==chosen['date'] and a['job']=='legacy-original']
 assert page.locator('.output').count()==len(expected)
 assert page.locator('#totalArticles').inner_text()==str(len(expected))
 assert page.locator('.job').count()==sum(j['product']['id']==chosen['product']['id'] and j['date']==chosen['date'] for j in data['jobs'])
 page.evaluate('refresh()')
 page.wait_for_function('!refreshing')
 assert page.locator('#dateFilter').input_value()==chosen['date']
 assert page.locator('#productFilter').input_value()==chosen['product']['id']
 href=page.locator('#downloadAll').get_attribute('href')
 response=page.request.get(base+href);assert response.ok
 archive=zipfile.ZipFile(io.BytesIO(response.body()))
 words=[n for n in archive.namelist() if n.endswith('.docx')]
 assert len(words)==len(expected)
 assert {hashlib.sha256(archive.read(n)).hexdigest() for n in words}=={a['receipt']['files']['article.docx'] for a in expected}
 page.locator('#search').fill('__no_matching_article__');assert page.locator('.output').count()==0
 assert page.locator('#totalArticles').inner_text()=='0' and page.locator('#downloadAll').get_attribute('href') is None
 page.locator('#clearFilters').click();assert page.locator('.output').count()==94 and page.locator('.job').count()==len(data['jobs'])
 page.locator('#todayFilter').click();today=page.locator('#dateFilter').input_value()
 assert page.locator('.output').count()==sum(a['date']==today for a in rows)
 page.locator('#clearFilters').click()
 for width in [1500,1280,390]:
  page.set_viewport_size({'width':width,'height':1000});page.evaluate('window.scrollTo(0,0)')
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
  page.screenshot(path=str(R/f'{"preview" if preview else "production"}-{width}.png'),full_page=True)
 assert not errors,errors
 browser.close()
report={'passed':True,'articles':len(rows),'filtered_date':chosen['date'],'filtered_count':len(expected),'bundle_words':len(words),'refresh_kept_filters':True,'mobile_overflow':False,'browser_errors':errors,'writes':0}
(R/('qa-preview.json' if preview else 'qa-production.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
