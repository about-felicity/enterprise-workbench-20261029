"""Inspect existing profiles on provider login pages, without submitting a prompt."""
import json,os,sqlite3,sys,time,re
from pathlib import Path
from geo_source_cards.runtime import process_lock
from web_collectors.collector import BrowserCollector
base=Path('/opt/monitor/geo-capture')
pointer={'test_id':sys.argv[1]};batch=sys.argv[2]
assert re.fullmatch(r'question-only-soak12h-[a-z0-9-]+',pointer['test_id']) and re.fullmatch(r'geo-panel-deepseek-[a-z0-9-]+',batch)
runtime=base/'batches'/batch/'collector'
report={'at':time.time(),'test_id':pointer['test_id'],'batch':batch,'profiles':{},'model_submissions':0}
with sqlite3.connect((runtime/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    report['queue_states']=dict(db.execute('select state,count(*) from captures group by state'))
for name,root,port in [('geo',runtime,'9514'),('original_content',Path('/home/user/geo-editorial/runtime-api/collectors/deepseek'),'9414')]:
    os.environ.update(GEO_COLLECTOR_RUNTIME=str(root),GEO_DEEPSEEK_PORT=port)
    os.environ.pop('GEO_PIPELINE_ROOT',None)
    with process_lock(root/'collector.lock'):
        collector=BrowserCollector('deepseek',headless=True)
        try:
            state=collector.check_ready()
            observations=[]
            for index in range(2):
                if index:time.sleep(3)
                observations.append({'state':collector.session_status(), 'page':collector.page.evaluate("""(()=>{const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};const labels=[...document.querySelectorAll('button,[role=button],a[href*=login]')].filter(visible).map(e=>String(e.innerText||e.getAttribute('aria-label')||'').trim()).filter(x=>/^(登录|立即登录|重新登录|登录\/注册|Sign in|Log in|Sign in to DeepSeek)$/i.test(x));return {hostname:location.hostname,pathname:location.pathname,readyState:document.readyState,login_controls:labels,has_password_input:[...document.querySelectorAll('input[type=password]')].some(visible)}})()""")})
            report['profiles'][name]={'status':state['status'],'observations':observations}
        finally:collector.close()
target=Path('/tmp/geo-deepseek-auth-audit.json');target.write_text(json.dumps(report,ensure_ascii=False,indent=2));target.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
