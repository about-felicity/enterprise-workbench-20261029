"""Real browser QA against isolated file-backed API actions; no live paid jobs."""
import asyncio,base64,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from playwright.async_api import async_playwright
sys.path.insert(0,'/opt/monitor/geo-content/maintenance/20261019-studio-workflow/candidate')
from creation import runtime,studio,materials,source_adapter
from geo_source_cards.runtime import atomic_json

async def main():
 out=Path('/opt/monitor/geo-content/maintenance/20261019-studio-workflow/qa');out.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as tmp:
  base=Path(tmp)
  with patch.object(runtime,'BASE',base/'runtime'),patch.object(studio,'ROOT',base/'studio'),patch.object(materials,'ROOT',base/'materials'),patch.object(materials,'GEO',base/'geo'):
   atomic_json(materials.ROOT/'settings.json',{'questions':[],'channels':list(materials.CHANNELS)})
   atomic_json(materials.GEO/'daily_plan.json',{'time':'09:00'})
   imported=studio.import_word({'filename':'科熙本二硫化硒清爽去屑止痒洗发水知识库.docx','content_base64':base64.b64encode(Path('/tmp/geo-studio-product-knowledge.docx').read_bytes()).decode()})
   errors=[]
   async with async_playwright() as pw:
    browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
    async def handle(route):
     request=route.request;path=request.url.split('studio.test',1)[1].split('?',1)[0]
     try:
      if path=='/':return await route.fulfill(content_type='text/html',body=Path(studio.__file__).with_name('panel.html').read_text())
      if path=='/api/panel':value={**runtime.status(),'csrf':'a'*64}
      elif path=='/api/catalog':value={'dedicated':materials.catalog(),'product':{},'geo':{'dates':[],'questions':[],'channels':[]}}
      elif path.startswith('/api/control/'):
       assert request.headers.get('x-csrf-token')=='a'*64
       value={'ok':True,'result':runtime.action(path.rsplit('/',1)[-1],request.post_data_json,request.headers['x-action-id'])}
      else:return await route.abort()
      return await route.fulfill(content_type='application/json',body=json.dumps(value,ensure_ascii=False))
     except Exception as error:
      errors.append(type(error).__name__+': '+str(error));return await route.fulfill(status=400,content_type='application/json',body=json.dumps({'message':str(error)}))
    page=await browser.new_page(viewport={'width':1366,'height':900});page.on('pageerror',lambda e:errors.append(str(e)));await page.route('http://studio.test/**',handle)
    await page.goto('http://studio.test/');await page.wait_for_function("document.getElementById('kbName').value.includes('科熙本')")
    assert await page.locator('#kbBrand').input_value()=='科熙本'
    assert '200ml/瓶' in await page.locator('#kbExtracted').inner_text()
    await page.screenshot(path=str(out/'01-product-desktop.png'),full_page=False)
    await page.locator('#kbSave').click();await page.locator('#dailyPlan').wait_for(state='visible')
    await page.locator('#planQuestions').fill('推荐一款去屑止痒洗发水\n油性头皮适合什么洗发水')
    assert await page.locator('[name=planChannel]:checked').count()==3
    await page.locator('#toSchedule').click();await page.locator('#schedule').wait_for(state='visible')
    await page.locator('#planName').fill('隔离验收一次任务')
    await page.locator('#planFrequency').select_option('once');await page.locator('#planStart').fill('2099-10-20')
    await page.locator('#planArticleBudget').fill('0.1');await page.locator('#planTaskBudget').fill('1')
    await page.locator('#planEnable').click()
    await page.wait_for_function("document.getElementById('planQueue').innerText.includes('2099-10-20')")
    assert len(studio.plans())==1 and studio.plans()[0]['frequency']=='once'
    assert not list((runtime.BASE/'runs').glob('*/job.json'))
    await page.screenshot(path=str(out/'02-queue-desktop.png'),full_page=False)
    await page.set_viewport_size({'width':390,'height':844});await page.locator('#wizardNav').scroll_into_view_if_needed();await page.screenshot(path=str(out/'03-mobile.png'),full_page=False)
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    await page.locator('[data-edit-plan]').first.click();await page.locator('#toSchedule').click()
    assert await page.locator('#planName').input_value()=='隔离验收一次任务'
    assert await page.locator('#planFrequency').input_value()=='once'
    await browser.close()
   assert not errors,errors
   result={'word_analysis':{k:imported['analysis'][k] for k in ['name','brand','specification','manufacturer','filing_number']},'wizard_product_questions_schedule':True,'three_default_channels':True,'oneoff_saved_in_isolated_queue':True,'oneoff_edit_preserved':True,'mobile_no_horizontal_overflow':True,'live_paid_jobs_created':0,'page_errors':errors}
   (out/'ui-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))

asyncio.run(main())
