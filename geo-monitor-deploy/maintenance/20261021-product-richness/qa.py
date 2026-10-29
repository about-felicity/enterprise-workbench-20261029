import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
R=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness')
async def main():
 task=json.loads((R/'task.json').read_text())
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await b.new_page(viewport={'width':1366,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected',timeout=30000)
  await page.locator('[data-edit-plan="'+task['plan_id']+'"]:visible').click()
  values=await page.evaluate('({ranking:document.getElementById("planRankingTarget").value,science:document.getElementById("planScienceTarget").value,detail:document.getElementById("planRankingDetail").value,science_detail:document.getElementById("planScienceDetail").value,payload:planPayload(true)})')
  assert values['ranking']=='7' and values['science']=='7' and values['detail']=='1000' and values['science_detail']=='600',values
  assert values['payload']['genre_targets']=={'排行类':7,'科普类':7}
  assert values['payload']['writing_profile']['ranking_hanzi']==1000
  assert not errors,errors
  await page.screenshot(path=str(R/'task-editor.png'),full_page=True)
  (R/'ui-qa.json').write_text(json.dumps({'loaded_plan':task['plan_id'],'values':{k:v for k,v in values.items() if k!='payload'},'page_errors':errors,'actions_saved':0},ensure_ascii=False,indent=2))
  print('Real browser loaded configurable 7+7 and 1000/600 detail; no JS errors; zero saves')
  await b.close()
asyncio.run(main())
