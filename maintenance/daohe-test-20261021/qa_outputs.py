"""Exercise actual trial downloads; never count held drafts as deliverables."""
import asyncio, json, sys, zipfile, hashlib
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.async_api import async_playwright
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime, studio
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
OUT=M/'browser-qa';OUT.mkdir(exist_ok=True)
state=runtime.read(M/'task.json');task=runtime.read(studio.day_path(state['plan_id'],state['date']))
items=[]
for jid in task.get('jobs',{}).values():
 for a in runtime.articles(runtime.job_root(jid)):items.append({**a,'job':jid})
ready=[a for a in items if a['quality_status']=='ready'];held=[a for a in items if a['quality_status']!='ready']
firstjob=next(iter(task['jobs'].values()));product=runtime.product_label(runtime.job_root(firstjob),state['date'])
blocked={(a['job'],a['id']) for a in held}
for jid in task['jobs'].values():
 root=runtime.job_root(jid)
 for folder in (root/'days'/state['date']/'jobs').glob('*/*'):
  article_id=state['date']+'/'+folder.parent.name+'/'+folder.name
  if not any(a['job']==jid and a['id']==article_id for a in ready):blocked.add((jid,article_id))
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await b.new_page(viewport={'width':1400,'height':1000},accept_downloads=True);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected',timeout=30000)
  await page.evaluate("([product,date])=>{showView('outputs',false);$('dateFilter').value=date;$('productFilter').value=product;$('search').value='';$('outputFilter').value='new';applyFilters()}",[product['id'],state['date']])
  links=page.locator('#library a[href*="kind=word"]');assert await links.count()==len(ready)
  words=[]
  for i in range(len(ready)):
   target=links.nth(i);query=parse_qs(urlsplit(await target.get_attribute('href')).query)
   item=next(a for a in ready if a['id']==query['article'][0] and a['job']==query['job'][0])
   name=item['job'].split('-')[-1]+'_'+item['id'].split('/')[-2]+'_'+item['id'].split('/')[-1]+'.docx'
   async with page.expect_download() as event:await target.click()
   dl=await event.value;await dl.save_as(str(OUT/name))
   original=runtime.job_root(item['job'])/'approved'/item['id']/'article.docx'
   assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==hashlib.sha256(original.read_bytes()).hexdigest()
   words.append({'file':name,'id':item['id'],'title':item['title']})
  if ready:
   async with page.expect_download() as event:await page.locator('#downloadAll').click()
   dl=await event.value;await dl.save_as(str(OUT/'道和小绿瓶测试合格稿与溯源.zip'))
   with zipfile.ZipFile(OUT/'道和小绿瓶测试合格稿与溯源.zip') as z:
    assert z.testzip() is None;manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==len(ready)
    for row in manifest['articles']:
     folder=row['directory'];doc=next(n for n in z.namelist() if n.startswith(folder+'/') and n.endswith('.docx'))
     receipt=json.loads(z.read(folder+'/审核与溯源/receipt.json'))
     expected=receipt['files']['article.docx'];expected=expected.get('sha256') if isinstance(expected,dict) else expected
     assert hashlib.sha256(z.read(doc)).hexdigest()==expected
  else:
   code=await page.evaluate('async ([plan,date])=>(await fetch(link("all-approved","","bundle")+"&"+new URLSearchParams({plan,date}))).status',[state['plan_id'],state['date']]);assert code==400
  rejected=[]
  for jid,article_id in sorted(blocked):
   code=await page.evaluate('async ([j,id])=>(await fetch(link(j,id,"word"))).status',[jid,article_id]);assert code==400;rejected.append({'job':jid,'id':article_id})
  code=await page.evaluate('async ()=> (await fetch(link("all-approved","","bundle")+"&date=2099-01-01")).status');assert code==400
  await page.screenshot(path=str(OUT/'trial-downloads.png'),full_page=True);await b.close();assert not errors
  result={'downloaded':len(words),'by_genre':dict(Counter(a['category'] for a in ready)),'words':words,'zip_crc_ok':True if ready else None,'word_hashes_verified':True if ready else None,'file_checks_status':'verified' if ready else 'not_applicable_no_approved_articles','held_http400':rejected,'empty_filter_http':code,'page_errors':errors}
  (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
