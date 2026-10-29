import asyncio,io,json,shutil,sys,time,uuid,zipfile
from pathlib import Path
from playwright.async_api import async_playwright,expect
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,knowledge_library as lib
D=Path('/tmp/knowledge-library-20261024');name='知识库入口验收临时产品-'+uuid.uuid4().hex[:8]
async def main():
 lid=pid=plan_id=None;errors=[];before_products={p['product_id'] for p in studio.products()};before_plans={p['plan_id'] for p in studio.plans()}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':950});page.on('pageerror',lambda e:errors.append(str(e)))
  try:
   await page.goto('http://127.0.0.1:3000/#creation');f=page.frame_locator('iframe[title="GEO 内容创作控制台"]');await expect(f.locator('#connection')).to_contain_text('已连接',timeout=30000)
   await f.locator('[data-view="knowledge"]').click();await expect(f.locator('#libraryUpload')).to_be_disabled()
   buf=io.BytesIO()
   with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>验收产品规格200ml，仅用于交互测试。</w:t></w:r></w:p></w:body></w:document>')
   await f.locator('#libraryName').fill(name);await f.locator('#libraryNotes').fill('发布验收临时上传，测试后清理')
   await f.locator('#libraryWord').set_input_files({'name':'验收知识库.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()});await f.locator('#libraryUpload').click()
   await expect(f.locator('#libraryFeedback')).to_contain_text('等待人工分析',timeout=20000)
   r=next(r for r in lib.records() if r['name']==name);lid=r['library_id'];u=r['uploads'][-1];assert u['status']=='pending' and not r['product_id']
   await page.reload();await expect(f.locator('#connection')).to_contain_text('已连接');await f.locator('[data-view="knowledge"]').click();await f.locator('#librarySearch').fill(name);await expect(f.locator('#knowledgeRows')).to_contain_text('待人工分析')
   result=runtime.action('kb_publish',{'library_id':lid,'import_id':u['import_id'],'reviewer':'人工验收','product':{'name':name,'brand':'验收专用','facts':['规格200ml']}},uuid.uuid4().hex);pid=result['product_id']
   await f.locator('#librarySearch').evaluate('()=>refresh()');await f.locator('[data-library-use="'+pid+'"]').click();await expect(f.locator('#dailyPlan')).to_be_visible()
   await f.locator('#planQuestions').fill('验收问题，不执行采集');await f.locator('[name="planChannel"][value="baidu_ai"]').check();await f.locator('#planRounds').fill('1');await f.locator('#toSchedule').click()
   for selector,value in [('planName',name+'任务'),('planStart','2099-10-24'),('planCapture','02:01'),('planWriting','04:00'),('planCount','1'),('planArticleBudget','0.35'),('planTaskBudget','1')]:await f.locator('#'+selector).fill(value)
   await f.locator('#planFrequency').select_option('once');await f.locator('#planTaskType').select_option('capture_only');await f.locator('#planSave').click()
   await expect(f.locator('#message')).to_contain_text('草稿',timeout=20000);plan=next(p for p in studio.plans() if p['name']==name+'任务');plan_id=plan['plan_id'];assert not plan['enabled'] and plan['product_id']==pid
   await f.locator('[data-view="knowledge"]').click();await f.locator('[data-library-update="product:'+pid+'"]').click();await f.locator('#libraryWord').set_input_files({'name':'验收新版.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()});await f.locator('#libraryUpload').click();await expect(f.locator('#knowledgeRows')).to_contain_text('新版待分析')
   assert studio.product(pid)['version']==result['version'];assert studio.plan(plan_id)['product_version']==result['version']
   await f.locator('#knowledgeRows details').first.evaluate('(e)=>e.open=true');await page.screenshot(path=str(D/'live-library.png'),full_page=True)
   await f.locator('[data-view="tasks"]').click();await f.locator('[data-delete-plan="'+plan_id+'"]').click();await f.locator('#deleteConfirm').click();await expect(f.locator('[data-delete-plan="'+plan_id+'"]')).to_have_count(0)
   assert not errors,errors
   report={'success':True,'actual_dashboard_gateway':True,'upload_survives_reload':True,'manual_publish_and_task_draft':True,'update_keeps_current_and_task_versions':True,'paid_jobs':0,'page_errors':errors,'original_products':len(before_products),'original_tasks':len(before_plans)}
  finally:
   if plan_id:
    assert studio.plan(plan_id,include_deleted=True)['name']==name+'任务';runtime.action('plan_delete',{'plan_id':plan_id},uuid.uuid4().hex)
   # Only temporary test records identified above are cleaned up. No user product is touched.
   if lid:
    r=lib.record(lid);assert r['name']==name
    for u in r['uploads']:
     studio.identity(u['import_id'],'upload');shutil.rmtree(studio.ROOT/'imports'/u['import_id'])
    (studio.ROOT/'library'/(lid+'.json')).unlink()
   if pid:
    assert pid not in before_products and studio.product(pid)['product']['name']==name
    (studio.ROOT/'products'/(pid+'.json')).unlink();shutil.rmtree(studio.ROOT/'versions'/pid)
   await browser.close()
  assert {p['product_id'] for p in studio.products()}==before_products and {p['plan_id'] for p in studio.plans()}==before_plans
  (D/'live-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
asyncio.run(main())
