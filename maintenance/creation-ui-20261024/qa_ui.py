"""Browser integration: real file-backed actions, isolated data, zero model calls."""
import asyncio,base64,io,json,sys,tempfile,zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from playwright.async_api import async_playwright,expect
D=Path('/tmp/geo-creation-ui-20261024');C=D/'candidate';sys.path[:0]=[str(C),str(C/'engine')]
from creation import runtime,studio,materials

async def main():
 errors=[];counts=Counter();fault={};gate=asyncio.Event();gate.set();checks=[]
 with tempfile.TemporaryDirectory() as tmp:
  T=Path(tmp)
  with patch.object(runtime,'BASE',T/'runtime'),patch.object(runtime,'SHARED',T/'shared'),patch.object(studio,'ROOT',T/'studio'),patch.object(materials,'ROOT',T/'materials'),patch.object(materials,'GEO',T/'geo'),patch.object(runtime,'balance',return_value={'is_available':True}):
   runtime.atomic_json(materials.GEO/'daily_plan.json',{'time':'09:00'})
   kb=studio.save_product({'name':'交互验收产品','facts':['规格200ml']})
   def make(name):
    p=studio.save_plan({'product_id':kb['product_id'],'name':name,'questions':['用户问题'],'channels':['baidu_ai','wenxin_card'],'frequency':'once','task_type':'collect_write','capture_time':'01:00','writing_time':'04:00','start_date':'2099-10-17','enabled':True,'rounds':1,'max_per_category':1,'article_target':1})
    return studio.plan(p['plan_id'])
   def job(p,state,n):
    day=p['start_date'];jid='creation-1234567890-'+str(n)*8;r=runtime.BASE/'runs'/jid
    runtime.atomic_json(r/'job.json',{'job_id':jid,'date':day,'studio_plan_id':p['plan_id'],'question':'用户问题','material_source':'dedicated','material_counts':{'full_articles':1},'product':p['product']})
    runtime.atomic_json(r/'days'/day/'day.json',{'status':state})
    task=studio.ensure_day(p,day);task['jobs']={'用户问题':jid};runtime.atomic_json(studio.day_path(p['plan_id'],day),task)
   ended=make('已结束部分未通过测试');job(ended,'complete_with_failures',1)
   done=make('已完成测试');job(done,'complete',2)
   active=make('正在执行测试');job(active,'running',3)
   gap=make('素材不足测试');job(gap,'complete_with_shortfall',4)
   async with async_playwright() as pw:
    browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
    page=await browser.new_page(viewport={'width':1366,'height':950});page.on('pageerror',lambda e:errors.append(str(e)))
    async def handle(route):
     req=route.request;path=req.url.split('studio.test',1)[1].split('?',1)[0]
     if path=='/':return await route.fulfill(content_type='text/html',body=(C/'creation/panel.html').read_text())
     if path=='/api/panel':
      if fault.pop('offline',False):return await route.abort('failed')
      value={**runtime.status(),'csrf':'a'*64}
     elif path=='/api/catalog':value={'dedicated':{'dates':[],'questions':[],'channels':[]},'product':{},'geo':{'dates':[],'questions':[],'channels':[]}}
     elif path.startswith('/api/control/'):
      name=path.rsplit('/',1)[1];counts[name]+=1;await gate.wait()
      if fault.pop('validation',False):return await route.fulfill(status=400,json={'ok':False,'message':'测试：任务名称需要调整，输入已保留'})
      try:value={'ok':True,'result':runtime.action(name,req.post_data_json,req.headers['x-action-id'])}
      except ValueError as e:return await route.fulfill(status=400,json={'ok':False,'message':str(e)})
      if fault.pop('lost_response',False):return await route.abort('failed')
     else:return await route.abort()
     return await route.fulfill(json=value)
    await page.route('http://studio.test/**',handle);await page.goto('http://studio.test/')
    await expect(page.locator('#connection')).to_contain_text('已连接')
    for p in (ended,done,gap):
     row=page.locator('.queue-item').filter(has=page.locator('[data-edit-plan="'+p['plan_id']+'"]'))
     await expect(row.locator('[data-day-action]')).to_have_count(0);await expect(row.locator('[data-control-unavailable]')).to_be_disabled()
    checks.append('所有终态无可点击暂停/继续按钮')
    await page.screenshot(path=str(D/'01-task-list.png'),full_page=True)
    # Pause/resume keeps one request and displays the immediate pending state.
    pause=page.locator('[data-day-action="day_pause"][data-plan="'+active['plan_id']+'"]');gate.clear();await pause.click()
    await expect(pause).to_be_disabled();await expect(pause).to_contain_text('正在暂停');await expect(page.locator('#message')).to_contain_text('安全收尾')
    await pause.dispatch_event('click');gate.set();await expect(page.locator('[data-day-action="day_resume"][data-plan="'+active['plan_id']+'"]')).to_be_enabled();assert counts['day_pause']==1
    await page.locator('[data-day-action="day_resume"][data-plan="'+active['plan_id']+'"]').click();await expect(page.locator('[data-day-action="day_pause"][data-plan="'+active['plan_id']+'"]')).to_be_enabled()
    checks.append('暂停/继续反馈和重复点击防护')
    await page.get_by_role('button',name='＋ 新建任务').click();await expect(page.locator('#kbImport')).to_be_disabled()
    # Genuine small docx file.
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>眉毛护理产品知识库</w:t></w:r></w:p><w:p><w:r><w:t>品牌：测试品牌</w:t></w:r></w:p><w:p><w:r><w:t>规格：10ml</w:t></w:r></w:p></w:body></w:document>')
    await page.locator('#kbWord').set_input_files({'name':'交互测试.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()})
    gate.clear();await page.locator('#kbImport').click();await expect(page.locator('#kbImport')).to_be_disabled();await expect(page.locator('#kbName')).to_be_disabled();await expect(page.locator('#kbSource')).to_contain_text('正在')
    await page.screenshot(path=str(D/'02-import-working.png'),full_page=True)
    await page.locator('#kbImport').dispatch_event('click');gate.set();await expect(page.locator('#kbImport')).to_be_enabled();await expect(page.locator('#knowledge .action-feedback')).to_contain_text('已解析');assert counts['kb_import']==1
    await page.locator('#kbName').fill('浏览器全流程测试产品');await page.locator('#kbSave').click();await expect(page.locator('#dailyPlan')).to_be_visible();await expect(page.locator('#kbSave')).to_be_enabled()
    await page.locator('#planQuestions').fill('眉毛稀疏怎么护理？\n眉毛护理液怎么选？');await page.locator('[name=planChannel][value=baidu_ai]').check();await page.locator('[name=planChannel][value=wenxin_card]').check();await page.locator('#planRounds').fill('1');await page.locator('#toSchedule').click()
    for ident,value in {'planName':'浏览器新建任务','planStart':'2099-10-18','planCapture':'01:00','planWriting':'04:00','planCount':'1','planArticleBudget':'0.1','planTaskBudget':'1'}.items():await page.locator('#'+ident).fill(value)
    await page.locator('#planFrequency').select_option('once');await page.locator('#planTaskType').select_option('collect_write')
    fault['validation']=True;await page.locator('#planEnable').click();await expect(page.locator('#schedule .action-feedback')).to_contain_text('需要调整');await expect(page.locator('#planEnable')).to_be_enabled();await expect(page.locator('#planName')).to_have_value('浏览器新建任务')
    checks.append('Word导入、字段回填、保存失败后保留输入并恢复按钮')
    gate.clear();await page.locator('#planEnable').click();await expect(page.locator('#planEnable')).to_contain_text('正在保存');await expect(page.locator('#planSave')).to_be_disabled();await expect(page.locator('#planName')).to_be_disabled();await page.locator('#planEnable').dispatch_event('click');gate.set()
    await expect(page.locator('#taskList')).to_be_visible();await expect(page.locator('#message')).to_contain_text('加入队列');assert counts['plan_save']==2
    created=next(p for p in studio.plans() if p['name']=='浏览器新建任务');assert created['enabled'];checks.append('新建保存成功返回任务列表，仅建立一次任务')
    # Cancel delete leaves data intact; lost response reconciles with original operation ID.
    delete=page.locator('[data-delete-plan="'+created['plan_id']+'"]');await delete.click();await expect(page.locator('#deleteTaskName')).to_have_text('浏览器新建任务');await page.locator('#deleteCancel').click();assert len(studio.plans())==5
    await delete.click();fault['lost_response']=True;await page.locator('#deleteConfirm').click();await expect(page.locator('#retryAction')).to_be_visible();await expect(page.locator('#message')).to_contain_text('未确认');await expect(page.locator('[data-delete-plan]').first).to_be_disabled()
    await page.locator('#retryAction').click();await expect(page.locator('#message')).to_contain_text('任务已删除');await expect(page.locator('[data-delete-plan="'+created['plan_id']+'"]')).to_have_count(0);assert len(studio.plans())==4
    assert counts['plan_delete']==2;checks.append('删除取消/确认、响应丢失后按原编号核对，不重复执行')
    # Re-rendering a filtered list must retain offline disabled states.
    fault['offline']=True;await page.evaluate('refresh()');await expect(page.locator('#connection')).to_contain_text('连接中断');await page.locator('#taskSearch').fill('已结束');await expect(page.locator('[data-delete-plan]').first).to_be_disabled();await page.evaluate('refresh()');await expect(page.locator('[data-delete-plan]').first).to_be_enabled();await page.locator('#taskSearch').fill('')
    checks.append('断线时禁止写操作，筛选刷新不绕过锁定，重连后恢复')
    await page.set_viewport_size({'width':390,'height':844});await page.screenshot(path=str(D/'03-mobile-list.png'),full_page=True);assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');checks.append('390px移动端无横向溢出')
    await browser.close()
 assert not errors,errors
 result={'success':True,'checks':checks,'page_errors':errors,'requests':dict(counts),'paid_requests':0};(D/'ui-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
