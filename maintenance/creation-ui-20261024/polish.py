from pathlib import Path
R=Path(__file__).resolve().parents[2]/'geo-monitor-deploy/creation';p=R/'panel.html';s=p.read_text('utf8')
s=s.replace("if(!operation)return false;","if(!operation||operation.finishing)return false;")
s=s.replace("const result=await request('control/'+name,body);clearInterval(operationTimer);", "const result=await request('control/'+name,body);clearInterval(operationTimer);operation.finishing=true;buttons();")
s=s.replace("csrf=data.csrf;connected=true;$('connection')", "csrf=data.csrf;connected=true;$('connectionNotice').hidden=true;$('connection')")
s=s.replace("if(!busy)message('暂时无法获取最新状态，已保留输入与进度，正在自动重连。',true);", "$('connectionNotice').hidden=false;")
s=s.replace('<div data-workspace="editor" hidden>', '<p id="connectionNotice" class="action-feedback" data-state="error" role="status" hidden>暂时无法获取最新状态，已保留输入与进度，正在自动重连。后台任务继续执行。</p><div data-workspace="editor" hidden>')
s=s.replace('#message{position:sticky;top:10px;z-index:20;box-shadow:0 4px 16px #19372f12;white-space:pre-line}', '#message{position:relative;top:auto;z-index:20;white-space:pre-line}#message[data-state="working"]{background:#f0f8f4;border-color:#c9ddd3}#message[data-state="success"]{background:#edf8f1;border-color:#c9ddd3;color:#14664f}#message[data-state="error"]{background:#fff2ed;border-color:#e6b8aa;color:#943c2c}')
s=s.replace("${state==='paused'?' · 已暂停，已完成进度保留':''}", "${state==='paused'?' · 已暂停，已完成进度保留':finished&&p.frequency==='daily'&&p.enabled?' · 本次已结束，后续仍按每日计划执行':''}")
p.write_bytes(s.replace('\n','\r\n').encode('utf8'));(R/'wizard.js').write_bytes(s[s.index("let activeView='tasks';"):s.index('</script>')].replace('\n','\r\n').encode('utf8'))
# Capture-only completion is terminal even with a stale pause bit.
p=R/'studio.py';s=p.read_text('utf8');s=s.replace("  elif t.get('paused'):state='paused'", "  elif p.get('task_type')=='capture_only' and progress and all(v['completed']>=target for v in progress):state='complete'\n  elif t.get('paused'):state='paused'")
p.write_bytes(s.replace('\n','\r\n').encode('utf8'))
