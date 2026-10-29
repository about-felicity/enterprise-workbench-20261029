from pathlib import Path
p=Path('geo-monitor-deploy/deepseek_login.html');s=p.read_text(encoding='utf8')
s=s.replace("const screen=document", "const testing=location.pathname.includes('/deepseek_test/');\nconst screen=document",1)
needle="const mount=location.pathname.split('/api/')[0];"
assert needle in s
s=s.replace(needle,"""if(testing){
 document.title='DeepSeek · 独立手动测试';
 document.getElementById('heading').textContent='DeepSeek · 独立手动测试';
 document.querySelector('.hint').textContent='独立测试模拟器，所有问题由你手动发送。不会进入每日采集、GEO统计或创作素材；登录后保持投屏，每次投屏最长一小时。';
 textInput.placeholder='手动输入问题、手机号或验证码';
 const open=document.createElement('button');open.textContent='打开 / 重开测试投屏';open.id='testOpen';
 open.onclick=async()=>{open.disabled=true;try{const r=await fetch(prefix+'open',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Action-Id':key()},body:'{}'});if(!r.ok)throw Error('打开失败，请稍后重试');flow='';streamFlow='';message.textContent='正在启动测试投屏…'}catch(e){message.textContent=e.message}finally{open.disabled=false}};
 document.getElementById('message').before(open);
}
"""+needle,1)
s=s.replace("if(flow&&flow!==s.id){", "if(flow&&flow!==s.id&&!testing){",1)
s=s.replace("if(s.status==='ready'){finish();return}", "if(s.status==='ready'&&!testing){finish();return}",1)
s=s.replace("message.textContent=s.message||'正在建立scrcpy投屏…'", "message.textContent=testing&&['closed','failed'].includes(s.status)?'点击上方按钮打开测试投屏；账号数据会保留。':testing&&s.status==='waiting_login'?'手动测试投屏已连接；登录后不会自动关闭。':s.message||'正在建立scrcpy投屏…'",1)
p.write_text(s,encoding='utf8')
p=Path('geo-monitor-deploy/panel.html');s=p.read_text(encoding='utf8')
needle="footer.append(enable,node('span'"
assert needle in s
s=s.replace(needle,"const testLink=node('a','独立 DeepSeek 手动测试');testLink.href='/api/login/'+'deepseek_test/ui';testLink.target='_blank';testLink.rel='noopener';testLink.style.marginLeft='12px';footer.append(testLink);"+needle,1)
p.write_text(s,encoding='utf8')
