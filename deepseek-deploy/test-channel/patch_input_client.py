from pathlib import Path
p=Path('geo-monitor-deploy/deepseek_login.html');s=p.read_text(encoding='utf8')
start=s.index('function input(value)');end=s.index("screen.addEventListener('keydown'",start)
s=s[:start]+Path('deepseek-deploy/test-channel/input_client.js').read_text(encoding='utf8')+'\n'+s[end:]
s=s.replace("document.getElementById('reconnect').onclick=()=>{streamFlow='';connectStream()};","document.getElementById('reconnect').onclick=()=>{inputPaused=false;inputEvents=[];clearTimeout(inputTimer);inputTimer=null;streamFlow='';connectStream()};",1)
s=s.replace("flow=s.id||'';csrf=", "if(flow&&flow!==s.id){inputEvents=[];inputPaused=false}flow=s.id||'';csrf=",1)
p.write_text(s,encoding='utf8')
