import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path('/opt/monitor/geo-deepseek-browser-test')
async def main():
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path=str(ROOT/'chromium/chrome-linux64/chrome'))
        page=await browser.new_page()
        cases=[
          ('normal_answer_mentions_login','<textarea></textarea><div class="ds-message"><p>登录官网可查询产品资料，操作频繁可能影响使用。</p></div>',False,False),
          ('normal_answer_mentions_ban','<textarea></textarea><div class="ds-assistant-message-main-content"><p>账号已被封禁是一个提示示例。</p></div>',False,False),
          ('real_login','<input placeholder="请输入手机号"><input placeholder="请输入验证码">',True,False),
          ('real_restriction','<textarea></textarea><div role="alert">因违反用户使用规范，你的账号已被禁言</div>',False,True),
          ('real_verification','<div role="dialog">请完成安全验证</div>',False,True),
          ('missing_page','<p>网络加载中</p>',False,False)]
        result=[]
        for name,html,login,risk in cases:
            await page.set_content(html)
            value=await page.evaluate((ROOT/'auth_probe.js').read_text())
            assert (value['login'],value['risk'])==(login,risk),(name,value)
            result.append(name)
        (ROOT/'auth-qa.json').write_text(json.dumps({'passed':result,'production_inputs':0},indent=2))
        print(json.dumps({'passed':result}));await browser.close()
asyncio.run(main())
