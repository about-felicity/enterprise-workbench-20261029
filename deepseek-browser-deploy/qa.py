import asyncio,functools,json,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path('/opt/monitor/geo-deepseek-browser-test')
async def main():
    server=ThreadingHTTPServer(('127.0.0.1',18821),functools.partial(SimpleHTTPRequestHandler,directory=str(ROOT/'project')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path=str(ROOT/'chromium/chrome-linux64/chrome'))
        page=await browser.new_page()
        await page.goto('http://127.0.0.1:18821/tests/extension_self_test.html')
        await page.wait_for_function('document.querySelector("#result").textContent!=="RUNNING"',timeout=30000)
        result=await page.locator('#result').inner_text()
        assert result.startswith('ALL_PASS'),result
        # Execute the real adapted background gate against its isolated mock storage.
        gate=await page.evaluate('async()=>{await initialization;const a=await claimSendSlot();const b=await claimSendSlot();return {a,b,settings:safeSettings({intervalMinSeconds:1,intervalMaxSeconds:1})}}')
        assert gate['a']['ok'] and not gate['b']['ok'] and 599000<=gate['b']['waitMs']<=900000
        assert gate['settings']['intervalMinSeconds']==600 and gate['settings']['intervalMaxSeconds']==900
        source=await page.evaluate('fetch("../extension/content.js").then(r=>r.text())')
        assert source.index('phase: "send_intent"')<source.index('if (send) send.click()')
        assert 'await ensureThinkingOff();' in source and 'error.pauseJob = true' in source
        report={'self_test':result,'persistent_send_gate_10_15':True,'single_click_intent_before_send':True,'thinking_guard':True,'test_questions_sent':0}
        (ROOT/'qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False))
        await browser.close()
    server.shutdown()
asyncio.run(main())
