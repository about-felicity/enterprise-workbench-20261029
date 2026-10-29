from pathlib import Path
path=Path('geo-monitor-deploy/creation/panel.html')
text=path.read_text('utf8')
old=":'运行中'} · 合格成稿"
new=":(j.day.status==='complete'?'已完成':'运行中')} · 合格成稿"
assert text.count(old)==1
path.write_text(text.replace(old,new),encoding='utf8')
