from pathlib import Path
p=Path('geo-monitor-deploy/panel.html')
s=p.read_text(encoding='utf8')
s=s.replace('<span>自动刷新 5 秒 · 时间均为北京时间</span>','<span id="dailySchedule">自动刷新 5 秒 · 时间均为北京时间</span>')
s=s.replace('models=data.models;csrf=data.csrf;',"models=data.models;csrf=data.csrf;if(data.schedule?.enabled)document.getElementById('dailySchedule').textContent='每天北京时间 '+data.schedule.time+' 启动 · 跑满设置轮数正常结束';")
p.write_text(s,encoding='utf8')
