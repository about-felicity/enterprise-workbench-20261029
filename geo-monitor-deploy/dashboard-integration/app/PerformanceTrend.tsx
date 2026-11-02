"use client";
import React, { useMemo, useState } from "react";

type Part = "traffic" | "budget" | "mention" | "values";
type Daily = { date: string; score: number | null; scores: Record<Part, number | null>; provisional: boolean };
const SERIES = [
  { key: "total", label: "累计绩效", color: "#127a61" },
  { key: "traffic", label: "流量", color: "#3478c7" },
  { key: "budget", label: "预算", color: "#bc841e" },
  { key: "mention", label: "提及达成率", color: "#8c60bc" },
  { key: "values", label: "价值观", color: "#7d8f95" },
] as const;
type Key = typeof SERIES[number]["key"];
const value = (d: Daily, key: Key) => key === "total" ? d.score : d.scores[key];
const display = (n: number | null) => n == null ? "待补数据" : n.toLocaleString("zh-CN", { maximumFractionDigits: 1 }) + "%";
const short = (date: string) => Number(date.slice(5, 7)) + "/" + Number(date.slice(8, 10));

export function PerformanceTrend({ days, selectedDate, onSelect, name }: { days: Daily[]; selectedDate: string; onSelect: (date: string) => void; name: string }) {
  const sorted = useMemo(() => [...days].sort((a, b) => a.date.localeCompare(b.date)), [days]);
  const [visible, setVisible] = useState<Key[]>(SERIES.map(s => s.key));
  const [hovered, setHovered] = useState<string | null>(null);
  const selected = Math.max(0, sorted.findIndex(d => d.date === selectedDate));
  const hoverIndex = hovered ? sorted.findIndex(d => d.date === hovered) : -1;
  const activeIndex = hoverIndex < 0 ? selected : hoverIndex;
  const active = sorted[activeIndex];
  if (!active) return null;
  const W = 1000, H = 282, left = 57, right = 22, top = 18, bottom = 34;
  const plotW = W - left - right, plotH = H - top - bottom;
  const maximum = Math.max(100, ...sorted.flatMap(d => visible.map(key => value(d, key) ?? 0)));
  const ceiling = Math.ceil(maximum / 25) * 25;
  const x = (i: number) => left + (sorted.length === 1 ? plotW / 2 : i * plotW / (sorted.length - 1));
  const y = (n: number) => top + plotH * (1 - n / ceiling);
  const move = (step: number) => onSelect(sorted[Math.max(0, Math.min(sorted.length - 1, selected + step))].date);
  const toggle = (key: Key) => setVisible(old => old.includes(key) ? old.length > 1 ? old.filter(k => k !== key) : old : [...old, key]);
  return <section className="performance-trend" aria-label={name + "每日绩效折线图"}>
    <header><div><h3>每日绩效趋势</h3><p>点击图中日期查看计算明细</p></div><label>查看日期<select aria-label="选择绩效计算日期" value={selectedDate} onChange={e => onSelect(e.target.value)}>{sorted.map(d => <option key={d.date} value={d.date}>{d.date}</option>)}</select></label></header>
    <div className="performance-trend-legend" aria-label="图表指标">{SERIES.map(s => <button type="button" key={s.key} aria-pressed={visible.includes(s.key)} onClick={() => toggle(s.key)} style={{ opacity: visible.includes(s.key) ? 1 : .4 }}><i style={{ background: s.color }} />{s.label}</button>)}</div>
    <div className="performance-trend-scroll">
      <svg viewBox={"0 0 " + W + " " + H} role="group" aria-label={name + "绩效趋势，左右方向键选择日期"} tabIndex={0} onPointerLeave={() => setHovered(null)} onKeyDown={e => {
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); setHovered(null); move(e.key === "ArrowLeft" ? -1 : 1); }
        if (e.key === "Home" || e.key === "End") { e.preventDefault(); setHovered(null); onSelect(sorted[e.key === "Home" ? 0 : sorted.length - 1].date); }
      }}>
        <title>{name + "每日绩效趋势"}</title><desc>横轴为日期，纵轴为截至当日的累计达成百分比。缺失数据断线。左右方向键切换所选日期。</desc>
        {Array.from({ length: 5 }, (_, i) => ceiling * i / 4).map(tick => <g key={tick}><line x1={left} x2={W - right} y1={y(tick)} y2={y(tick)} stroke="#e7efeb" /><text x={left - 10} y={y(tick) + 4} textAnchor="end">{Number(tick.toFixed(1))}%</text></g>)}
        <line x1={left} x2={W - right} y1={y(100)} y2={y(100)} stroke="#96aea3" strokeDasharray="5 5" />
        {sorted.map((d, i) => i === 0 || i === sorted.length - 1 || i % Math.max(1, Math.ceil(sorted.length / 8)) === 0 ? <text key={d.date} x={x(i)} y={H - 10} textAnchor="middle">{short(d.date)}</text> : null)}
        <line x1={x(selected)} x2={x(selected)} y1={top} y2={H - bottom} stroke="#127a61" opacity=".35" strokeDasharray="4 4" />
        {SERIES.filter(s => visible.includes(s.key)).map(series => {
          let connected = false;
          const path = sorted.map((d, i) => {
            const n = value(d, series.key); if (n == null) { connected = false; return ""; }
            const segment = (connected ? "L" : "M") + x(i).toFixed(2) + "," + y(n).toFixed(2); connected = true; return segment;
          }).join(" ");
          return <g key={series.key}><path data-series={series.key} d={path} fill="none" stroke={series.color} strokeWidth={series.key === "total" ? 3.2 : 1.8} strokeDasharray={series.key === "values" ? "5 4" : undefined} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            {sorted.map((d, i) => { const n = value(d, series.key); return n == null ? null : <circle key={d.date} cx={x(i)} cy={y(n)} r={i === activeIndex ? 4.5 : sorted.length === 1 ? 3 : 1.7} fill={i === activeIndex ? "#fff" : series.color} stroke={series.color} strokeWidth={i === activeIndex ? 2 : 0} />; })}
          </g>;
        })}
        {hovered && activeIndex !== selected && <line x1={x(activeIndex)} x2={x(activeIndex)} y1={top} y2={H - bottom} stroke="#8caaa0" strokeDasharray="3 4" />}
        {sorted.map((d, i) => {
          const start = i === 0 ? left - 10 : (x(i - 1) + x(i)) / 2;
          const end = i === sorted.length - 1 ? W - right + 10 : (x(i) + x(i + 1)) / 2;
          return <rect key={d.date} x={start} y={top} width={Math.max(1, end - start)} height={plotH} fill="transparent" className="performance-trend-hit" onPointerEnter={() => setHovered(d.date)} onClick={() => { setHovered(null); onSelect(d.date); }}><title>{d.date + " · 累计绩效 " + display(d.score) + "；点击查看计算"}</title></rect>;
        })}
      </svg>
    </div>
    <div className="performance-trend-readout" aria-live="polite"><strong>{active.date}</strong>{SERIES.filter(s => visible.includes(s.key)).map(s => <span key={s.key}><i style={{ background: s.color }} />{s.label}<b>{display(value(active, s.key))}</b></span>)}{active.provisional && <small>部分数据待补齐</small>}</div>
    <footer><button type="button" onClick={() => move(-1)} disabled={selected === 0}>← 前一天</button><span>截至当日的累计值 · 缺失数据断线显示</span><button type="button" onClick={() => move(1)} disabled={selected === sorted.length - 1}>后一天 →</button></footer>
  </section>;
}
