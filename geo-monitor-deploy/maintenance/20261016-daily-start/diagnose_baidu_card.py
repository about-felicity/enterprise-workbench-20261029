"""Inspect a current Baidu card in its own search context; no Wenxin substitution."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture/venv/lib/python3.10/site-packages')
from wenxin_monitor.controller import WenxinWebCollector,BAIDU_AI_SNAPSHOT_JS
from geo_source_cards.runtime import process_lock

root=Path('/opt/monitor/geo-capture/batches/geo-panel-baidu-ai-20261015-181822-d44632b8/collector')
out=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start/baidu-diagnosis')
out.mkdir(parents=True,exist_ok=True)
os.environ['WENXIN_STEALTH_HEADLESS']='1'
question=sys.argv[1]
with process_lock(root/'collector.lock'):
    collector=WenxinWebCollector(profile=root/'profiles/baidu/scrapling_profile')
    try:
        collector.page.call('Page.navigate',{'url':'https://www.baidu.com/'},timeout=30)
        nav=collector._navigate_fresh(collector.search_url(question))
        for _ in range(35):
            snapshot=collector.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
            if collector._is_security_verification(snapshot):raise RuntimeError('security_verification')
            if snapshot.get('ok') and snapshot.get('readyState')=='complete':break
            time.sleep(1)
        collector._expand_ai_card();collector._scroll_ai_card();time.sleep(3)
        snapshot=collector.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
        details=collector.page.evaluate(r'''(()=>{const c=document.querySelector('#content_left [tpl="new_baikan_index"],#content_left [tpl="wenda_generate"],#content_left .cosc-card');return {card:c?.outerHTML||'',text:c?.innerText||'',links:[...(c?.querySelectorAll('a[href]')||[])].map(a=>({text:a.innerText,url:a.href,cls:a.className,parent:a.parentElement?.className})),controls:[...(c?.querySelectorAll('button,[role=button]')||[])].map(a=>({text:a.innerText,cls:a.className}))}})()''')
        key=str(time.time_ns())
        (out/(key+'.json')).write_text(json.dumps({'question':question,'snapshot':snapshot,'details':details},ensure_ascii=False))
        if getattr(collector.page,'page',None):collector.page.page.screenshot(path=str(out/(key+'.png')),full_page=True)
        print(json.dumps({'question':question,'navigation_id':nav,'snapshot':{k:v for k,v in snapshot.items() if k!='body'},
                          'body_length':len(snapshot.get('body','')),'card_tail':details['text'][-650:],
                          'links':details['links'],'controls':details['controls'],'evidence':key},ensure_ascii=False))
    finally:collector.close()
