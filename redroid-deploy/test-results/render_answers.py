"""Render collected App records without modifying their contents."""
import json, html
from pathlib import Path
from urllib.parse import urlsplit

root=Path(__file__).parent
records=json.loads((root/'hpe14-all-answers.json').read_text(encoding='utf8'))
assert len({r['task_id'] for r in records})==len(records)
assert all(r['finished'] and r['body_markdown'].strip() for r in records)
sources=sum(len(r['sources']) for r in records)
citations=sum(len(r['citations']) for r in records)
esc=lambda value:html.escape(str(value),quote=True)
def link(url,title):
    if urlsplit(str(url)).scheme not in ('http','https'):
        return esc(title)
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(title)}</a>'

md=['# 豆包 App 真实采集结果',
    f'北京时间 2026-10-07 09:58 导出：{len(records)} 条完整回答、{sources} 条信源记录、{citations} 处引用。',
    '以下为 App 数据原样展示，含其返回的任务编号、重复来源和追踪参数；回答事实及链接可访问性未逐项审核。',
    '正文是回答文本；sources 是搜索信源卡片；citations 是正文引用，保留原始位置与文档编号。']
cards=[]
for i,r in enumerate(records,1):
    question=r.get('question',r['wire_question'].split('\n\n（采集任务编号')[0])
    md.extend([f'## {i}. {question}',f"任务编号：`{r['task_id']}`  | 请求编号：`{r['request_id']}`  | 完成：true",
               '### 完整正文',r['body_markdown'],'### 全部信源'])
    source_html=[]
    for s in r['sources']:
        title=s.get('title') or '无标题'
        md.extend([f"- 编号 {s.get('index')}：[ {title} ](<{s['url']}>)",f"  - 文档编号：`{s.get('doc_id')}`"])
        source_html.append(f'<li>{link(s["url"],title)}<div class="url">{esc(s["url"])}</div><small>编号 {esc(s.get("index"))} · doc_id {esc(s.get("doc_id"))}</small></li>')
    md.append('### 正文引用')
    citation_html=[]
    for c in r['citations']:
        title=c.get('title') or '无标题'
        md.extend([f"- [{title}](<{c['url']}>)；原始位置：`{c.get('pos')}`；文档编号：`{c.get('doc_id')}`",
                   f"  - 插入文本：{c.get('insert_text') or ''}",f"  - 原始摘要：{c.get('summary') or ''}"])
        citation_html.append(f'<li>{link(c["url"],title)}<div class="url">{esc(c["url"])}</div><small>原始位置 {esc(c.get("pos"))} · doc_id {esc(c.get("doc_id"))}</small><pre>{esc(c.get("summary") or "")}</pre></li>')
    md.extend(['### 搜索词', '\n'.join('- '+str(q) for q in r.get('search_queries',[])), '---'])
    search=esc(question+' '+r['body_markdown'])
    cards.append(f'''<details class="record" data-search="{search}" {'open' if i==1 else ''}>
<summary><span>{i:03d}</span> {esc(question)}<small>{len(r['sources'])} 条信源 · {len(r['citations'])} 处引用</small></summary>
<div class="content"><div class="meta">任务 {esc(r['task_id'])}<br>请求 {esc(r['request_id'])}<br>回答 {esc(r['answer_id'])} · finished=true</div>
<h3>完整正文（原始 Markdown）</h3><pre class="body">{esc(r['body_markdown'])}</pre>
<h3>全部信源</h3><ol>{''.join(source_html)}</ol>
<h3>正文引用与原始位置</h3><ol>{''.join(citation_html) or '<li>本条没有正文引用</li>'}</ol>
<h3>搜索词</h3><pre>{esc(json.dumps(r.get('search_queries',[]),ensure_ascii=False,indent=2))}</pre></div></details>''')
(root/'doubao-test-data.md').write_text('\n\n'.join(md),encoding='utf8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>豆包 App 真实采集数据</title>
<style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:16px/1.7 system-ui;background:#f5f7fb;color:#202938}h1{margin-bottom:4px}header{margin-bottom:24px}.toolbar{position:sticky;top:0;background:#f5f7fb;padding:12px 0;z-index:1}input{width:65%;padding:12px;border:1px solid #ccd3de;border-radius:8px}button{padding:10px;margin-left:8px;background:white;border:1px solid #ccd3de;border-radius:8px;cursor:pointer}details{background:white;border:1px solid #dce2ec;border-radius:10px;margin:12px 0}summary{padding:16px;cursor:pointer;font-weight:600}summary span{color:#4667b0;margin-right:10px}summary small{display:block;padding-left:42px;font-weight:400;color:#667085}.content{padding:0 22px 22px}.meta{font:12px/1.8 monospace;color:#667085;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.8 system-ui}.body{padding:18px;background:#f6f8fc;border-radius:8px}li{margin-bottom:18px}a{color:#245ac0}.url{font-size:12px;overflow-wrap:anywhere;color:#667085}small{color:#667085}h3{margin-top:28px}[hidden]{display:none}</style>
<header><h1>豆包 App 真实采集数据</h1><p>COUNT 条完整回答 · SOURCES 条信源 · CITATIONS 处引用</p><small>导出时间：北京时间 2026-10-07 09:58。原样保留正文、重复信源和引用参数，未逐项审核事实或链接可访问性。</small></header>
<div class="toolbar"><input id="search" placeholder="搜索问题或正文"><button id="expand">展开全部</button><button id="collapse">折叠全部</button><div id="count"></div></div>
CARDS
<script>const rows=[...document.querySelectorAll('.record')];document.getElementById('search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();for(const r of rows)r.hidden=!r.dataset.search.toLowerCase().includes(q);document.getElementById('count').textContent='显示 '+rows.filter(r=>!r.hidden).length+' / '+rows.length+' 条'});document.getElementById('expand').onclick=()=>rows.filter(r=>!r.hidden).forEach(r=>r.open=true);document.getElementById('collapse').onclick=()=>rows.forEach(r=>r.open=false);</script></html>'''
page=page.replace('COUNT',str(len(records))).replace('SOURCES',str(sources)).replace('CITATIONS',str(citations)).replace('CARDS',''.join(cards))
(root/'doubao-test-data.html').write_text(page,encoding='utf8')
print(f'Rendered {len(records)} answers; {sources} sources; {citations} citations')
