"""Exercise the login controller on a fake screen; never inputs into DeepSeek."""
import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path('/opt/monitor/geo-deepseek-browser-test')

async def main():
    calls=[];fail={'next':False}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path=str(ROOT/'chromium/chrome-linux64/chrome'))
        page=await browser.new_page(viewport={'width':1200,'height':1100})
        async def handle(route):
            path=route.request.url.split('18822',1)[-1].split('?')[0]
            if path=='/':return await route.fulfill(body=(ROOT/'login.html').read_text(),content_type='text/html')
            if path=='/status':return await route.fulfill(json={'message':'isolated test'})
            if path=='/frame':return await route.fulfill(body='<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="780"><rect width="1100" height="780" fill="white"/></svg>',content_type='image/svg+xml')
            if path=='/input':
                value=route.request.post_data_json;calls.append(value)
                await asyncio.sleep(.08)
                status=500 if fail['next'] else 200;fail['next']=False
                return await route.fulfill(status=status,json={'ok':status==200})
            return await route.fulfill(status=404)
        await page.route('http://127.0.0.1:18822/**',handle)
        await page.goto('http://127.0.0.1:18822/')
        await page.locator('#screen').click(position={'x':80,'y':80})
        await page.keyboard.type('1234567890',delay=0)
        await page.keyboard.press('Enter')
        await asyncio.sleep(.6)
        assert calls[0]['type']=='click'
        assert ''.join(x.get('text','') for x in calls)=='1234567890',calls
        assert calls[-1]=={'type':'key','key':'Enter'}
        calls.clear()
        await page.locator('#capture').evaluate('''e=>{e.dispatchEvent(new CompositionEvent('compositionstart'));e.value='中文输入';e.dispatchEvent(new InputEvent('input',{inputType:'insertCompositionText',data:'中文输入',isComposing:true}));e.dispatchEvent(new CompositionEvent('compositionend',{data:'中文输入'}));e.dispatchEvent(new InputEvent('input',{data:'中文输入'}));}''')
        await asyncio.sleep(.3)
        assert calls==[{'type':'text','text':'中文输入'}],calls
        calls.clear()
        await page.locator('#text').fill('2468')
        await page.locator('#send').click()
        await asyncio.sleep(.3)
        assert calls==[{'type':'text','text':'2468'}]
        assert await page.locator('#text').input_value()==''
        calls.clear();fail['next']=True
        await page.locator('#screen').click(position={'x':90,'y':90})
        await page.keyboard.type('will-not-replay',delay=0)
        await asyncio.sleep(.4)
        before=len(calls);await asyncio.sleep(.3)
        assert before==len(calls)==1,calls
        assert '未确认' in await page.locator('#inputState').inner_text()
        result={'keyboard_after_click':True,'click_text_enter_order':True,'no_dropped_digits':True,
                'chinese_composition_once':True,'local_text_fallback':True,'unknown_response_not_replayed':True,
                'production_inputs':0,'remote_page_restarted':False}
        (ROOT/'input-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        print(json.dumps(result,ensure_ascii=False));await browser.close()
asyncio.run(main())
