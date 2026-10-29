from pathlib import Path
import re
D=Path(__file__).resolve().parent
out=D/'app';out.mkdir(exist_ok=True)
s=(D/'before/Dashboard.tsx').read_text(encoding='utf-8')
s='import WorkbenchLogo from "./WorkbenchLogo";\n'+s
s=s.replace('<div>MI</div>','<div className="brand-mark"><WorkbenchLogo /></div>')
s=re.sub(r'\s*<a className="enterprise-entry"[^>]*>企业概率监控</a>','',s)
s=s.replace('{eyebrow && <span>{eyebrow}</span>}','')
s=s.replace('<small>{item.hint}</small>','')
s=re.sub(r'\s*<span>\s*MODEL INTELLIGENCE /\{" "\}.*?</span>','',s,flags=re.S)
s=re.sub(r'\s*<p>\{view === "creation" \? .*?</p>','',s)
s=s.replace('<span>分析 15 秒 · 状态 5 秒</span>','<span>最近更新</span>')
s=s.replace('<small>综合比较</small>','')
for text in ['当前筛选范围内完成轮次','衡量回答证据密度','当前筛选范围实际有回传的采集端']:
 s=s.replace('<small>'+text+'</small>','')
start=s.index('            <div>\n              <span>当前口径</span>')
end=s.index('            </div>',start)+len('            </div>')
s=s[:start]+s[end:]
(out/'Dashboard.tsx').write_text(s,encoding='utf-8')
s=(D/'before/PerformanceBoard.tsx').read_text(encoding='utf-8')
s=s.replace('<span>DAILY PERFORMANCE</span>','').replace('<p>{payload?.formula}</p>','')
s=s.replace('<em>文心双卡各50%</em>','')
s=s.replace('<p className="performance-note">','<details className="performance-rules"><summary>考核规则</summary><p className="performance-note">')
s=s.replace('{payload?.wenxin_scope}</p>','{payload?.wenxin_scope} {payload?.formula}</p></details>')
(out/'PerformanceBoard.tsx').write_text(s,encoding='utf-8')
s=(D/'before/globals.css').read_text(encoding='utf-8')
s+='''\n/* Compact workbench chrome. */
.brand > .brand-mark { background: none; box-shadow: none; border-radius: 0; color: #43c9aa; flex-shrink: 0; }
.workbench-logo { width: 43px; height: 43px; display: block; }
.sidebar nav button { min-height: 44px; }
.topbar { padding-top: 24px; padding-bottom: 24px; }
.topbar h1 { margin: 0; }
.performance-heading { align-items: center; }
.performance-heading h2 { margin-top: 0; }
.performance-rules { margin-top: 16px; color: var(--muted); font-size: 12px; }
.performance-rules > summary { cursor: pointer; width: fit-content; }
'''
(out/'globals.css').write_text(s,encoding='utf-8')
