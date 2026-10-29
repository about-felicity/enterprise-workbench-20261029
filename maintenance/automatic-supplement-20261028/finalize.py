from pathlib import Path
p=Path('geo-monitor-deploy/creation/supplement.py');s=p.read_text('utf8');s=s.replace("  if any(v['blocked'] or v.get('recovery',{}).get('blocked') for v in original_progress):continue", "  if any(v['blocked'] or v.get('recovery',{}).get('blocked') for v in original_progress):\n   save(task,{**s,'status':'waiting_verification','message':'采集通道需要处理平台验证，保留原会话'})\n   continue")
p.write_text(s,encoding='utf8')
p=Path('geo-monitor-deploy/creation/studio.py');s=p.read_text('utf8').replace("if supplement.eligible(t,supplement.policy()) and extra.get('status')", "if state!='needs_attention' and supplement.eligible(t,supplement.policy()) and extra.get('status')");p.write_text(s,encoding='utf8')
