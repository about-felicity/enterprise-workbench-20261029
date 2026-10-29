from playwright.sync_api import sync_playwright
from pathlib import Path
import json
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 page=b.new_page()
 try:
  page.goto('https://baijiahao.baidu.com/s?id=1879084544049497599&wfr=spider&for=pc',wait_until='domcontentloaded',timeout=45000)
  page.wait_for_timeout(5000)
  Path('/tmp/wenxin-article.html').write_text(page.content())
  print(json.dumps(page.evaluate('''()=>({text:document.body.innerText.slice(0,14000),nodes:[...document.querySelectorAll('article,main,[class*=article],[class*=content]')].map(e=>({tag:e.tagName,cls:e.className,chars:e.innerText.length,p:e.querySelectorAll('p').length})).filter(e=>e.chars>200).slice(0,40)})'''),ensure_ascii=False))
 finally:b.close()
