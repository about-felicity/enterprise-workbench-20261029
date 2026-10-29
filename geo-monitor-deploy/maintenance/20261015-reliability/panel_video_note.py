from pathlib import Path
p=Path('geo-monitor-deploy/panel.html');s=p.read_text('utf-8')
s=s.replace("if(c.updated_at)detail.push","if(c.nontext_observations)detail.push('原生视频回答 '+c.nontext_observations+' 次，审计回传 '+c.nontext_processed+'，不计正文成功');if(c.updated_at)detail.push")
p.write_text(s,encoding='utf-8')
