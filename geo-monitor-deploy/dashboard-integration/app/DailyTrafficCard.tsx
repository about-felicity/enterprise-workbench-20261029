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
  const monthLength = new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0).getDate();
  const monthDates = Array.from({ length: monthLength }, (_, index) => `${month}-${String(index + 1).padStart(2, "0")}`);
  const monthlyProducts = scoped.flatMap(person => {
    const products = person.daily[0]?.products || [];
    return products.map(product => {
      const values = Object.fromEntries(person.daily.map(day => [day.date, day.products.find(item => item.product === product.product)?.traffic_today ?? null]));
      const entered = Object.entries(values).filter(([date, value]) => date <= asOf && value != null);
      return { ...product, owner: person.name, values, entered: entered.length, total: entered.reduce((sum, [, value]) => sum + value!, 0) };
    });
  });
  return <section className="daily-traffic-card" aria-label="每日流量明细">
    <header className="daily-traffic-header"><div><h3>本月每日流量</h3><p>{month} · 每个产品逐日查看，左右滑动查看整月日期</p></div>
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
      <div className="monthly-traffic-grid"><table aria-label="整月每日产品流量"><caption>已录合计按已有数据求和；待录入表示数据缺失，截止日后的日期显示 —。</caption><thead><tr><th className="traffic-owner">员工</th><th className="traffic-product">产品</th><th>日目标</th><th>本月已录合计</th>{monthDates.map(date => <th key={date} className={date === current.date ? "traffic-selected" : ""}><button type="button" disabled={date > asOf} aria-label={`查看${date}流量`} onClick={() => setSelectedDate(date)}>{Number(date.slice(-2))}日</button></th>)}</tr></thead><tbody>
        {monthlyProducts.map(product => <tr key={`${product.owner}-${product.product}`}><td className="traffic-owner">{product.owner}</td><th scope="row" className="traffic-product">{product.product}</th><td>{count(product.daily_target)}</td><td><strong>{product.entered ? count(product.total) : "—"}</strong></td>{monthDates.map(date => <td key={date} data-date={date} className={date === current.date ? "traffic-selected" : ""} title={date > asOf ? "截止日后" : undefined}>{date > asOf ? "—" : product.values[date] == null ? <span className="daily-traffic-missing">待录入</span> : count(product.values[date]!)}</td>)}</tr>)}
      </tbody><tfoot><tr><th className="traffic-owner" scope="row">合计</th><td className="traffic-product">{monthlyProducts.length} 个产品</td><td>{count(current.target)}</td><td>{monthlyProducts.some(product => product.entered > 0) ? count(monthlyProducts.reduce((sum, product) => sum + product.total, 0)) : "—"}</td>{monthDates.map(date => { const row = rows.find(item => item.date === date); return <td key={date} title={row && row.filled < row.total ? `已录 ${row.filled}/${row.total} 个产品` : undefined}>{date > asOf ? "—" : row?.filled ? `${count(row.actual)}${row.filled < row.total ? "*" : ""}` : "待录入"}</td>; })}</tr></tfoot></table></div>
      <p className="daily-traffic-grid-note">* 表示当天仅录入部分产品。点击日期表头可查看上方当日汇总。</p>
      <details className="daily-traffic-products"><summary>{current.date} 单日产品明细</summary><div className="daily-traffic-table"><table><thead><tr><th>员工</th><th>产品</th><th>当天搜索数</th><th>日目标</th><th>达成率</th></tr></thead><tbody>
        {current.products.map(product => <tr key={`${product.owner}-${product.product}`}><td>{product.owner}</td><td>{product.product}</td><td>{product.traffic_today == null ? <span className="daily-traffic-missing">待录入</span> : count(product.traffic_today)}</td><td>{count(product.daily_target)}</td><td>{product.traffic_today == null ? "—" : rate(product.traffic_today, product.daily_target)}</td></tr>)}
      </tbody></table></div></details>
    </> : <p className="daily-traffic-notice">本月暂无流量明细。</p>}
  </section>;
}
