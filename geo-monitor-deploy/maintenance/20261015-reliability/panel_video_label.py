from pathlib import Path
p=Path('geo-monitor-deploy/panel.html');s=p.read_text('utf-8')
s=s.replace('<label>去重 / 未取得完整结果</label>','<label id="exceptionLabel">去重 / 未取得完整结果</label>')
s=s.replace("$('exceptions').textContent=c.duplicates+' / '+c.unavailable;", "$('exceptions').textContent=c.duplicates+' / '+c.unavailable;$('exceptionLabel').textContent=m.id==='yuanbao'?'去重 / 仅视频回答':'去重 / 未取得完整结果';")
p.write_text(s,encoding='utf-8')
