from pathlib import Path
path=Path('geo-monitor-deploy/dashboard-integration/app/Dashboard.tsx')
text=path.read_text('utf-8-sig')
text=text.replace('import { CaptureControl } from "./CaptureControl";','import { CaptureControl } from "./CaptureControl";\nimport { CreationControl } from "./CreationControl";')
text=text.replace('"runs" | "control";','"runs" | "control" | "creation";')
text=text.replace('  generated_at: string;','  generated_at: string;\n  cache_status?: { state: string; message: string; generated_at: string };',1)
anchor='  { id: "control", label: "采集控制", hint: "问题、账号与任务", symbol: "▶" },'
assert anchor in text
text=text.replace(anchor,anchor+'\n  { id: "creation", label: "内容创作", hint: "GEO素材、审稿与成稿", symbol: "✎" },')
text=text.replace('    if (nextView === "control") {','    if (nextView === "creation") {\n      window.history.replaceState(null, "", "#creation");\n    } else if (nextView === "control") {',1)
text=text.replace('    } else if (window.location.hash.startsWith("#capture")) {','    } else if (window.location.hash.startsWith("#capture") || window.location.hash === "#creation") {',1)
text=text.replace('      if (window.location.hash.startsWith("#capture")) setView("control");','      if (window.location.hash.startsWith("#capture")) setView("control");\n      if (window.location.hash === "#creation") setView("creation");',1)
# Both operational tabs skip analytics, selectors, legacy data polling and cards.
text=text.replace('if (view === "control") {\n      setLoading(false);','if (view === "control" || view === "creation") {\n      setLoading(false);')
text=text.replace('view !== "control"','view !== "control" && view !== "creation"')
text=text.replace('view === "control" ? " capture-view"','(view === "control" || view === "creation") ? " capture-view"')
text=text.replace('<p>{view === "control" ? "按通道设置问题与轮数，管理采集任务并核对回传。" :','<p>{view === "creation" ? "使用GEO完整素材，管理创作、证据、审稿与Word成稿。" : view === "control" ? "按通道设置问题与轮数，管理采集任务并核对回传。" :')
text=text.replace('{view === "control" && (\n            <>','{view === "creation" && <CreationControl />}\n          {view === "control" && (\n            <>')
if '{view === "creation" && <CreationControl />}' not in text:
    anchor='          {view === "control" && ('
    assert anchor in text
    text=text.replace(anchor,'          {view === "creation" && <CreationControl />}\n'+anchor,1)
text=text.replace('· 第 {run.sequence} 轮','· 采集记录 #{run.sequence}')
anchor='        {view !== "control" && view !== "creation" && (\n          <div className="filterbar">'
assert anchor in text
text=text.replace(anchor,'        {view !== "control" && view !== "creation" && analytics.cache_status?.state !== "current" && analytics.generated_at && <p className="message" role="status">{analytics.cache_status?.message || "统计快照时间："} {analytics.generated_at}。刷新完成前请勿按此判断最新结果。</p>}\n'+anchor,1)
path.write_text(text,encoding='utf8')
