import asyncio,hashlib,json,time
from pathlib import Path
from playwright.async_api import async_playwright,expect
D=Path('/tmp/geo-creation-ui-20261024');L=Path('/opt/monitor/geo-content')
async def main():
 errors=[];created=None
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':950});page.on('pageerror',lambda e:(errors.append(str(e)),print('PAGE ERROR:',str(e))))
  page.on('requestfailed',lambda r:print('REQUEST FAILED:',r.url,r.failure))
  await page.goto('http://127.0.0.1:8804/');await expect(page.locator('#connection')).to_contain_text('已连接',timeout=20000)
  response=await page.request.get('http://127.0.0.1:8804/api/panel');s=await response.json()
  headers={'Origin':'http://127.0.0.1:8804','X-CSRF-Token':s['csrf']}
  async def action(name,payload):
   return await page.request.post('http://127.0.0.1:8804/api/control/'+name,data=payload,headers={**headers,'X-Action-Id':hashlib.md5((name+str(time.time_ns())).encode()).hexdigest()})
  target=next(p for p in s['studio']['plans'] if p.get('name','').startswith('道和'))
  row=page.locator('.queue-item').filter(has=page.locator('[data-edit-plan="'+target['plan_id']+'"]'))
  await expect(row.locator('[data-day-action]')).to_have_count(0);await expect(row.locator('[data-control-unavailable]')).to_be_disabled();await expect(row).to_contain_text('已结束')
  denied=await action('day_pause',{'plan_id':target['plan_id'],'date':target['start_date']});assert denied.status==400
  denied_body=await denied.json();assert '已结束' in denied_body['message']
  before=len(s['studio']['plans'])
  try:
   response=await action('plan_save',{'product_id':s['studio']['products'][0]['product_id'],'name':'前端发布验收临时草稿（已自动清理）','frequency':'once','task_type':'capture_only','start_date':'2099-10-24','capture_time':'01:01','writing_time':'04:00','questions':['前端交互验收，不执行采集'],'channels':['baidu_ai'],'rounds':1,'max_per_category':1,'enabled':False})
   result=await response.json();assert response.ok,result;created=result['result']['plan_id']
   await page.reload();await expect(page.locator('[data-delete-plan="'+created+'"]')).to_be_enabled()
   await page.locator('[data-delete-plan="'+created+'"] ').click();await expect(page.locator('#deleteDialog')).to_be_visible();await page.locator('#deleteConfirm').click()
   await expect(page.locator('#message')).to_contain_text('任务已删除');await expect(page.locator('[data-delete-plan="'+created+'"]')).to_have_count(0)
   latest=await (await page.request.get('http://127.0.0.1:8804/api/panel')).json();assert len(latest['studio']['plans'])==before
   assert not any(j.get('studio_plan_id')==created for j in latest['jobs'])
   approved=next(j for j in latest['jobs'] if j['job_id']=='creation-1792807286-eb504495');assert len(approved['articles'])==7
   daily=next(p for p in latest['studio']['plans'] if p['plan_id']=='plan-9b827648df6c4bf9b5648db2eaf6079e');assert daily['enabled'] and daily['article_target']==7 and daily['capture_time']=='01:00' and daily['writing_time']=='04:00'
   await page.locator('#taskSearch').fill('道和');await page.screenshot(path=str(D/'live-task-controls.png'),full_page=True)
   await page.get_by_role('button',name='＋ 新建任务').click();await expect(page.locator('#kbImport')).to_be_disabled();await page.screenshot(path=str(D/'live-editor.png'),full_page=True)
   assert not errors,errors
   result={'success':True,'task_count_preserved':before,'finished_task_pause_denied':True,'actual_http_draft_save_and_ui_delete':True,'temporary_plan_id':created,'test_capture_or_paid_jobs':0,'existing_brow_articles':7,'daily_schedule_preserved':True,'page_errors':errors}
   (D/'live-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
  finally:
   if created:
    await action('plan_delete',{'plan_id':created})
   await browser.close()
asyncio.run(main())
