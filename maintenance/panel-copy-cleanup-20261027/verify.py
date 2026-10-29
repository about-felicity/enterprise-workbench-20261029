import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
D=Path('/tmp/panel-copy-verification');D.mkdir(exist_ok=True)
forbidden=['上榜以对应问题正文中','仅统计所选自然月；每个','任意1轮回答正文确认推荐','专用素材采集、创作与成稿下载','管理任务、查看进度、下载成稿','查看执行安排，或打开任务修改配置','MODEL INTELLIGENCE','DAILY PERFORMANCE','COLLECTION WORKSPACE','INTERACTIVE TREND','准确性与成本口径','问题清单、账号校验、采集进程、分析与数据文件','主占比＝命中自有品牌','模型交集严格服从','标题本地分词；显示每日 Top 10','填写三步配置后保存','先确认产品资料，再确认问题与渠道']
async def main():
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  p=await b.new_page(viewport={'width':1530,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  await p.goto('http://127.0.0.1:3000/',wait_until='networkidle')
  await p.locator('.owned-product-board').wait_for(timeout=30000)
  checked=[]
  async def check(surface,name):
   text=await surface.locator('body').inner_text()
   assert not [s for s in forbidden if s in text],(name,[s for s in forbidden if s in text])
   checked.append(name)
  for label in ['模型总览','问题对比','信源洞察','品牌与产品','回答审计','采集控制','内容创作中心']:
   await p.locator('.sidebar nav button').filter(has_text=label).click()
   await p.wait_for_timeout(600)
   await check(p,label)
   if label in ['模型总览','品牌与产品','信源洞察','内容创作中心']:
    await p.screenshot(path=str(D/(label+'.png')),full_page=False)
   if label=='采集控制':
    frame=p.frame_locator('iframe');await frame.locator('#nav button').first.wait_for(timeout=30000)
    for index in range(await frame.locator('#nav button').count()):
     await frame.locator('#nav button').nth(index).click();await check(frame,'采集通道'+str(index))
   if label=='内容创作中心':
    frame=p.frame_locator('iframe');await frame.locator('#taskSearch').wait_for(timeout=30000)
    await frame.locator('#connection').filter(has_text='已连接').wait_for(timeout=30000)
    assert await frame.locator('#planQueue .queue-item').count()>0
    assert not await frame.locator('#workspaceTop h1').is_visible()
    await p.screenshot(path=str(D/'creation-loaded.png'),full_page=False)
    for view in ['tasks','knowledge','editor','progress','outputs']:
     await frame.locator('[data-view="'+view+'"]').click();await p.wait_for_timeout(200)
     await check(frame,'创作-'+view)
    # Inspect every editor section without saving or changing a production plan.
    await frame.locator('[data-view="editor"]').click()
    for section in ['knowledge','dailyPlan','schedule']:
     content=await frame.locator('#'+section).text_content()
     assert not [s for s in forbidden if s in content],section
     checked.append('编辑-'+section)
    for action in ['knowledge','outputs']:
     await frame.locator('[data-view="'+action+'"]').click()
     assert await frame.locator('[data-workspace="'+action+'"]').is_visible()
  assert not errors,errors
  report={'checked':checked,'page_errors':errors,'forbidden_phrases':len(forbidden)}
  (D/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  print(json.dumps(report,ensure_ascii=False))
  await b.close()
asyncio.run(main())
