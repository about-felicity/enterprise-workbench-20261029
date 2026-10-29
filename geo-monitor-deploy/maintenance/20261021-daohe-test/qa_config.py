import sys,asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
state=json.loads((M/'task.json').read_text())
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await b.new_page(viewport={'width':1400,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected',timeout=30000)
  result=await page.evaluate('id=>{loadPlan(id);showView("editor",false);showStep(3);const p=planPayload(true);return {target:p.article_target,genres:p.genre_targets,once:p.frequency,article_budget:p.article_budget_cny,task_budget:p.task_budget_cny,question_count:p.questions.length}}',state['plan_id'])
  assert result['target']==14 and result['genres']=={'排行类':7,'测评类':7} and result['once']=='once' and result['question_count']==7,result
  await page.screenshot(path=str(M/'configured-test.png'),full_page=True);await b.close();assert not errors
  result['page_errors']=errors;(M/'ui-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
