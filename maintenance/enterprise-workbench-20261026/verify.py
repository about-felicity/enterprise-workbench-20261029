import asyncio,json,sys
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  p=await b.new_page();base=sys.argv[1];errors=[]
  p.on('pageerror',lambda e:errors.append(str(e)))
  await p.goto(base,wait_until='networkidle')
  assert await p.title()=='企业工作台',await p.title()
  assert await p.get_by_text('企业工作台',exact=True).count()>0
  for path in ['api/geo-capture/panel','api/geo-creation/panel','api/geo-creation/ui']:
   r=await p.request.get(base+path);assert r.ok,(path,r.status)
  assert not errors,errors
  print(json.dumps({'base':base,'title':await p.title(),'routes':3,'page_errors':errors},ensure_ascii=False))
  await b.close()
asyncio.run(main())
