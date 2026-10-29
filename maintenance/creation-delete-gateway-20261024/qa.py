"""Exercise the real embedded dashboard gateway using a disabled future draft."""
import asyncio,hashlib,json,sys,time
from pathlib import Path
from playwright.async_api import async_playwright,expect
D=Path('/tmp/creation-delete-gateway-20261024');port=int(sys.argv[1]);base=f'http://127.0.0.1:{port}';api=base+'/api/geo-creation/'
async def main():
 created=None;errors=[];writes=[];fault={'reject':False,'delay':False};checks=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  context=await browser.new_context(viewport={'width':1366,'height':950});page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  if port==3001 or 'candidate' in sys.argv:
   await page.route('**/api/geo-creation/ui',lambda route:route.fulfill(content_type='text/html',body=(D/'stage/panel.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';")))
  async def intercept(route):
   writes.append(route.request.headers['x-action-id'])
   if fault['reject']:
    fault['reject']=False;return await route.fulfill(status=400,json={'ok':False,'message':'测试失败提示：请稍后重试'})
   if fault['delay']:
    await asyncio.sleep(2)
   await route.continue_()
  await page.route('**/api/geo-creation/control/plan_delete',intercept)
  async def panel():return await (await context.request.get(api+'panel')).json()
  s=await panel();before={p['plan_id'] for p in s['studio']['plans']};csrf=s['csrf']
  async def action(name,payload,key=None):
   return await context.request.post(api+'control/'+name,data=payload,headers={'Origin':base,'X-CSRF-Token':csrf,'X-Action-Id':key or hashlib.md5(str(time.time_ns()).encode()).hexdigest()})
  try:
   response=await action('plan_save',{'product_id':s['studio']['products'][0]['product_id'],'name':'删除入口验收临时草稿（自动清理）','frequency':'once','task_type':'capture_only','start_date':'2099-10-24','capture_time':'01:01','writing_time':'04:00','questions':['界面测试，不执行采集'],'channels':['baidu_ai'],'rounds':1,'max_per_category':1,'enabled':False})
   result=await response.json();assert response.ok,result;created=result['result']['plan_id']
   await page.goto(base+'/#creation');frame=page.frame_locator('iframe[title="GEO 内容创作控制台"]')
   await expect(frame.locator('#connection')).to_contain_text('已连接',timeout=30000)
   # Bottom-of-long-iframe visibility, then cancel: no real task is removed.
   await frame.locator('[data-delete-plan]').last.click();await expect(frame.locator('#deleteDialog')).to_be_visible()
   box=await frame.locator('#deleteDialog').bounding_box();assert 0<=box['y'] and box['y']+box['height']<=950,box
   await page.screenshot(path=str(D/f'bottom-confirm-{port}.png'))
   await frame.locator('#deleteCancel').click();assert not writes
   checks.append('长列表底部确认区可见，取消不发请求')
   target=frame.locator('[data-delete-plan="'+created+'"]');await target.click()
   # Polling must not dismiss confirmation or lose its handlers.
   await frame.locator('#deleteDialog').evaluate('()=>refresh()');await expect(frame.locator('#deleteConfirm')).to_be_enabled()
   fault['reject']=True;await frame.locator('#deleteConfirm').click()
   await expect(frame.locator('#deleteFeedback')).to_contain_text('测试失败提示');await expect(frame.locator('#deleteConfirm')).to_be_enabled();assert len(writes)==1
   await page.screenshot(path=str(D/f'inline-error-{port}.png'));checks.append('失败原因就地显示，可重新提交；轮询保留确认区')
   fault['delay']=True;await frame.locator('#deleteConfirm').click()
   await expect(frame.locator('#deleteConfirm')).to_be_disabled();await expect(frame.locator('#deleteCancel')).to_be_disabled()
   await expect(frame.locator('#deleteFeedback')).to_contain_text('正在停止后续执行')
   await frame.locator('#deleteConfirm').dispatch_event('click')
   await page.screenshot(path=str(D/f'deleting-{port}.png'))
   await expect(target).to_have_count(0,timeout=20000);await expect(frame.locator('#message')).to_contain_text('任务已删除');assert len(writes)==2
   checks.append('实际网关删除成功，提交期间禁用按钮，重复点击仅发一次')
   # Replaying the same completed action must remain safe and idempotent.
   replay=await action('plan_delete',{'plan_id':created},writes[-1]);assert replay.ok,await replay.text()
   await page.reload();await expect(frame.locator('#connection')).to_contain_text('已连接');await expect(target).to_have_count(0)
   latest=await panel();assert {p['plan_id'] for p in latest['studio']['plans']}==before
   assert not any(j.get('studio_plan_id')==created for j in latest['jobs'])
   assert len(next(j for j in latest['jobs'] if j['job_id']=='creation-1792807286-eb504495')['articles'])==7
   checks.append('刷新不恢复已删任务、操作重放幂等、真实任务及七篇眉毛文章保留')
   # The same confirmation must remain usable on mobile in the embedded dashboard.
   await page.set_viewport_size({'width':390,'height':844});await frame.locator('[data-delete-plan]').last.click()
   await asyncio.sleep(.5)
   box=await frame.locator('#deleteDialog').bounding_box();assert 0<=box['y'] and box['y']+box['height']<=844,box
   await page.screenshot(path=str(D/f'mobile-confirm-{port}.png'));await frame.locator('#deleteCancel').click()
   assert not errors,errors
   report={'success':True,'port':port,'checks':checks,'real_tasks_preserved':len(before),'test_plan':created,'test_paid_jobs':0,'browser_errors':errors}
   (D/f'qa-{port}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
  finally:
   if created:await action('plan_delete',{'plan_id':created})
   await browser.close()
asyncio.run(main())

