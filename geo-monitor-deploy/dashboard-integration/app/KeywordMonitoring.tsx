"use client";

import { Fragment, useEffect, useState } from "react";
import { beijingDate } from "./beijingCalendar";
import { MonthlyKeywords, monthLastDay, planByQuestion, questionKey, useKeywordPlan } from "./MonthlyKeywords";
import type { Stats } from "./MonthlyKeywords";

const metrics = { mention: "正文提及率", recommend: "明确推荐率", first: "首推率" } as const;
type Metric = keyof typeof metrics;
type Series = { stats: Stats; days: Record<string, Stats> };
type Row = {
  product: string; id: string; name: string; active: boolean; version: number;
  questions: string[]; platforms: Record<string, Series>;
};
type Board = { month: string; products: string[]; models: Record<string, string>; rows: Row[] };
type DaySample = [string, Stats];

const timeFormat = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function precedingDay(day: string) {
  const date = new Date(day + "T00:00:00Z");
  date.setUTCDate(date.getUTCDate() - 1);
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
  return { valid, pending, hits, modelDays, days: days.size, rate: modelDays ? sum * 100 / modelDays : null };
}

function delta(samples: DaySample[], all: DaySample[], day: string, cutoff: string, metric: Metric) {
  const previousDay = day ? precedingDay(day) : "";
  const baseline = all.filter(([date]) => day ? date === previousDay : date < cutoff);
  const current = totals(samples, metric).rate;
  const previous = totals(baseline, metric).rate;
  return current === null || previous === null ? null : current - previous;
}

function Change({ value }: { value: number | null }) {
  if (value === null) return <small className="keyword-delta-missing">暂无前日基准</small>;
  const rounded = Math.round(value * 10) / 10;
  return <span className="keyword-delta" data-direction={Math.sign(rounded)}>
    较前日 {rounded > 0 ? "+" : ""}{rounded.toFixed(1)} 个百分点
  </span>;
}

function PlatformCell({ series, day, cutoff, metric, remaining, unavailable }: {
  series?: Series; day: string; cutoff: string; metric: Metric; remaining: number; unavailable: number;
}) {
  const samples = inPeriod(series, day, cutoff);
  const result = totals(samples, metric);
  const state = result.valid ? (day && !result.hits ? "miss" : "ready") : result.pending ? "pending" : "empty";
  const title = result.valid ? (day ? (result.hits ? "已命中" : "未命中") : "日均")
    : result.pending ? "待分析" : remaining ? "今日待采" : unavailable ? "今日未取得" : "未采集";
  return <div className="keyword-platform" data-state={state}>
    <div className="keyword-platform-value"><b>{title}</b><strong>{result.rate === null ? "—" : `${result.rate.toFixed(1)}%`}</strong></div>
    {result.valid > 0 && <small>{day ? "" : `${result.days} 天 · `}{result.hits}/{result.valid} 轮</small>}
    {result.pending > 0 && <small>{result.pending} 轮待分析</small>}
    {remaining > 0 && <small>今日还剩 {remaining} 轮</small>}
    {unavailable > 0 && <small>今日未取得 {unavailable} 轮</small>}
    {result.valid > 0 && <Change value={delta(samples, Object.entries(series?.days || {}), day, cutoff, metric)} />}
  </div>;
}

function SampleDetails({ row, models, day, cutoff, metric }: {
  row: Row; models: [string, string][]; day: string; cutoff: string; metric: Metric;
}) {
  const items = models.flatMap(([id, label]) =>
    inPeriod(row.platforms[id], day, cutoff).map(([date, stats]) => ({ id, label, date, stats }))
  ).sort((a, b) => b.date.localeCompare(a.date));
  if (!items.length) return <p>所选日期范围内暂无回传明细。</p>;
  return <div className="keyword-detail-scroll"><table aria-label={`${row.name}采样明细`}>
    <thead><tr><th>采集日期</th><th>平台</th><th>命中 / 有效样本</th><th>待分析</th><th>最近回传</th></tr></thead>
    <tbody>{items.map(({ id, label, date, stats }) => {
      const receipt = stats.last_received_at ? new Date(stats.last_received_at * 1000) : null;
      return <tr key={id + date}>
        <td>{date}</td><td>{label}</td><td>{stats[metric]} / {stats.valid}</td><td>{stats.pending}</td>
        <td>{receipt ? <time dateTime={receipt.toISOString()}>{beijingDate(receipt)} {timeFormat.format(receipt)}</time> : "—"}</td>
      </tr>;
    })}</tbody>
  </table></div>;
}

export function KeywordMonitoring({ apiBase }: { apiBase: string }) {
  const today = beijingDate();
  const currentMonth = today.slice(0, 7);
  const [month, setMonth] = useState(currentMonth);
  const [day, setDay] = useState("");
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

  const models = Object.entries(board?.models || {});
  const visible = (board?.month === month ? board.rows : []).filter(row => !product || row.product === product);
  const plans = new Map(models.map(([model]) => [
    model, planByQuestion(month === currentMonth && (!day || day === today) ? plan : [], today, model),
  ]));
  const rows = visible.map(row => {
    const samples = models.flatMap(([id]) => inPeriod(row.platforms[id], day, cutoff));
    const all = models.flatMap(([id]) => Object.entries(row.platforms[id]?.days || {}));
    return { row, result: totals(samples, metric), change: delta(samples, all, day, cutoff, metric) };
  });
  const manage = (name = product || board?.rows[0]?.product || "") => {
    setManageProduct(name);
    setTab("manage");
  };

  return <div className="keyword-monitor">
    <nav className="keyword-monitor-tabs" aria-label="二级词功能">
      <button type="button" aria-pressed={tab === "monitor"} onClick={() => setTab("monitor")}>监控看板</button>
      <button type="button" aria-pressed={tab === "manage"} onClick={() => manage()}>词表管理</button>
    </nav>
    {tab === "manage" ? <MonthlyKeywords apiBase={apiBase} initialMonth={month} initialProduct={manageProduct} /> :
      <section className="panel monthly-keywords" aria-labelledby="keyword-matrix-title">
        <header className="monthly-keyword-header">
          <div>
            <span className="monthly-keyword-eyebrow">GEO 监控 · 多平台</span>
            <h3 id="keyword-matrix-title">二级词多平台看板</h3>
            <p>按产品和实际问句对比各平台表现。有效样本完成分析后计入统计。</p>
          </div>
          <button className="monthly-keyword-primary" type="button" onClick={() => manage()}>管理二级词</button>
        </header>
        <div className="monthly-keyword-controls">
          <label>月份 <input type="month" value={month} onChange={event => {
            if (event.target.value) { setMonth(event.target.value); setDay(""); setExpanded(""); setError(""); }
          }} /></label>
          <label>采集日期 <input type="date" value={day} min={month + "-01"} max={cutoff} onChange={event => {
            if (!event.target.value || (event.target.validity.valid && event.target.value.startsWith(month + "-"))) {
              setDay(event.target.value); setExpanded("");
            }
          }} /></label>
          {day && <button type="button" onClick={() => { setDay(""); setExpanded(""); }}>看整月</button>}
          <label>产品 <select value={product} onChange={event => { setProduct(event.target.value); setExpanded(""); }}>
            <option value="">全部产品</option>
            {board?.products.map(name => <option key={name}>{name}</option>)}
          </select></label>
          <label>统计指标 <select value={metric} onChange={event => setMetric(event.target.value as Metric)}>
            {Object.entries(metrics).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select></label>
          <button type="button" onClick={() => { setError(""); setRefresh(value => value + 1); }}>刷新数据</button>
        </div>
        {error && <p role="alert">{error}</p>}
        {board?.month !== month && !error && <p role="status">正在读取二级词看板…</p>}
        {board?.month === month && <>
          <dl className="monthly-keyword-overview" aria-label="当前筛选汇总">
            <div><dt>监控产品</dt><dd>{new Set(rows.map(({ row }) => row.product)).size}<small> 个</small></dd></div>
            <div><dt>启用二级词</dt><dd>{rows.filter(({ row }) => row.active).length}<small> 个</small></dd></div>
            <div><dt>{day ? "当天" : "本月"}有有效样本的词</dt><dd>{rows.filter(({ result }) => result.valid).length}<small> 个</small></dd></div>
          </dl>
          <div className="monthly-keyword-guide">
            <p><strong>{day || month + " 整月"}</strong> · 北京时间。{day ? "综合为各有数据平台的平均。" : "日均按有有效样本的平台日等权计算。"}按当前问句版本统计。</p>
            <a href="#capture">查看采集进度 <span aria-hidden="true">→</span></a>
          </div>
          {!rows.length ? <div className="monthly-keyword-empty"><strong>所选范围未配置二级词</strong>
            <button type="button" onClick={() => manage()}>前往词表管理</button></div> :
            <div className="keyword-matrix"><table aria-label="二级词平台对比">
              <thead><tr>
                <th scope="col">我的产品</th><th scope="col">二级词与问句</th>
                <th scope="col">有效天数</th><th scope="col">{day ? "平台平均" : "日均"}{metrics[metric]}</th>
                <th scope="col">命中 / 有效回答</th>
                {models.map(([id, name]) => <th scope="col" key={id}>{name}</th>)}
              </tr></thead>
              <tbody>{rows.map(({ row, result, change }) => {
                const id = row.product + ":" + row.id;
                return <Fragment key={id}>
                  <tr className="keyword-matrix-row">
                    <th scope="row" className="keyword-product">{row.product}</th>
                    <td className="keyword-question"><strong>{row.name}</strong>
                      <span className="monthly-keyword-version">v{row.version}</span>
                      {!row.active && <span className="monthly-keyword-state">已停用</span>}
                      <ul className="monthly-keyword-questions">{row.questions.map(q => <li key={q}>{q}</li>)}</ul>
                    </td>
                    <td data-label="有效天数"><strong>{result.days} 天</strong></td>
                    <td data-label={metrics[metric]}><strong className="keyword-matrix-rate">{result.rate === null ? "—" : `${result.rate.toFixed(1)}%`}</strong>
                      {!day && result.modelDays > 0 && <small>{result.modelDays} 个有效平台日</small>}
                      {result.valid > 0 && <Change value={change} />}</td>
                    <td data-label="命中 / 有效回答"><strong>{result.hits} / {result.valid}</strong>
                      <button type="button" className="keyword-detail-toggle" aria-expanded={expanded === id}
                        onClick={() => setExpanded(expanded === id ? "" : id)}>{expanded === id ? "收起明细" : "采样明细"}</button></td>
                    {models.map(([model, name]) => {
                      const slots = row.active ? row.questions.map(q => plans.get(model)?.get(questionKey(q))) : [];
                      const remaining = slots.reduce((sum, slot) => sum + (slot?.remaining ?? 0), 0);
                      const unavailable = slots.reduce((sum, slot) => sum + (slot?.unavailable ?? 0), 0);
                      return <td key={model} data-label={name}><PlatformCell series={row.platforms[model]}
                        day={day} cutoff={cutoff} metric={metric} remaining={remaining} unavailable={unavailable} /></td>;
                    })}
                  </tr>
                  {expanded === id && <tr className="keyword-sample-row"><td colSpan={5 + models.length}>
                    <SampleDetails row={row} models={models} day={day} cutoff={cutoff} metric={metric} />
                  </td></tr>}
                </Fragment>;
              })}</tbody>
            </table></div>}
        </>}
      </section>}
  </div>;
}
