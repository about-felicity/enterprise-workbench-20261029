"use client";
import { useState } from "react";

type Product = { product: string; traffic_today: number | null; daily_target: number };
type Day = { date: string; products: Product[] };
type Person = { name: string; daily: Day[] };
const count = (value: number) => value.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
const rate = (actual: number, target: number) => target > 0 ? `${(actual / target * 100).toFixed(1)}%` : "—";

export function DailyTrafficCard({ people, month, asOf }: { people: Person[]; month: string; asOf: string }) {
  const [owner, setOwner] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const scoped = owner && people.some(person => person.name === owner) ? people.filter(person => person.name === owner) : people;
  const dates = Array.from(new Set(people.flatMap(person => person.daily.map(day => day.date)))).sort().reverse();
  const rows = dates.map(date => {
    const products = scoped.flatMap(person => (person.daily.find(day => day.date === date)?.products || []).map(product => ({ ...product, owner: person.name })));
    const filled = products.filter(product => product.traffic_today != null);
    return { date, products, filled: filled.length, total: products.length,
      actual: filled.reduce((sum, product) => sum + product.traffic_today!, 0),
      target: products.reduce((sum, product) => sum + product.daily_target, 0) };
  });
  const current = rows.find(row => row.date === selectedDate) || rows.find(row => row.filled > 0) || rows[0];
  const complete = Boolean(current && current.total > 0 && current.filled === current.total);
  return <section className="daily-traffic-card" aria-label="每日流量明细">
    <header className="daily-traffic-header"><div><h3>每日流量明细</h3><p>查看当天搜索数、目标和产品明细</p></div>
      <div className="daily-traffic-controls"><label>员工<select aria-label="流量员工" value={owner} onChange={event => setOwner(event.target.value)}><option value="">全部员工</option>{people.map(person => <option key={person.name} value={person.name}>{person.name}</option>)}</select></label>
        <label>日期<input aria-label="流量明细日期" type="date" min={`${month}-01`} max={asOf} value={current?.date || ""} onChange={event => setSelectedDate(event.target.value)} /></label></div>
    </header>
    {current ? <>
      <div className="daily-traffic-summary">
        <div><span>{current.date} 已录流量</span><strong data-testid="daily-traffic-actual">{current.filled ? count(current.actual) : "—"}</strong></div>
        <div><span>当日目标</span><strong>{count(current.target)}</strong></div>
        <div><span>当日达成率</span><strong>{complete ? rate(current.actual, current.target) : "待补齐"}</strong></div>
        <div><span>数据覆盖</span><strong>{current.filled}<small> / {current.total} 个产品</small></strong></div>
      </div>
      {!complete && <p className="daily-traffic-notice">{current.filled ? `当前合计包含已录入的 ${current.filled} 个产品，另有 ${current.total - current.filled} 个待录入。` : "当天尚未录入流量。"}</p>}
      <div className="daily-traffic-history"><table><caption>每日流量汇总 · 点击日期查看产品</caption><thead><tr><th>日期</th><th>已录搜索数</th><th>日目标</th><th>达成率</th><th>录入情况</th></tr></thead><tbody>
        {rows.map(row => <tr key={row.date} className={row.date === current.date ? "selected" : ""}><td><button type="button" aria-label={`查看${row.date}流量`} aria-pressed={row.date === current.date} onClick={() => setSelectedDate(row.date)}>{row.date}</button></td><td>{row.filled ? count(row.actual) : "—"}</td><td>{count(row.target)}</td><td>{row.total > 0 && row.filled === row.total ? rate(row.actual, row.target) : "待补齐"}</td><td>{row.filled} / {row.total} 个产品</td></tr>)}
      </tbody></table></div>
      <details className="daily-traffic-products" open><summary>{current.date} 产品流量明细</summary><div className="daily-traffic-table"><table><thead><tr><th>员工</th><th>产品</th><th>当天搜索数</th><th>日目标</th><th>达成率</th></tr></thead><tbody>
        {current.products.map(product => <tr key={`${product.owner}-${product.product}`}><td>{product.owner}</td><td>{product.product}</td><td>{product.traffic_today == null ? <span className="daily-traffic-missing">待录入</span> : count(product.traffic_today)}</td><td>{count(product.daily_target)}</td><td>{product.traffic_today == null ? "—" : rate(product.traffic_today, product.daily_target)}</td></tr>)}
      </tbody></table></div></details>
    </> : <p className="daily-traffic-notice">本月暂无流量明细。</p>}
  </section>;
}
