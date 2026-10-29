from pathlib import Path
p=Path('geo-monitor-deploy/creation/studio.py');s=p.read_text('utf8');needle="   extra=supplement.state(t)";s=s.replace(needle,needle+"\n   if state=='complete' and extra.get('status')=='complete':reason=''",1);p.write_text(s,encoding='utf8')
