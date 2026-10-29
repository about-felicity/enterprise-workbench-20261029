import json
from pathlib import Path
import re
import sys
import time
from playwright.sync_api import sync_playwright,expect

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-compact-board')
mode=sys.argv[1] if len(sys.argv)>1 else 'preview'
url={'preview':'http://127.0.0.1:3000/','production':'http://127.0.0.1:3000/','public':'https://1any.top/geo_monitor/'}[mode]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1366,'height':768},permissions=['local-network-access'])
 if mode=='public':
  sys.path.insert(0,'/tmp');from vps_geo_access import browser_cookie
  context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=context.new_page();errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def guard(route):
  if route.request.method!='GET':writes.append(route.request.url);route.abort()
  elif mode=='preview' and route.request.url.startswith('http://127.0.0.1:3000/'):
   # Serve the candidate through the normal origin; API CORS permits port3000.
   route.fulfill(response=context.request.get(route.request.url.replace(':3000/',':3001/')))
  else:route.continue_()
 page.route('**/*',guard)
 page.goto(url,wait_until='domcontentloaded',timeout=60000)
 board=page.locator('.owned-product-board')
 board.locator('.owned-product-summary-table tbody tr').first.wait_for(timeout=90000)
 expect(board.locator('.owned-product-daily-table tbody tr')).to_have_count(24,timeout=90000)
 expected={'summary':board.locator('.owned-product-summary-table tbody').text_content(),'daily':board.locator('.owned-product-daily-table tbody').text_content()}
 results=[]
 for width,height in [(2560,1440),(1920,1080),(1536,864),(1440,900),(1366,768),(1280,720),(1024,768),(820,1180),(768,1024),(390,844),(320,740)]:
  page.set_viewport_size({'width':width,'height':height})
  page.wait_for_timeout(150)
  metrics=board.evaluate('''el=>{
   const bad=[];const outer=el.getBoundingClientRect();
   for(const node of el.querySelectorAll('tbody td, .owned-product-state, .owned-product-surface, .owned-product-model-average, .rate-delta')){
    const r=node.getBoundingClientRect();
    if(r.left<outer.left-1||r.right>outer.right+1||node.scrollWidth>node.clientWidth+1)bad.push({class:node.className,label:node.getAttribute('data-label'),width:r.width,scroll:node.scrollWidth,client:node.clientWidth});
   }
   const sizes={};const unequal=[];
   for(const kind of ['summary','daily']){
    const rows=[...el.querySelectorAll('.owned-product-'+kind+'-table tbody tr')];
    const all=[];
    for(const [i,row] of rows.entries()){
     const rects=[...row.querySelectorAll('.owned-product-model-cell > span')].map(n=>({width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height}));
     all.push(...rects);
     if(Math.max(...rects.map(r=>r.width))-Math.min(...rects.map(r=>r.width))>1.1||Math.max(...rects.map(r=>r.height))-Math.min(...rects.map(r=>r.height))>1.1)unequal.push({kind,row:i,rects});
    }
    sizes[kind]={minHeight:Math.min(...all.map(r=>r.height)),maxHeight:Math.max(...all.map(r=>r.height)),minWidth:Math.min(...all.map(r=>r.width)),maxWidth:Math.max(...all.map(r=>r.width))};
   }
   const outside=[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(n=>({tag:n.tagName,class:n.className,width:n.getBoundingClientRect().width,right:n.getBoundingClientRect().right}));
   return {pageOverflow:document.documentElement.scrollWidth>innerWidth,outside:document.documentElement.scrollWidth>innerWidth?outside:[],boardWidth:outer.width,bad,unequal,sizes,summaryRows:el.querySelectorAll('.owned-product-summary-table tbody tr').length,dailyRows:el.querySelectorAll('.owned-product-daily-table tbody tr').length,layout:getComputedStyle(el.querySelector('tbody tr')).display};
  }''')
  assert not metrics['bad'] and not metrics['pageOverflow'],(width,metrics)
  assert not metrics['unequal'],(width,metrics['unequal'][:3])
  for kind,sizes in metrics['sizes'].items():
   assert sizes['maxHeight']-sizes['minHeight']<=1.1,(width,kind,sizes)
  for name in ['summary','daily']:
   assert board.locator('.owned-product-'+('summary' if name=='summary' else 'daily')+'-table tbody').text_content()==expected[name],(width,'changed data',name)
  assert board.locator('.owned-product-daily-table tbody tr').first.locator('.owned-product-model-cell').count()==5
  assert board.locator('.owned-product-daily-table tbody tr').first.locator('.owned-product-surface').count()==2
  if width in [2560,1366,1024,390]:
   board.locator('.owned-product-summary-table tbody tr').first.screenshot(path=str(ROOT/f'{mode}-summary-{width}.png'))
   board.locator('.owned-product-daily-table tbody tr').first.screenshot(path=str(ROOT/f'{mode}-daily-{width}.png'))
  results.append({'width':width,'height':height,**metrics})
  if width in [1920,1366]:
   assert metrics['sizes']['summary']['maxHeight']<=112 and metrics['sizes']['daily']['maxHeight']<=112,(width,'cards are too tall',metrics['sizes'])
   assert board.locator('.owned-product-summary-table tbody tr').first.bounding_box()['height']<280
 # Secondary evidence is retained and opens in the header, outside model cards.
 page.set_viewport_size({'width':1366,'height':768})
 for kind in ['summary','daily']:
  first=board.locator('.owned-product-'+kind+'-table tbody tr').first
  details=first.locator('.owned-product-sampling-details')
  assert not details.evaluate('(e)=>e.open')
  details.locator('summary').click()
  expect(details.locator('div')).to_be_visible()
  assert '百度卡片' in details.inner_text() and ('有效日期' in details.inner_text() if kind=='summary' else '轮采集' in details.inner_text())
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  details.locator('summary').click()
 # Filtering still uses actual data; selecting one model must retain its rate.
 page.set_viewport_size({'width':1366,'height':768})
 page.locator('aside .scope button').filter(has_text='元宝').click()
 page.get_by_test_id('question-filter').select_option(label='眉毛增长液推荐')
 expect(board.locator('.owned-product-daily-table .owned-product-rate')).to_have_text('50.0%',timeout=60000)
 expect(board.locator('.owned-product-daily-table tbody tr')).to_have_count(1)
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors and not writes
 browser.close()
report={'passed':True,'mode':mode,'at':time.time(),'resolutions':results,'all_models_visible':True,'wenxin_and_baidu_visible':True,'data_unchanged_on_resize':True,'filter_regression':'yuanbao 4/8 50%','javascript_errors':errors,'production_test_writes':writes}
(ROOT/('qa-'+mode+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
