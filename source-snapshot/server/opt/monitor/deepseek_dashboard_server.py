import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "deepseek_refs_result.csv")
XLSX_PATH = os.path.join(BASE_DIR, "deepseek_refs_result.xlsx")
LOG_PATH = os.path.join(BASE_DIR, "deepseek_web_monitor.log")
ERR_LOG_PATH = os.path.join(BASE_DIR, "deepseek_web_monitor.err.log")
HOST = os.environ.get("DEEPSEEK_DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.environ.get("DEEPSEEK_DASHBOARD_PORT", "8766"))


def read_rows():
    if not os.path.exists(CSV_PATH):
        return []
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def safe_int(value, default=0):
    try:
        return int(str(value or "").strip())
    except Exception:
        return default


def file_info(path):
    if not os.path.exists(path):
        return {"exists": False, "mtime": "", "size": 0}
    stat = os.stat(path)
    return {
        "exists": True,
        "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "size": stat.st_size,
    }


def log_tail(path, max_lines=80):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return [line.rstrip("\n") for line in f.readlines()[-max_lines:]]
    except Exception as exc:
        return ["read log failed: " + repr(exc)]


def host_of(url):
    return urlparse(url or "").netloc.lower().split(":")[0]


def source_label(row):
    domain = (row.get("domain") or host_of(row.get("href"))).lower()
    title = row.get("title") or ""
    if "douyin" in domain or "iesdouyin" in domain:
        return "视频 | 抖音"
    if "taobao" in domain:
        return "商品页 | 淘宝"
    if "tmall" in domain:
        return "商品页 | 天猫"
    if "jd." in domain or domain.endswith("jd.com"):
        return "商品页 | 京东"
    if "hktvmall" in domain:
        return "商品页 | HKTVmall"
    if "sina" in domain:
        return "文章 | 新浪"
    if "sxxynews" in domain:
        return "文章 | 咸阳新闻网"
    if "hdhospital" in domain:
        return "官网 | 北京市海淀医院"
    if "dayi.org.cn" in domain:
        return "平台 | 医问医答"
    if "matsukiyo" in domain:
        return "商品页 | 松本清"
    if "nurse.org.hk" in domain:
        return "商品页 | 香港护士协会商城"
    if title.startswith("- "):
        return "引用链接 | " + (domain or "未知域名")
    return domain or "未知域名"


def row_question(row):
    return row.get("question") or row.get("chat_title") or "未识别问题"


def rows_for_question(rows, question):
    if not question or question == "全部问题":
        return rows
    return [row for row in rows if row_question(row) == question]


def counter_items(counter, limit=None):
    rows = counter.most_common(limit) if limit else counter.most_common()
    return [{"name": name, "count": count} for name, count in rows]


def build_question_stats(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row_question(row)].append(row)

    result = []
    for question, items in grouped.items():
        runs = {safe_int(row.get("run_no")) for row in items if safe_int(row.get("run_no"))}
        links = {row.get("href") for row in items if row.get("href")}
        latest_run = max(runs) if runs else 0
        latest_time = ""
        for row in items:
            if safe_int(row.get("run_no")) == latest_run:
                latest_time = row.get("run_time") or latest_time
        result.append({
            "question": question,
            "refs": len(items),
            "unique_links": len(links),
            "runs": len(runs),
            "latest_run_no": latest_run,
            "latest_run_time": latest_time,
        })
    result.sort(key=lambda x: (x["latest_run_no"], x["refs"]), reverse=True)
    return result


def build_daily_question_stats(rows):
    grouped = defaultdict(list)
    for row in rows:
        date = (row.get("run_time") or "")[:10] or "未知日期"
        grouped[(date, row_question(row))].append(row)

    result = []
    for (date, question), items in grouped.items():
        runs = {safe_int(row.get("run_no")) for row in items if safe_int(row.get("run_no"))}
        links = {row.get("href") for row in items if row.get("href")}
        source_counter = Counter(source_label(row) for row in items)
        result.append({
            "date": date,
            "question": question,
            "refs": len(items),
            "unique_links": len(links),
            "runs": len(runs),
            "top_sources": counter_items(source_counter, 8),
        })
    result.sort(key=lambda x: (x["date"], x["question"]), reverse=True)
    return result


def build_stats(question=""):
    rows = read_rows()
    questions = build_question_stats(rows)
    latest_run_no = max((safe_int(row.get("run_no")) for row in rows), default=0)
    latest_rows = [row for row in rows if safe_int(row.get("run_no")) == latest_run_no]
    latest_question = row_question(latest_rows[0]) if latest_rows else (questions[0]["question"] if questions else "")
    selected = question or latest_question or "全部问题"
    scoped = rows_for_question(rows, selected)

    by_domain = Counter((row.get("domain") or host_of(row.get("href")) or "未知域名") for row in scoped)
    by_source = Counter(source_label(row) for row in scoped)
    by_date = Counter((row.get("run_time") or "")[:10] or "未知日期" for row in scoped)
    run_numbers = {safe_int(row.get("run_no")) for row in scoped if safe_int(row.get("run_no"))}
    unique_links = {row.get("href") for row in scoped if row.get("href")}

    latest_items = [{
        "index": row.get("index"),
        "title": row.get("title"),
        "href": row.get("href"),
        "domain": row.get("domain") or host_of(row.get("href")),
        "source": source_label(row),
    } for row in latest_rows]

    return {
        "ok": True,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "csv": file_info(CSV_PATH),
        "xlsx": file_info(XLSX_PATH),
        "selected_question": selected,
        "latest_question": latest_question,
        "questions": questions,
        "daily_questions": build_daily_question_stats(rows),
        "question_count": len(questions),
        "total_runs": len(run_numbers),
        "total_refs": len(scoped),
        "unique_links": len(unique_links),
        "latest_run_no": latest_run_no,
        "latest_run_time": latest_rows[0].get("run_time") if latest_rows else "",
        "latest_chat_title": latest_rows[0].get("chat_title") if latest_rows else "",
        "latest_refs": len(latest_rows),
        "latest_expected_count": latest_rows[0].get("expected_count") if latest_rows else "",
        "by_source": counter_items(by_source),
        "by_domain": counter_items(by_domain),
        "by_date": counter_items(by_date),
        "latest_items": latest_items,
        "log_tail": log_tail(LOG_PATH, 80),
        "err_tail": log_tail(ERR_LOG_PATH, 40),
    }


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DeepSeek 信源监控</title>
  <style>
    :root{--bg:#f4f7f2;--card:#fff;--text:#14211b;--muted:#66736d;--green:#169978;--green2:#55c7aa;--line:#dde8e2}
    *{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at top left,#e6fff3,transparent 32rem),var(--bg);color:var(--text);font-family:"Microsoft YaHei UI","Segoe UI",sans-serif}
    .wrap{max-width:1380px;margin:0 auto;padding:24px}.top{display:flex;justify-content:space-between;gap:16px;margin-bottom:18px}h1{margin:0;font-size:28px}.sub{color:var(--muted);font-size:13px}.pill{display:inline-flex;gap:8px;align-items:center;padding:8px 12px;border-radius:999px;background:#e8f5ef;color:#096b55;font-size:13px}.dot{width:9px;height:9px;border-radius:99px;background:var(--green);box-shadow:0 0 0 5px rgba(22,153,120,.12)}
    .card{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 14px 40px rgba(32,66,52,.08)}.metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin-bottom:14px}.metric-label{color:var(--muted);font-size:13px}.metric-value{font-size:26px;font-weight:800;margin-top:6px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.section-title{font-size:17px;font-weight:800;margin-bottom:12px;display:flex;justify-content:space-between;gap:12px}
    select{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:white;min-width:420px;font-size:14px}.bar-row{display:grid;grid-template-columns:minmax(180px,340px) 1fr 58px;gap:12px;align-items:center;margin:10px 0;padding:7px 10px;border-radius:12px;transition:background .16s ease,box-shadow .16s ease,transform .16s ease}.bar-row:hover{background:rgba(22,153,120,.08);box-shadow:inset 3px 0 0 rgba(22,153,120,.42);transform:translateX(2px)}.bar-name{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.bar-shell{height:12px;border-radius:99px;background:#e3ece7;overflow:hidden}.bar-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--green),var(--green2));min-width:2%}.bar-count{text-align:right;font-variant-numeric:tabular-nums}
    .table-wrap{overflow:auto;max-height:440px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;vertical-align:top}tbody tr{transition:background .14s ease,box-shadow .14s ease}tbody tr:hover{background:rgba(22,153,120,.075);box-shadow:inset 3px 0 0 rgba(22,153,120,.45)}th{position:sticky;top:0;background:#f6fbf8;z-index:1}a{color:#087f67;text-decoration:none}.log{white-space:pre-wrap;background:#12211b;color:#c8f7e6;border-radius:14px;padding:12px;max-height:380px;overflow:auto;font-family:Consolas,monospace;font-size:12px}.empty{color:var(--muted);padding:18px;text-align:center}.daily-card{border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0;background:#fbfffd;transition:background .16s ease,border-color .16s ease,box-shadow .16s ease}.daily-card:hover{background:#fff;border-color:rgba(22,153,120,.32);box-shadow:0 12px 30px rgba(32,66,52,.09)}.daily-title{font-weight:800}.daily-meta{color:var(--muted);font-size:13px;margin-top:4px}.chip{display:inline-block;margin:6px 6px 0 0;padding:4px 8px;border-radius:999px;background:#e8f5ef;color:#096b55;font-size:12px}
    @media(max-width:980px){.metrics{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}select{min-width:0;width:100%}.top{flex-direction:column}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top"><div><h1>DeepSeek 信源实时监控</h1><div class="sub">多问题按天统计，每 2 秒刷新。</div></div><div class="pill"><span class="dot"></span><span id="status">连接中...</span></div></div>
    <div class="card" style="margin-bottom:14px"><div class="section-title">按问题筛选 <span id="fileInfo" class="sub"></span></div><select id="questionSelect"></select></div>
    <section class="metrics">
      <div class="card"><div class="metric-label">当前范围轮次</div><div class="metric-value" id="totalRuns">-</div></div>
      <div class="card"><div class="metric-label">当前范围链接</div><div class="metric-value" id="totalRefs">-</div></div>
      <div class="card"><div class="metric-label">当前范围去重</div><div class="metric-value" id="uniqueLinks">-</div></div>
      <div class="card"><div class="metric-label">最新轮次</div><div class="metric-value" id="latestRun">-</div></div>
      <div class="card"><div class="metric-label">最新抓取</div><div class="metric-value" id="latestRefs">-</div></div>
      <div class="card"><div class="metric-label">问题数量</div><div class="metric-value" id="questionCount">-</div></div>
    </section>
    <section class="grid"><div class="card"><div class="section-title">媒体 / 平台 / 类型（全部）</div><div id="sourceBars"></div></div><div class="card"><div class="section-title">域名（全部）</div><div id="domainBars"></div></div></section>
    <section class="grid"><div class="card"><div class="section-title">按日期</div><div id="dateBars"></div></div><div class="card"><div class="section-title">运行日志</div><div class="log" id="logTail">暂无日志</div></div></section>
    <section class="card" style="margin-top:14px"><div class="section-title">每天每个问题统计</div><div id="dailyQuestions"></div></section>
    <section class="card" style="margin-top:14px"><div class="section-title">最新一轮明细 <span class="sub" id="latestInfo"></span></div><div class="table-wrap"><table><thead><tr><th>#</th><th>标题/引用</th><th>信源</th><th>域名</th><th>链接</th></tr></thead><tbody id="latestRows"></tbody></table></div></section>
  </div>
  <script>
    let selectedQuestion = "";
    const $ = id => document.getElementById(id);
    const esc = s => String(s ?? "").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    const setText = (id, value) => $(id).textContent = value ?? "-";
    const scrollSelector = ".table-wrap, .log";
    function captureScrollState(){return{windowX:window.scrollX,windowY:window.scrollY,nodes:Array.from(document.querySelectorAll(scrollSelector)).map((el,index)=>({index,top:el.scrollTop,left:el.scrollLeft}))}}
    function restoreScrollState(state){if(!state)return; requestAnimationFrame(()=>{Array.from(document.querySelectorAll(scrollSelector)).forEach((el,index)=>{const item=state.nodes.find(node=>node.index===index); if(item){el.scrollTop=item.top; el.scrollLeft=item.left}}); window.scrollTo(state.windowX,state.windowY)})}
    function bars(id, rows){const root=$(id); if(!rows||!rows.length){root.innerHTML='<div class="empty">暂无数据</div>';return} const max=Math.max(...rows.map(r=>r.count||0),1); root.innerHTML=rows.map(r=>{const w=Math.max(2,Math.round((r.count||0)/max*100)); return `<div class="bar-row"><div class="bar-name" title="${esc(r.name)}">${esc(r.name)}</div><div class="bar-shell"><div class="bar-fill" style="width:${w}%"></div></div><div class="bar-count">${esc(r.count)}</div></div>`}).join("")}
    function renderQuestions(data){const select=$("questionSelect"); const questions=data.questions||[]; const options=[{question:"全部问题",refs:data.total_refs||0,unique_links:data.unique_links||0,runs:data.total_runs||0},...questions]; select.innerHTML=options.map(q=>`<option value="${esc(q.question)}">${esc(q.question)}（${q.refs||0} 条 / ${q.unique_links||0} 链接 / ${q.runs||0} 轮）</option>`).join(""); select.value=selectedQuestion||data.selected_question||"全部问题"}
    function latestRows(rows){if(!rows||!rows.length){$("latestRows").innerHTML='<tr><td colspan="5" class="empty">暂无最新轮次数据</td></tr>';return} $("latestRows").innerHTML=rows.map(r=>`<tr><td>${esc(r.index)}</td><td>${esc(r.title)}</td><td>${esc(r.source)}</td><td>${esc(r.domain)}</td><td><a href="${esc(r.href)}" target="_blank" rel="noreferrer">打开</a></td></tr>`).join("")}
    function dailyQuestions(rows){const root=$("dailyQuestions"); if(!rows||!rows.length){root.innerHTML='<div class="empty">暂无每日问题数据</div>';return} root.innerHTML=rows.map(r=>`<div class="daily-card"><div class="daily-title">${esc(r.date)} | ${esc(r.question)}</div><div class="daily-meta">${esc(r.runs)} 轮 / ${esc(r.refs)} 条 / ${esc(r.unique_links)} 去重链接</div><div>${(r.top_sources||[]).map(s=>`<span class="chip">${esc(s.name)} ${esc(s.count)}</span>`).join("")}</div></div>`).join("")}
    async function refresh(){try{const q=selectedQuestion?"&question="+encodeURIComponent(selectedQuestion):""; const res=await fetch("/api/stats?_="+Date.now()+q,{cache:"no-store"}); const data=await res.json(); const scrollState=captureScrollState(); renderQuestions(data); setText("status","在线，刷新于 "+data.generated_at); setText("totalRuns",data.total_runs); setText("totalRefs",data.total_refs); setText("uniqueLinks",data.unique_links); setText("latestRun",data.latest_run_no||"-"); setText("latestRefs",`${data.latest_refs}/${data.latest_expected_count||"?"}`); setText("questionCount",data.question_count); setText("fileInfo",data.csv.exists?`CSV 更新：${data.csv.mtime}`:"CSV 尚未生成"); setText("latestInfo",`标题：${data.latest_chat_title||"-"}，时间：${data.latest_run_time||"-"}`); bars("sourceBars",data.by_source||[]); bars("domainBars",data.by_domain||[]); bars("dateBars",data.by_date||[]); dailyQuestions(data.daily_questions||[]); latestRows(data.latest_items||[]); const err=(data.err_tail||[]).join("\n"); $("logTail").textContent=(data.log_tail||[]).join("\n")+(err?"\n\n---ERR---\n"+err:""); restoreScrollState(scrollState)}catch(err){setText("status","连接失败："+err.message)}}
    $("questionSelect").addEventListener("change", e => { selectedQuestion=e.target.value; refresh(); });
    refresh(); setInterval(refresh,2000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def send_bytes(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path.startswith("/api/stats"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            question = (params.get("question") or [""])[0]
            self.send_bytes(json.dumps(build_stats(question), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        if self.path in ("/", "/index.html"):
            self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        self.send_bytes(b"not found", "text/plain; charset=utf-8", 404)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("DeepSeek dashboard: http://%s:%s" % (HOST, PORT), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
