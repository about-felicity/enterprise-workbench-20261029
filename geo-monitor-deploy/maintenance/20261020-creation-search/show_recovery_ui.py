from pathlib import Path
base=Path(__file__).resolve().parents[2]/'creation'
for name in ('wizard.js','panel.html'):
 p=base/name;s=p.read_text(encoding='utf8')
 old='${capture}${creation}</div></div><div class="queue-controls">'
 new='${capture}${creation}${t?.error?`<small class="queue-note">${escape(t.error)}</small>`:\'\'}</div></div><div class="queue-controls">'
 assert s.count(old)==1,(name,s.count(old))
 s=s.replace(old,new)
 s=s.replace("${m.blocked?.kind?'需要登录或验证':'问题采集进度'}","${m.blocked?.kind?'需要登录或验证':m.recovery?.status==='cooling_down'?(m.recovery.kind==='verification'?'平台安全验证，冷却等待':'读取未完成，退避等待'):'问题采集进度'}")
 p.write_text(s,encoding='utf8')
