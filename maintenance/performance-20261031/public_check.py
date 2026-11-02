import json,re,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for url in ['http://127.0.0.1:3000/','https://1any.top/geo_monitor/','https://1any.top/geo_monitor/api/performance?month=2026-10']:
 try:
  with op.open(url,timeout=25) as r:
   html=r.read().decode('utf8','replace')
   print(json.dumps({'url':url,'final_url':r.url,'status':r.status,'bytes':len(html),'headers':{k:r.headers.get(k) for k in ['Content-Type','Cache-Control','Server']},'title':re.findall(r'<title[^>]*>(.*?)</title>',html,re.S),'headings':re.findall(r'<h[12][^>]*>(.*?)</h[12]>',html,re.S)[:3],'forms':re.findall(r'<form[^>]*action=["\']([^"\']+)',html),'has_performance':'绩效考核' in html,'login_words':[s for s in ['登录','验证码','login','password','访问密码'] if s in html]},ensure_ascii=False))
 except Exception as e:print(url,type(e).__name__,str(e))
