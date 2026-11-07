"use client";
import { useCallback, useEffect, useState } from "react";
import { beijingDate } from "./beijingCalendar";

type Field = "traffic" | "expenses" | "traffic_target" | "budget_limit";
type Row = { product: string; owner: string; priority: string; fields: Record<Field, { value: number | null; revision: number; updated_by: string | null; updated_at: string | null }> };
type EntryData = { rows: Row[]; targets_confirmed: boolean; history: Array<{ product: string; day: string; field: Field; old_value: number | null; new_value: number | null; actor: string; at: string }> };
type Values = Record<string, Record<Field, string>>;
const labels: Record<Field, string> = { traffic: "每日流量", expenses: "累计实际花费", traffic_target: "每日流量目标", budget_limit: "整月预算" };
const today = () => beijingDate();
const initialDate = (month: string) => month === today().slice(0, 7) ? today() : `${month}-${new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0).getDate()}`;
const initialValues = (data: EntryData): Values => Object.fromEntries(data.rows.map(row => [row.product, Object.fromEntries(Object.entries(row.fields).map(([field, cell]) => [field, cell.value == null ? "" : String(cell.value)])) as Record<Field, string>]));

export function PerformanceEntry({ apiBase, month, csrf, onSaved, onClose }: { apiBase: string; month: string; csrf: string; onSaved: () => void; onClose: () => void }) {
  const [date, setDate] = useState(() => initialDate(month));
  const [mode, setMode] = useState<"traffic" | "expenses" | "targets">("traffic");
  const [data, setData] = useState<EntryData | null>(null);
  const [values, setValues] = useState<Values>({});
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const selectedDate = date.startsWith(month) ? date : initialDate(month);
  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true); setError("");
    try {
      const response = await fetch(`${apiBase}/api/performance-entry/data?${new URLSearchParams({ month, date: selectedDate })}`, { cache: "no-store", signal });
      if (!response.headers.get("Content-Type")?.includes("application/json")) throw Error("登录已失效，请重新登录superadmin");
      const value = await response.json(); if (!response.ok) throw Error(value.error || "无法读取录入数据");
      if (signal?.aborted) return;
      setData(value); setValues(initialValues(value)); setDirty(false);
    } catch (e) { if (!signal?.aborted) setError(e instanceof Error ? e.message : "读取失败"); }
    finally { if (!signal?.aborted) setLoading(false); }
  }, [apiBase, month, selectedDate]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const confirmLeave = () => !dirty || window.confirm("有未保存的数据，确定放弃这些修改吗？");
  const fields: Field[] = mode === "targets" ? ["traffic_target", "budget_limit"] : [mode];
  const change = (product: string, field: Field, value: string) => { setValues(old => ({ ...old, [product]: { ...old[product], [field]: value } })); setDirty(true); setMessage(""); };
  const save = async () => {
    if (!data) return; setError(""); setMessage("");
    const changes = [];
    for (const row of data.rows) for (const field of fields) {
      const text = values[row.product]?.[field]?.trim() || "";
      const value = text === "" ? null : Number(text);
      if (value !== null && (!Number.isFinite(value) || value < 0 || (field === "traffic" || field === "traffic_target") && !Number.isInteger(value))) { setError(`${row.product}：请输入非负数字，流量须为整数`); return; }
      if (mode === "targets" && value === null) { setError(`${row.product}：月度目标不能为空`); return; }
      if (value === row.fields[field].value && row.fields[field].revision > 0 || value === null && row.fields[field].revision === 0) continue;
      changes.push({ product: row.product, field, date: mode === "targets" ? `${month}-01` : selectedDate, value, expected_revision: row.fields[field].revision });
    }
    if (!changes.length) { setMessage("没有需要保存的修改"); return; }
    setBusy(true);
    try {
      const operation_id = Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, "0")).join("");
      const response = await fetch(`${apiBase}/api/performance-entry/save`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf }, body: JSON.stringify({ month, operation_id, changes }) });
      if (!response.headers.get("Content-Type")?.includes("application/json")) throw Error("登录已失效，请保留填写内容并重新登录");
      const result = await response.json(); if (!response.ok) throw Error(result.error || "保存失败");
      setDirty(false); setMessage(`已保存 ${result.updated_cells} 项，绩效已更新`); await load(); onSaved();
    } catch (e) { setError(e instanceof Error ? e.message : "保存失败，已保留填写内容"); }
    finally { setBusy(false); }
  };
  return <section className="performance-entry" aria-label="superadmin绩效数据录入">
    <header><div><h3>绩效数据录入</h3><span>superadmin</span></div><button type="button" disabled={busy} onClick={() => { if (confirmLeave()) onClose(); }}>收起录入</button></header>
    <div className="performance-entry-toolbar"><div role="group" aria-label="录入类型">{[["traffic", "每日流量"], ["expenses", "累计费用"], ["targets", "月度目标"]].map(([id, title]) => <button key={id} className={mode === id ? "active" : ""} disabled={busy} onClick={() => { if (confirmLeave()) { setMode(id as typeof mode); if (data) setValues(initialValues(data)); setDirty(false); setMessage(""); setError(""); } }}>{title}</button>)}</div>
      <label>{mode === "targets" ? "考核月份" : "数据日期"}{mode === "targets" ? <b>{month}</b> : <input aria-label="录入数据日期" type="date" min={`${month}-01`} max={initialDate(month)} value={selectedDate} disabled={busy} onChange={e => { if (confirmLeave()) { setDate(e.target.value); setMessage(""); } }} />}</label>
    </div>
    <p className="performance-entry-hint">{mode === "traffic" ? "填写各产品当天淘宝搜索数，多链接合计。可从表格粘贴一列；留空表示未填写，0表示实际为零。" : mode === "expenses" ? "填写截至所选日期的累计实际花费（元），不是单日花费。" : "填写当月各产品的每日流量目标和整月预算。"} 提及率由GEO自动获取。</p>
    {data && !data.targets_confirmed && <p className="performance-entry-warning">本月目标暂沿用已导入方案，请在“月度目标”中确认保存。</p>}
    {error && <p className="performance-entry-error" role="alert">{error}</p>}{message && <p className="performance-entry-success" role="status">{message}</p>}
    {loading ? <p role="status">正在读取录入数据…</p> : data && <>
      <div className="assessment-table-wrap"><table><thead><tr><th>考核产品</th><th>负责人</th>{fields.map(field => <th key={field}>{labels[field]}{field.includes("budget") || field === "expenses" ? "（元）" : ""}</th>)}<th>最近修改</th></tr></thead>
        <tbody>{data.rows.map((row, index) => <tr key={row.product}><td>{row.product}</td><td>{row.owner}</td>{fields.map(field => <td key={field}><input aria-label={`${row.product}${labels[field]}`} type="number" inputMode={field === "traffic" || field === "traffic_target" ? "numeric" : "decimal"} min="0" step={field === "traffic" || field === "traffic_target" ? "1" : "0.01"} disabled={busy} value={values[row.product]?.[field] || ""} placeholder={mode === "targets" ? "必填" : "未填写"} onChange={e => change(row.product, field, e.target.value)} onPaste={e => {
          const lines = e.clipboardData.getData("text").trimEnd().split(/\r?\n/); if (lines.length < 2) return;
          e.preventDefault(); if (index + lines.length > data.rows.length) { setError("粘贴数据超出产品行数，请核对后再粘贴"); return; }
          if (lines.some(line => line.includes("\t") || line.trim() && (!Number.isFinite(Number(line)) || Number(line) < 0))) { setError("请只粘贴当前数值列，不要包含产品名或其他列"); return; }
          setValues(old => { const next = { ...old }; lines.forEach((text, n) => { const product = data.rows[index + n].product; next[product] = { ...next[product], [field]: text.trim() }; }); return next; }); setDirty(true); setMessage("");
        }} /></td>)}<td><small>{row.fields[fields[0]].updated_by === "historical_import" ? "历史导入" : row.fields[fields[0]].updated_by || "—"}<br />{row.fields[fields[0]].updated_at?.slice(0, 19).replace("T", " ") || ""}</small></td></tr>)}</tbody></table></div>
      <div className="performance-entry-totals">{Array.from(new Set(data.rows.map(row => row.owner).filter(Boolean))).map(name => { const owned = data.rows.filter(row => row.owner === name); const field = fields[0]; const filled = owned.filter(row => values[row.product]?.[field] !== ""); const total = filled.reduce((sum, row) => sum + (Number(values[row.product]?.[field]) || 0), 0); return <span key={name}><b>{name}</b> {total.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}<small>{filled.length}/{owned.length} 项已填</small></span>; })}</div>
      <footer><span>{dirty ? "有未保存的数据" : "当前数据已载入"}</span><button onClick={() => { if (confirmLeave()) void load(); }} disabled={busy}>重新载入</button><button className="primary" onClick={() => void save()} disabled={busy}>{busy ? "保存中…" : "保存并更新绩效"}</button></footer>
      <details className="performance-entry-history"><summary>最近修改记录</summary><div className="assessment-table-wrap"><table><thead><tr><th>时间</th><th>数据日期</th><th>产品</th><th>项目</th><th>修改前 → 修改后</th><th>修改人</th></tr></thead><tbody>{data.history.map((item, i) => <tr key={i}><td>{item.at.slice(0, 19).replace("T", " ")}</td><td>{item.day}</td><td>{item.product}</td><td>{labels[item.field]}</td><td>{item.old_value ?? "未填"} → {item.new_value ?? "未填"}</td><td>{item.actor}</td></tr>)}</tbody></table></div></details>
    </>}
  </section>;
}
