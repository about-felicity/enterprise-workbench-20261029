from pathlib import Path
root=Path(__file__).resolve().parents[3]
p=root/'geo-monitor-deploy/panel.html';s=p.read_text('utf-8-sig')
s=s.replace('id="totalModels">5</strong>','id="totalModels">6</strong>')
s=s.replace(" $('runningCount').textContent=", " $('totalModels').textContent=models.length;$('runningCount').textContent=")
s=s.replace("receiver_request_rejected:'回传参数被拒绝，需核对配置'", "receiver_request_rejected:'回传参数被拒绝，需核对配置',receiver_invalid_response:'接收服务返回格式异常，完整结果已保留'")
s=s.replace("refreshing=true;try{let r=await fetch('/api/panel',{cache:'no-store'});", "refreshing=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{let r=await fetch('/api/panel',{cache:'no-store',signal:controller.signal});")
s=s.replace("finally{refreshing=false}}", "finally{clearTimeout(timer);refreshing=false}}")
p.write_text(s,encoding='utf-8')
# Remove a redundant attribute: disabled state is managed in buttons().
p=root/'geo-monitor-deploy/creation/panel.html';s=p.read_text('utf-8-sig')
s=s.replace(" ${j.day.status==='complete'?'disabled':''}","")
s=s.replace("$ ('retryAction')", "$('retryAction')")
p.write_text(s,encoding='utf-8')
