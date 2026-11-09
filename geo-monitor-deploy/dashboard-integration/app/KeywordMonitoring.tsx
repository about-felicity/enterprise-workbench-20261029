"use client";

import { Fragment, useEffect, useState } from "react";
import { beijingDate } from "./beijingCalendar";
import { MonthlyKeywords, monthLastDay, planByQuestion, questionKey, useKeywordPlan } from "./MonthlyKeywords";
import type { Stats } from "./MonthlyKeywords";
import { DeltaIndicator, OwnedProductAverageCard, OwnedProductStateCard } from "./OwnedProductBoardCards";

const metrics = { recommend: "推荐率", mention: "正文提及率", first: "首推率" } as const;
const dailyLabels = { recommend: ["已上榜", "未上榜"], mention: ["已提及", "未提及"], first: ["已首推", "未首推"] } as const;
type Metric = keyof typeof metrics;
type Series = { stats: Stats; days: Record<string, Stats> };
type Row = {
  product: string; id: string; name: string; active: boolean; version: number;
  questions: string[]; platforms: Record<string, Series>;
};
type Board = { month: string; products: string[]; models: Record<string, string>; rows: Row[] };
type DaySample = [string, Stats];
type Plans = Map<string, ReturnType<typeof planByQuestion>>;

const timeFormat = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function shiftDay(day: string, offset: number) {
  const date = new Date(day + "T00:00:00Z");
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
}

function inPeriod(series: Series | undefined, day: string, cutoff: string): DaySample[] {
  return Object.entries(series?.days || {}).filter(([date]) => day ? date === day : date <= cutoff);
}

function totals(samples: DaySample[], metric: Metric) {
  let valid = 0, pending = 0, hits = 0, sum = 0, modelDays = 0;
  const days = new Set<string>();
  for (const [day, sample] of samples) {
    valid += sample.valid;
    pending += sample.pending;
    hits += sample[metric];
    if (sample.valid) {
      sum += sample[metric] / sample.valid;
      modelDays += 1;
      days.add(day);
    }
  }
  return { valid, pending, hits, modelDays, days: [...days].sort(), rate: modelDays ? sum * 100 / modelDays : null };
}

function delta(samples: DaySample[], all: DaySample[], day: string, cutoff: string, metric: Metric) {
  const previousDay = day ? shiftDay(day, -1) : "";
  const baseline = all.filter(([date]) => day ? date === previousDay : date < cutoff);
  const current = totals(samples, metric).rate;
  const previous = totals(baseline, metric).rate;
  return current === null || previous === null ? null : current - previous;
}

function PlatformCard({ series, day, cutoff, metric, remaining, unavailable }: {
  series?: Series; day: string; cutoff: string; metric: Metric; remaining: number; unavailable: number;
}) {
  const samples = inPeriod(series, day, cutoff);
  const result = totals(samples, metric);
  const rate = result.rate === null ? null : `${result.rate.toFixed(1)}%`;
  const change = rate === null ? null : <DeltaIndicator value={delta(samples, Object.entries(series?.days || {}), day, cutoff, metric)} />;
  const detail = [
    result.valid ? `${day ? "" : result.days.length + " 个有效日 · "}${result.hits}/${result.valid} 轮${metric === "recommend" ? "推荐" : ""}` : "",
    result.pending ? `${result.pending} 轮待分析` : "",
    remaining ? `今日还剩 ${remaining} 轮` : "",
    unavailable ? `今日未取得 ${unavailable} 轮` : "",
  ].filter(Boolean).join(" · ");
  if (!day) return <OwnedProductAverageCard rate={rate} detail={detail || "暂无有效数据"} change={change} />;
  const state = result.valid ? (result.hits ? "listed" : "not-listed") : result.pending ? "pending" : "not-collected";
  const label = result.valid ? dailyLabels[metric][result.hits ? 0 : 1]
    : result.pending ? "待分析" : remaining ? "今日待采" : unavailable ? "未取得" : "未采集";
  return <OwnedProductStateCard className={state} label={label} rate={rate} rateLabel={metrics[metric]}
    detail={detail || "当日暂无有效样本"} change={change} />;
}

function SampleDetails({ row, models, day, cutoff, metric }: {
  row: Row; models: [string, string][]; day: string; cutoff: string; metric: Metric;
}) {
  const items = models.flatMap(([id, label]) =>
    inPeriod(row.platforms[id], day, cutoff).map(([date, stats]) => ({ id, label, date, stats }))
  ).sort((a, b) => b.date.localeCompare(a.date));
  if (!items.length) return <p>所选日期范围内暂无回传明细。</p>;
  return <div className="keyword-detail-scroll"><table aria-label={`${row.name}采样明细`}>
    <thead><tr><th>采集日期</th><th>平台</th><th>{metrics[metric]}</th><th>命中 / 有效样本</th><th>待分析</th><th>最近回传</th></tr></thead>
    <tbody>{items.map(({ id, label, date, stats }) => {
      const receipt = stats.last_received_at ? new Date(stats.last_received_at * 1000) : null;
      return <tr key={id + date}>
        <td>{date}</td><td>{label}</td><td>{stats.valid ? (100 * stats[metric] / stats.valid).toFixed(1) + "%" : "—"}</td>
        <td>{stats[metric]} / {stats.valid}</td><td>{stats.pending}</td>
        <td>{receipt ? <time dateTime={receipt.toISOString()}>{beijingDate(receipt)} {timeFormat.format(receipt)}</time> : "—"}</td>
      </tr>;
    })}</tbody>
  </table></div>;
}

function KeywordTable({ rows, models, day, cutoff, metric, plans, expanded, onExpand }: {
  rows: Row[]; models: [string, string][]; day: string; cutoff: string; metric: Metric;
  plans?: Plans; expanded: string; onExpand: (id: string) => void;
}) {
  const monthly = !day;
  const countLabel = metric === "recommend" ? "累计推荐 / 有效回答" : "累计命中 / 有效回答";
  const firstColumns = monthly ? ["我的产品", "二级词与问句", "有数据天数", `平均每日${metrics[metric]}`, countLabel]
    : ["我的产品", "二级词与问句"];
  return <div className={`owned-product-table ${monthly ? "owned-product-summary-table" : "owned-product-daily-table"} keyword-board-table`}>
    <table aria-label={monthly ? "二级词月度有效日汇总" : "二级词每日平台表现"}>
      <colgroup>
        {(monthly ? [13, 15, 7, 9, 9] : [16, 15]).map((width, i) => <col key={i} style={{ width: width + "%" }} />)}
        {models.map(([id]) => <col key={id} />)}
      </colgroup>
      <thead><tr>{firstColumns.map(name => <th scope="col" key={name}>{name}</th>)}
        {models.map(([id, name]) => <th scope="col" key={id}>{name}{monthly ? " 日均" : ""}</th>)}
      </tr></thead>
      <tbody>{rows.map(row => {
        const id = (monthly ? "month:" : "day:") + row.product + ":" + row.id;
        const samples = models.flatMap(([platform]) => inPeriod(row.platforms[platform], day, cutoff));
        const result = monthly ? totals(samples, metric) : null;
        const dateRange = result?.days.length ? result.days[0] + (result.days.length > 1 ? " 至 " + result.days.at(-1) : "") : null;
        const details = <button type="button" className="keyword-detail-toggle" aria-expanded={expanded === id}
          onClick={() => onExpand(expanded === id ? "" : id)}>
          <span aria-hidden="true" />{expanded === id ? "收起明细" : "采样明细"}
        </button>;
        return <Fragment key={id}>
          <tr className="keyword-board-row">
            <th scope="row" data-label="我的产品" className="keyword-product"><b>{row.product}</b></th>
            <td data-label="二级词与问句" className="keyword-question">
              <div className="keyword-term-title">
                <b>{row.name}</b><span className="monthly-keyword-version">v{row.version}</span>
                {!row.active && <span className="monthly-keyword-state">已停用</span>}
              </div>
              <ul className="monthly-keyword-questions">{row.questions.map(q => <li key={q}>{q}</li>)}</ul>
              {!monthly && details}
            </td>
            {result && <>
              <td data-label="有数据天数"><b>{result.days.length} 天</b>{dateRange && <small>{dateRange}</small>}</td>
              <td data-label={`平均每日${metrics[metric]}`}>
                <strong className="owned-product-summary-rate">{result.rate === null ? "—" : `${result.rate.toFixed(1)}%`}</strong>
                {result.modelDays > 0 && <><small>{result.modelDays} 个有效平台日</small><DeltaIndicator value={delta(samples, samples, "", cutoff, metric)} /></>}
              </td>
              <td data-label={countLabel}><b>{result.hits} / {result.valid}</b>{details}</td>
            </>}
            {models.map(([model, name]) => {
              const slots = plans && row.active ? row.questions.map(q => plans.get(model)?.get(questionKey(q))) : [];
              const remaining = slots.reduce((sum, slot) => sum + (slot?.remaining ?? 0), 0);
              const unavailable = slots.reduce((sum, slot) => sum + (slot?.unavailable ?? 0), 0);
              return <td key={model} data-label={name + (monthly ? " 日均" : "")} className="owned-product-model-cell">
                <PlatformCard series={row.platforms[model]} day={day} cutoff={cutoff}
                  metric={metric} remaining={remaining} unavailable={unavailable} />
              </td>;
            })}
          </tr>
          {expanded === id && <tr className="keyword-sample-row"><td colSpan={firstColumns.length + models.length}>
            <SampleDetails row={row} models={models} day={day} cutoff={cutoff} metric={metric} />
          </td></tr>}
        </Fragment>;
      })}</tbody>
    </table>
  </div>;
}

export function KeywordMonitoring({ apiBase }: { apiBase: string }) {
  const today = beijingDate();
  const currentMonth = today.slice(0, 7);
  const [month, setMonth] = useState(currentMonth);
  const [selectedDay, setDay] = useState("");
  const [product, setProduct] = useState("");
  const [metric, setMetric] = useState<Metric>("recommend");
  const [tab, setTab] = useState<"monitor" | "manage">("monitor");
  const [manageProduct, setManageProduct] = useState("");
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [expanded, setExpanded] = useState("");
  const plan = useKeywordPlan(today, tab === "monitor" && month === currentMonth, refresh);
  const cutoff = month === currentMonth ? today : monthLastDay(month);

  useEffect(() => {
    if (tab !== "monitor") return;
    const controller = new AbortController();
    const params = new URLSearchParams({ month, model: "all" });
    fetch(`${apiBase}/api/performance-entry/monthly-keywords?${params}`, { cache: "no-store", signal: controller.signal })
      .then(async response => {
        const data = await response.json();
        if (!response.ok || !Array.isArray(data.rows)) throw new Error(data.error || "无法读取二级词看板");
        if (!controller.signal.aborted) { setBoard(data); setError(""); }
      })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message); });
    return () => controller.abort();
  }, [apiBase, month, refresh, tab]);

  const models = Object.entries(board?.models || {}).map(([id, name]): [string, string] =>
    [id, id === "wenxin" || id === "baidu" ? name + "卡片" : name]);
  const rows = (board?.month === month ? board.rows : []).filter(row => !product || row.product === product);
  const lastObserved = rows.reduce((latest, row) => {
    for (const series of Object.values(row.platforms)) {
      for (const date of Object.keys(series.days)) if (date <= cutoff && date > latest) latest = date;
    }
    return latest;
  }, "");
  const day = selectedDay || (month === currentMonth ? today : lastObserved || cutoff);
  const firstDay = month + "-01";
  const plans = new Map(models.map(([model]) => [model, planByQuestion(day === today ? plan : [], today, model)]));
  const hitsToday = rows.filter(row => models.some(([id]) => (row.platforms[id]?.days[day]?.[metric] || 0) > 0)).length;
  const manage = () => {
    setManageProduct(product || board?.rows[0]?.product || "");
    setTab("manage");
  };
  const selectDay = (date: string) => { setDay(date); setExpanded(""); };
  const table = { rows, models, cutoff, metric, expanded, onExpand: setExpanded };

  return <div className="keyword-monitor">
    <nav className="keyword-monitor-tabs" aria-label="二级词功能">
      <button type="button" aria-pressed={tab === "monitor"} onClick={() => setTab("monitor")}>监控看板</button>
      <button type="button" aria-pressed={tab === "manage"} onClick={manage}>词表管理</button>
    </nav>
    {tab === "manage" ? <MonthlyKeywords apiBase={apiBase} initialMonth={month} initialProduct={manageProduct} /> :
      <section className="panel monthly-keywords owned-product-board keyword-owned-board" aria-labelledby="keyword-matrix-title">
        <header className="monthly-keyword-header">
          <div>
            <h3 id="keyword-matrix-title">我的产品二级词每日上榜情况</h3>
            <p>推荐率按已分析的有效回答计算，日均只计入有有效样本的日期。北京时间，按当前问句版本统计。</p>
          </div>
          <button className="monthly-keyword-primary" type="button" onClick={manage}>管理二级词</button>
        </header>
        <div className="monthly-keyword-controls">
          <label>月份 <input type="month" value={month} onChange={event => {
            if (event.target.value) { setMonth(event.target.value); selectDay(""); setError(""); }
          }} /></label>
          <label>产品 <select aria-label="产品" value={product} onChange={event => { setProduct(event.target.value); setExpanded(""); }}>
            <option value="">全部产品</option>
            {board?.products.map(name => <option key={name}>{name}</option>)}
          </select></label>
          <label>统计指标 <select aria-label="统计指标" value={metric} onChange={event => setMetric(event.target.value as Metric)}>
            {Object.entries(metrics).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select></label>
          <button type="button" onClick={() => { setError(""); setRefresh(value => value + 1); }}>刷新数据</button>
          {rows.length > 0 && <button type="button" onClick={() => document.getElementById("keyword-daily-heading")?.scrollIntoView({ block: "start" })}>查看每日 ↓</button>}
          <a className="keyword-capture-link" href="#capture">采集进度 →</a>
        </div>
        {error && <p role="alert">{error}</p>}
        {board?.month !== month && !error && <p role="status">正在读取二级词看板…</p>}
        {board?.month === month && (rows.length ? <>
          <section className="owned-product-summary" aria-labelledby="keyword-monthly-heading">
            <div className="owned-product-summary-heading">
              <div><b id="keyword-monthly-heading">{month} 月度有效日汇总</b><small>先算各平台每日{metrics[metric]}，再对有效平台日取平均。</small></div>
              <span>{new Set(rows.map(row => row.product)).size} 个产品 · {rows.length} 个二级词</span>
            </div>
            <KeywordTable {...table} day="" />
          </section>
          <section className="owned-product-day keyword-daily-board" aria-labelledby="keyword-daily-heading">
            <div className="keyword-daily-heading">
              <h3 id="keyword-daily-heading"><time dateTime={day}>{day}</time><span>每日{metrics[metric]} · {hitsToday}/{rows.length} 个词有{metric === "recommend" ? "推荐" : "命中"}</span></h3>
              <div className="keyword-date-actions">
                <button type="button" disabled={day <= firstDay} onClick={() => selectDay(shiftDay(day, -1))}>前一天</button>
                <label>采集日期 <input aria-label="采集日期" type="date" value={day} min={firstDay} max={cutoff}
                  onChange={event => {
                    if (event.target.validity.valid && event.target.value.startsWith(month + "-")) selectDay(event.target.value);
                  }} /></label>
                <button type="button" disabled={day >= cutoff} onClick={() => selectDay(shiftDay(day, 1))}>后一天</button>
                {day !== today && month === currentMonth && <button type="button" onClick={() => selectDay(today)}>今天</button>}
              </div>
            </div>
            <KeywordTable {...table} day={day} plans={plans} />
          </section>
        </> : <div className="monthly-keyword-empty"><strong>所选范围未配置二级词</strong>
          <button type="button" onClick={manage}>前往词表管理</button></div>)}
      </section>}
  </div>;
}
