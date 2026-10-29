"""Read-only public/LAN acceptance plus a real existing article export."""
import asyncio,hashlib,io,json,sys,zipfile
from pathlib import Path
from urllib.parse import urlencode
import requests
from playwright.async_api import async_playwright
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
ROOT=Path('/opt/monitor/geo-content/maintenance/20261019-studio-workflow')

async def main():
 s=requests.Session();s.trust_env=False;s.cookies.set('geo_monitor_session',browser_cookie(),domain='1any.top',path='/geo_monitor/')
 base='https://1any.top/geo_monitor/api/geo-creation/'
 results=[]
 for path in ['ui','panel']:
  r=s.get(base+path,timeout=30);r.raise_for_status()
  if path=='panel':data=r.json()
  else:assert 'wizardNav' in r.text and 'planFrequency' in r.text and '来源与执行日志' in r.text
  results.append({'path':path,'status':r.status_code})
 assert data['studio']['pending_import']['analysis']['brand']=='科熙本'
 article=next(a for a in data['legacy_articles'] if a.get('primary_reference',{}).get('url'))
 query=urlencode({'job':'legacy-original','article':article['id'],'kind':'package'})
 r=s.get(base+'download?'+query,timeout=30);r.raise_for_status()
 with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
  manifest=json.loads(archive.read('导出清单.json'));assert manifest['count']==1
  names=archive.namelist();word=next(n for n in names if n.endswith('.docx'))
  assert hashlib.sha256(archive.read(word)).hexdigest()==article['receipt']['files']['article.docx']
  assert any(n.endswith('文章信息.md') for n in names) and any(n.endswith('执行日志.json') for n in names)
  assert manifest['articles'][0]['primary_reference']['url']==article['primary_reference']['url']
 (ROOT/'qa/live-export.zip').write_bytes(r.content)
 errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900});page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function("document.getElementById('kbName').value.includes('科熙本')")
  await page.screenshot(path=str(ROOT/'qa/live-desktop.png'),full_page=False)
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  await page.screenshot(path=str(ROOT/'qa/live-mobile.png'),full_page=False)
  await browser.close()
 assert not errors,errors
 result={'public':results,'pending_product':data['studio']['pending_import']['analysis']['name'],'existing_plan_count':len(data['studio']['plans']),'existing_job_count':len(data['jobs']),'export_word_sha_identical':True,'export_contains_information_logs_and_audits':True,'directory':manifest['articles'][0]['directory'],'reference':manifest['articles'][0]['primary_reference'],'mobile_no_horizontal_overflow':True,'page_errors':errors,'mutations':'none; only read existing approved article, no live task saved or paid request'}
 (ROOT/'qa/live-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))

asyncio.run(main())
