import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
started=time.monotonic()
with op.open('http://127.0.0.1:8765/api/performance?month=2026-10',timeout=40) as response:
 raw=response.read();data=json.loads(raw)
assert len(data['people'])==5 and data['product_count']==15
assert len(data['excluded_products'])==9
assert all(p['current']['scores']['values']==100 for p in data['people'])
assert all(p['current']['budget']['latest_date']=='2026-10-27' for p in data['people'])
assert all(p['current']['traffic']['latest_date']=='2026-10-30' for p in data['people'])
assert all(len(p['daily'])==31 for p in data['people'])
with op.open('http://127.0.0.1:3003/',timeout=10) as response:html=response.read().decode()
assert '绩效考核' in html and '企业工作台' in html
report={'status':'preview_ready','url':'http://192.168.31.106:3003/#performance','backend_seconds':round(time.monotonic()-started,3),'payload_bytes':len(raw),'people':len(data['people']),'products':data['product_count'],'excluded':len(data['excluded_products']),'daily_rows_per_person':31,'backend_tests_passed':8,'frontend_build_passed':True,'browser_visual_verification':'blocked by browser URL identification failure','main_frontend_switched':False}
Path('/opt/monitor/maintenance/performance-20261031/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
