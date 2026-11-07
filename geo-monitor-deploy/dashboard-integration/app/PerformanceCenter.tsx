"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { PerformanceEntry } from "./PerformanceEntry";
import { PerformanceTrend } from "./PerformanceTrend";
import { PerformanceConfirmation } from "./PerformanceConfirmation";
import { beijingMonth } from "./beijingCalendar";
import { DailyTrafficCard } from "./DailyTrafficCard";

type Part = "traffic" | "budget" | "mention" | "values";
type Mention = { score: number | null; observed_items: number; target_items: number; applied_weight: number; models: Array<{
  model_id: string; model: string; weight: number; score: number | null; observed_items: number; target_items: number;
  items: Array<{ product: string; question: string; actual_rate: number; target_rate: number; attainment: number }>;
}> };
type Snapshot = { date: string; score: number | null; coefficient: number | null; provisional: boolean;
  scores: Record<Part, number | null>; contributions: Record<Part, number | null>;
  traffic: { actual: number; target: number; daily_target: number; observed_days: number; missing_days: string[]; latest_date: string | null; today_actual: number | null };
  budget: { monthly: number; planned: number | null; actual: number | null; latest_date: string | null; raw_score: number | null; floor: number; cap: number; checkpoint_days: number | null; month_days: number; daily_expense: number | null };
  mention: Mention;
  products: Array<{ product: string; priority: string; traffic_today: number | null; traffic_total: number; daily_target: number; monthly_budget: number; expense_total: number | null; expense_checkpoints: Record<string, number> }>;
};
type Person = { name: string; product_count: number; current: Snapshot; daily: Snapshot[] };
type Assessment = { month: string; as_of: string; max_as_of: string; generated_at: string; available_months: string[]; product_count: number;
  people: Person[]; notes: string[]; excluded_products: string[]; reconciliation: unknown[]; component_weights: Record<Part, number> };
const DEFAULT_PARTS: Array<[Part, string, number]> = [["traffic", "流量", 50], ["budget", "预算", 10], ["mention", "提及达成率", 30], ["values", "价值观", 10]];
const number = (v: number | null | undefined, digits = 1) => v == null ? "—" : v.toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
const percent = (v: number | null | undefined) => v == null ? "待补数据" : `${number(v)}%`;
const money = (v: number | null | undefined) => v == null ? "—" : `¥${number(v, 2)}`;
const tone = (v: number | null) => v == null ? "empty" : v >= 100 ? "met" : v >= 80 ? "near" : "below";
const shortDate = (v: string | null) => v ? `${Number(v.slice(5, 7))}/${Number(v.slice(8, 10))}` : "未提供";

export function PerformanceCenter({ apiBase }: { apiBase: string }) {
  const [month, setMonth] = useState(() => beijingMonth());
  const [cutoff, setCutoff] = useState("");
  const [payload, setPayload] = useState<Assessment | null>(null);
  const PARTS: Array<[Part, string, number]> = DEFAULT_PARTS.map(([key, label, weight]) => [key, label, payload?.component_weights?.[key] ?? weight]);
  const [selected, setSelected] = useState<string | null>(null);
  const [day, setDay] = useState("");
  const [dailyView, setDailyView] = useState<"chart" | "table">("chart");
  const [confirmationStatus, setConfirmationStatus] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [entryOpen, setEntryOpen] = useState(false);
  const [access, setAccess] = useState<{ user: string; can_edit: boolean; csrf?: string } | null>(null);
  const pending = useRef<AbortController | null>(null);
  const detail = useRef<HTMLElement>(null);
  const load = useCallback(async () => {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    const timeout = window.setTimeout(() => controller.abort("timeout"), 20000);
    setLoading(true);
    try {
      const params = new URLSearchParams({ month }); if (cutoff) params.set("as_of", cutoff);
      params.set("refresh", String(Date.now()));
      const response = await fetch(`${apiBase}/api/performance?${params}`, { cache: "no-store", signal: controller.signal });
      const value = await response.json();
      if (!response.ok) throw Error(value.error || "绩效数据暂时无法读取");
      if (controller.signal.aborted) return;
      setPayload(value); setError("");
    } catch (e) { if (!controller.signal.aborted || controller.signal.reason === "timeout") setError(controller.signal.reason === "timeout" ? "绩效读取超时，请重试" : e instanceof Error ? e.message : "绩效数据读取失败"); }
    finally { window.clearTimeout(timeout); if (pending.current === controller) { pending.current = null; setLoading(false); } }
  }, [apiBase, month, cutoff]);
  useEffect(() => {
    void load(); const timer = window.setInterval(() => { if (!document.hidden && !pending.current) void load(); }, 60000);
    return () => { window.clearInterval(timer); pending.current?.abort(); };
  }, [load]);
  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${apiBase}/api/performance-entry/access`, { cache: "no-store", signal: controller.signal })
      .then(async response => { if (response.ok && response.headers.get("Content-Type")?.includes("application/json")) setAccess(await response.json()); else setAccess(null); })
      .catch(() => { if (!controller.signal.aborted) setAccess(null); });
    return () => controller.abort();
  }, [apiBase]);
  const person = payload?.people.find(p => p.name === selected);
  const current = person?.daily.find(s => s.date === day) || person?.current;
  const available = payload?.people.filter(p => p.current.score !== null) || [];
  const average = available.length ? available.reduce((sum, p) => sum + p.current.score!, 0) / available.length : null;
  const open = (name: string) => { setSelected(name); setDay(""); requestAnimationFrame(() => detail.current?.scrollIntoView({ behavior: "smooth", block: "start" })); };
  return <div className="assessment-center">
    <section className="assessment-hero">
      <div><span className="assessment-eyebrow">GEO · 员工绩效</span>
        <div className="assessment-period">{payload ? <b>{payload.month} 考核月</b> : <span>正在读取考核数据…</span>}</div>
      </div>
      <div className="assessment-controls"><label>考核月份<select aria-label="绩效月份" disabled={entryOpen} value={month} onChange={e => { setMonth(e.target.value); setCutoff(""); setDay(""); }}>
        {Array.from(new Set([month, ...(payload?.available_months || [beijingMonth(), "2026-10"])])).sort().reverse().map(m => <option key={m} value={m}>{m}</option>)}</select></label>
        <label>截止日期<input aria-label="绩效截止日期" disabled={entryOpen} type="date" value={cutoff || payload?.as_of || ""} min={`${month}-01`} max={payload?.max_as_of || `${month}-31`} onChange={e => { setCutoff(e.target.value); setDay(""); }} /></label>
        <button onClick={() => void load()} disabled={loading}>{loading ? "更新中…" : "刷新绩效"}</button>
        {access?.can_edit && !entryOpen && <button className="performance-entry-open" onClick={() => setEntryOpen(true)}>录入数据</button>}
      </div>
    </section>
    {entryOpen && access?.can_edit && access.csrf && <PerformanceEntry apiBase={apiBase} month={month} csrf={access.csrf} onSaved={() => void load()} onClose={() => setEntryOpen(false)} />}
    {error && <p className="assessment-alert" role="alert">{error}。{payload ? `当前保留 ${payload.generated_at.slice(0, 19).replace("T", " ")} 的数据，请刷新后确认。` : "请点击刷新绩效重试。"}</p>}
    {!payload && !error && <div className="assessment-skeleton" role="status">正在汇总员工绩效与每日计算明细…</div>}
    {payload && <>
      <section className="assessment-stats" aria-label="绩效概览">
        <div><span>考核人员</span><strong>{payload.people.length}<small>人</small></strong></div>
        <div><span>纳入产品</span><strong>{payload.product_count}<small>个</small></strong></div>
        <div><span>团队参考绩效</span><strong>{number(average)}<small>%</small></strong></div>
        <div><span>考核构成</span><p>流量 <b>{payload.component_weights.traffic}%</b> · 预算 <b>{payload.component_weights.budget}%</b><br />提及率 <b>{payload.component_weights.mention}%</b> · 价值观 <b>{payload.component_weights.values}%</b></p></div>
      </section>
      <section className="assessment-cards" aria-label="员工绩效卡片">
        {payload.people.map(p => { const s = p.current; return <button key={p.name} type="button" className={`assessment-person ${tone(s.score)} ${selected === p.name ? "selected" : ""}`} aria-label={`查看${p.name}的每日绩效明细`} aria-pressed={selected === p.name} onClick={() => open(p.name)}>
          <span className="assessment-person-head"><span className="assessment-avatar">{p.name.slice(-1)}</span><span><b>{p.name}</b><small>{p.product_count} 个考核产品</small></span><em>{s.provisional ? "待补齐数据" : "数据齐全"}</em></span>
          <span className="assessment-big-score">{s.score === null ? "—" : number(s.score)}<small>{s.score === null ? "待补数据" : "%"}</small></span>
          <span className="assessment-score-label">累计参考绩效 <i>· 系数 {number(s.coefficient)}</i> · {confirmationStatus[p.name] || "确认状态读取中"}</span>
          <span className="assessment-parts">{PARTS.map(([key, label, weight]) => <span key={key}><small>{label} {weight}%</small><b>{s.scores[key] === null ? "—" : percent(s.scores[key])}</b><em>贡献 {number(s.contributions[key])} 分</em></span>)}</span>
          <span className="assessment-watermarks">流量 {shortDate(s.traffic.latest_date)} · 费用 {shortDate(s.budget.latest_date)} · GEO 截至 {shortDate(s.date)}</span>
          <span className="assessment-card-link">查看每日进展与计算明细 <b>↗</b></span>
        </button>; })}
      </section>
      <DailyTrafficCard key={payload.month} people={payload.people} month={payload.month} asOf={payload.as_of} />
      <section ref={detail}><PerformanceConfirmation apiBase={apiBase} month={payload.month} selected={selected} onStatus={setConfirmationStatus} /></section>
      {person && current && <section className="assessment-detail" aria-label={`${person.name}绩效明细`}>
        <header className="assessment-detail-heading"><div><span className="assessment-eyebrow">个人绩效明细</span><h2>{person.name}<small>{person.product_count} 个考核产品</small></h2><p>查看每天截至当日的累计变化，再核对流量、费用和模型的原始计算。</p></div><button onClick={() => setSelected(null)}>收起明细</button></header>
        <div className="assessment-view-switch" role="group" aria-label="每日绩效显示方式">
          <button type="button" aria-pressed={dailyView === "chart"} onClick={() => setDailyView("chart")}>折线图</button>
          <button type="button" aria-pressed={dailyView === "table"} onClick={() => setDailyView("table")}>表格</button>
        </div>
        {dailyView === "chart" ? <PerformanceTrend key={person.name} name={person.name} days={person.daily} selectedDate={current.date} onSelect={setDay} /> :
        <div className="assessment-table-wrap"><table className="assessment-daily-table"><caption>每日绩效进展 · 点击日期查看该日计算明细</caption><thead><tr><th>截至日期</th>{PARTS.map(([k, label, weight]) => <th key={k}>{label}<small>权重 {weight}%</small></th>)}<th>累计参考绩效</th><th>数据说明</th></tr></thead>
          <tbody>{person.daily.map(s => <tr key={s.date} className={s.date === current.date ? "active" : ""}><td><button aria-label={`查看${person.name}${s.date}计算明细`} onClick={() => setDay(s.date)}>{s.date}<span>查看计算 →</span></button></td>
            {PARTS.map(([k]) => <td key={k}>{s.scores[k] == null ? "—" : percent(s.scores[k])}<small>贡献 {number(s.contributions[k])} 分</small></td>)}
            <td><strong>{percent(s.score)}</strong><small>系数 {number(s.coefficient)}</small></td><td><small>流量至 {shortDate(s.traffic.latest_date)}<br />费用至 {shortDate(s.budget.latest_date)}</small>{s.provisional && <em>参考值 · 数据待补齐</em>}</td></tr>)}</tbody>
        </table></div>}
        <div className="assessment-calculation-title"><h3>{current.date} · 每一项怎么算</h3><span>截至当天的累计口径</span></div>
        <section className="assessment-equation" aria-label="综合绩效计算公式"><p>综合绩效 ＝ {PARTS.map(([k, label, weight], index) => <span key={k}>{index ? " ＋ " : ""}{label} {current.scores[k] == null ? "待补" : number(current.scores[k])} × {weight}%</span>)}</p><strong>＝ {percent(current.score)}</strong><small>绩效系数 {number(current.coefficient)}；价值观按已确认的100%计入。各项用完整精度相加后显示。</small></section>
        <div className="assessment-formulas">
          <article><span>01 / 流量 · {payload.component_weights.traffic}%</span><h3>{percent(current.scores.traffic)}</h3><p>累计搜索数 ÷ 有效日期应完成搜索数 × 100%</p><b>{number(current.traffic.actual, 0)} ÷（日目标 {number(current.traffic.daily_target, 0)} × {current.traffic.observed_days} 天）× 100%</b><small>当日搜索数：{number(current.traffic.today_actual, 0)}；流量数据至 {current.traffic.latest_date || "未提供"}。{current.traffic.missing_days.length ? `有 ${current.traffic.missing_days.length} 天未提供流量，未计作0。` : "流量日期齐全。"}</small></article>
          <article><span>02 / 预算 · {payload.component_weights.budget}%</span><h3>{percent(current.scores.budget)}</h3><p>节点计划预算 ÷ 节点累计花费 × 100%</p><b>{money(current.budget.monthly)} × {current.budget.checkpoint_days || "—"} ÷ {current.budget.month_days} ＝ {money(current.budget.planned)}<br />{money(current.budget.planned)} ÷ {money(current.budget.actual)} ＝ {percent(current.budget.raw_score)}</b><small>费用至 {current.budget.latest_date || "未提供"}；按该费用节点的时间进度计算，限制80%～150%。仅有累计节点，无法据此确定某一天实际花费。</small></article>
          <article><span>03 / 提及达成率 · {payload.component_weights.mention}%</span><h3>{percent(current.scores.mention)}</h3><p>实际提及率 ÷ 目标提及率 × 100%，单项最高200%</p><b>{current.mention.models.map(m => m.model + " " + m.weight + "%").join(" ＋ ")}</b><small>这是目标达成率；各产品的GEO实际提及率见下表。有效考核 {current.mention.observed_items}/{current.mention.target_items} 项；同一模型内按产品平均。</small></article>
          <article><span>04 / 价值观 · {payload.component_weights.values}%</span><h3>{percent(current.scores.values)}</h3><p>工作态度、主动性、响应速度、团队配合</p><b>100% × 10% ＝ 10 分</b><small>按你确认的“直接打满”执行，不从模型或流量推算。</small></article>
        </div>
        <h3 className="assessment-subheading">产品流量与费用核对</h3>
        <div className="assessment-table-wrap"><table className="assessment-products"><thead><tr><th>考核产品</th><th>当日搜索数</th><th>累计搜索数</th><th>每日目标</th><th>月预算</th><th>累计花费<small>至 {shortDate(current.budget.latest_date)}</small></th></tr></thead><tbody>{current.products.map(p => <tr key={p.product}><td>{p.product}<small>优先级 {p.priority}</small></td><td>{number(p.traffic_today, 0)}</td><td>{number(p.traffic_total, 0)}</td><td>{number(p.daily_target, 0)}</td><td>{money(p.monthly_budget)}</td><td>{money(p.expense_total)}</td></tr>)}</tbody></table></div>
        <details className="assessment-checkpoints"><summary>查看费用累计节点原始数据</summary><div className="assessment-table-wrap"><table><thead><tr><th>产品</th>{Object.keys(current.products[0]?.expense_checkpoints || {}).map(d => <th key={d}>{shortDate(d)}</th>)}</tr></thead><tbody>{current.products.map(p => <tr key={p.product}><td>{p.product}</td>{Object.entries(p.expense_checkpoints).map(([d, v]) => <td key={d}>{money(v)}</td>)}</tr>)}</tbody></table></div><p>这是各节点的累计花费，不将两个节点的差额平均分摊成每日费用。</p></details>
        <h3 className="assessment-subheading">提及率逐模型计算</h3>
        <div className="assessment-mention-models">{current.mention.models.map(m => <section key={m.model_id}><header><h4>{m.model}<small>权重 {m.weight}%</small></h4><strong>{percent(m.score)}</strong></header><p>模型分＝有效产品达成率平均；{m.observed_items}/{m.target_items} 项有有效数据。</p>
          {m.items.length ? <div className="assessment-table-wrap"><table><thead><tr><th>产品 / 监控问题</th><th>实际提及率</th><th>目标提及率</th><th>达成率（上限200%）</th></tr></thead><tbody>{m.items.map(i => <tr key={i.product}><td>{i.product}<small>{i.question}</small></td><td>{percent(i.actual_rate)}</td><td>{percent(i.target_rate)}</td><td>{percent(i.attainment)}</td></tr>)}</tbody></table></div> : <p>没有有效采样，保留待补状态，不记作0%。</p>}</section>)}</div>
      </section>}
      <details className="assessment-method"><summary>考核方案、系数档位与导入范围</summary><ul>{payload.notes.map(n => <li key={n}>{n}</li>)}</ul><p>完成率与系数：低于70% → 0.5；70%～80% → 0.8；80%～90% → 1；90%～95% → 1.5；95%～100% → 2；100%～105% → 2.5；105%～110% → 3；110%～115% → 3.5；115%～120% → 4；120%及以上 → 5。左边界包含，右边界不包含。</p><p>不纳入考核：{payload.excluded_products.join("、")}。</p><small>数据更新时间：{payload.generated_at.slice(0, 19).replace("T", " ")}（北京时间）</small></details>
    </>}
  </div>;
}
