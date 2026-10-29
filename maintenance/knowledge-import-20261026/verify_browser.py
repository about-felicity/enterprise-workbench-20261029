import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    rows=json.loads(Path('/opt/monitor/maintenance/knowledge-import-20261026/result.json').read_text())
    assert len(rows)==8
    async with async_playwright() as pw:
        b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        p=await b.new_page()
        await p.goto('http://192.168.31.106:3000/api/geo-creation/ui')
        await p.wait_for_function("document.querySelectorAll('#kbSelect option').length===17")
        await p.evaluate("newCreationTask()")
        for row in rows:
            assert await p.locator('#kbSelect option').filter(has_text=row['name']).count()==1
            await p.locator('#kbSelect').select_option(row['product_id'])
            assert row['name'] in await p.locator('#selectedKnowledge').inner_text()
        await p.screenshot(path='/opt/monitor/maintenance/knowledge-import-20261026/selector.png',full_page=True)
        print(json.dumps({'selectable_products':16,'imported_products_verified':8,'duplicate_options':0}))
        await b.close()
asyncio.run(main())
