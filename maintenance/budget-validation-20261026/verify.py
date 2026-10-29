import asyncio,json,sys
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  p=await b.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  async def guard(route):
   assert route.request.method=='GET'
   await route.fulfill(response=await route.fetch())
  await p.route('**/api/geo-creation/**',guard)
  if len(sys.argv)>1:
   async def html(route):
    await route.fulfill(content_type='text/html',body=Path(sys.argv[1]).read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await p.route('**/api/geo-creation/ui',html)
  await p.goto('http://192.168.31.106:3000/api/geo-creation/ui')
  await p.wait_for_function("data?.studio?.products?.length===9 && document.querySelector('#kbSelect').options.length===10")
  await p.evaluate('newCreationTask()')
  assert await p.locator('#kbSearch,#kbSearchHint,#planWriting').count()==0
  ids=await p.evaluate('data.studio.products.map(p=>p.product_id)')
  await p.locator('#kbSelect').select_option(ids[0]);await p.locator('#kbSave').click()
  await p.evaluate("""() => {
   $('planQuestions').value='眉毛稀疏怎么护理';$('planRounds').value='1';
   document.querySelectorAll('[name=planChannel]').forEach(e=>e.checked=e.value==='baidu_ai');confirmQuestions();
   for(const [id,value] of Object.entries({planName:'眉毛',planFrequency:'once',planTaskType:'collect_write',planStart:data.studio.today,planCapture:'11:05',planCount:'4',planArticleBudget:'0.5',planTaskBudget:'2'}))$(id).value=value;
  }""")
  assert not await p.evaluate('validateSchedule()')
  msg=await p.locator('#schedule .action-feedback').inner_text()
  assert '单篇预算上限不能超过共享限额 0.35 元' in msg,msg
  assert await p.evaluate('document.activeElement.id')=='planArticleBudget'
  await p.locator('#planArticleBudget').fill('0.35')
  assert await p.evaluate('validateSchedule()')
  await p.locator('#planTaskBudget').fill('11')
  assert not await p.evaluate('validateSchedule()')
  assert '本任务每次执行预算上限不能超过共享限额 10 元' in await p.locator('#schedule .action-feedback').inner_text()
  await p.locator('#planTaskBudget').fill('2');await p.locator('#planCapture').fill('')
  assert not await p.evaluate('validateSchedule()')
  assert '请填写开始采集时间' in await p.locator('#schedule .action-feedback').inner_text()
  assert not errors,errors
  print(json.dumps({'success':True,'selectable_products':len(ids),'search_removed':True,'page_errors':errors}))
  await b.close()

asyncio.run(main())
