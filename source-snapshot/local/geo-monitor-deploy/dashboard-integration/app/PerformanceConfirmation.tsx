"use client";
import { useCallback, useEffect, useState } from "react";
type Snapshot = { name: string; month: string; current: { score: number; coefficient: number; provisional: boolean; date: string; contributions: Record<string, number | null> } };
type Person = { name: string; password_set: boolean; confirmed_at: string | null; snapshot: Snapshot | null };
type Status = { csrf: string; can_confirm: boolean; can_reset: boolean; window: { state: string; message: string }; people: Person[] };
const labels: Record<string, string> = { traffic: "流量", budget: "预算", mention: "提及达成率", values: "价值观" };
export function PerformanceConfirmation({ apiBase, month, selected, onStatus }: { apiBase: string; month: string; selected: string | null; onStatus: (value: Record<string, string>) => void }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState(""); const [repeat, setRepeat] = useState(""); const [old, setOld] = useState("");
  const [change, setChange] = useState(false); const [reset, setReset] = useState(false);
  const [preview, setPreview] = useState<{ token: string; snapshot: Snapshot } | null>(null);
  const endpoint = `${apiBase}/api/performance-entry/confirmation`;
  const load = useCallback(async (signal?: AbortSignal) => {
    const r = await fetch(`${endpoint}?month=${encodeURIComponent(month)}`, { cache: "no-store", signal });
    const v = await r.json(); if (!r.ok) throw Error(v.error || "确认状态读取失败");
    setStatus(v); onStatus(Object.fromEntries(v.people.map((p: Person) => [p.name, p.confirmed_at ? "已确认" : v.window.state === "closed" ? "已逾期" : "未确认"])));
  }, [endpoint, month, onStatus]);
  useEffect(() => {
    const controller = new AbortController(); setStatus(null); setError(""); onStatus({});
    const refresh = () => { void load(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.message || "确认状态读取失败"); }); };
    refresh(); const timer = window.setInterval(refresh, 30000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [load, onStatus]);
  useEffect(() => { setPassword(""); setRepeat(""); setOld(""); setPreview(null); setChange(false); setReset(false); setError(""); setMessage(""); }, [selected, month]);
  const person = status?.people.find(p => p.name === selected);
  const operate = async (action: string) => {
    if (!person || !status || busy) return;
    if ((action === "setup" || action === "change") && password !== repeat) { setError("两次输入的新密码不一致"); return; }
    setBusy(true); setError(""); setMessage("");
    const controller = new AbortController(); const timer = window.setTimeout(() => controller.abort(), 60000);
    try {
      const r = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": status.csrf },
        body: JSON.stringify({ action, name: person.name, month, password, old_password: old, token: preview?.token }), signal: controller.signal });
      const v = await r.json(); if (!r.ok) throw Error(v.error || "操作失败");
      if (action === "preview") setPreview(v);
      else { setPassword(""); setRepeat(""); setOld(""); setPreview(null); setChange(false); setReset(false); setMessage(action === "confirm" ? "本月绩效已确认" : action === "reset" ? "密码已重置，请员工重新设置" : "密码已保存"); }
      await load();
    } catch (e) { setError(e instanceof Error && e.name !== "AbortError" ? e.message : "请求超时，请刷新核对状态后再试"); }
    finally { window.clearTimeout(timer); setBusy(false); }
  };
  const summary = (s: Snapshot) => <div className="performance-confirm-summary"><strong>{s.month} · {s.name} · {s.current.score.toFixed(1)}%</strong><span>绩效系数 {s.current.coefficient}</span><p>{Object.entries(s.current.contributions).map(([k, v]) => `${labels[k] || k} ${v == null ? "待补" : v.toFixed(1)}分`).join(" ＋ ")}</p>{s.current.provisional && <p>部分数据尚未齐全，确认将保存当前展示的参考绩效。</p>}</div>;
  return <section className="performance-confirm" aria-label="员工绩效确认">
    <header><strong>员工绩效确认</strong><span>{status?.window.message || "正在读取确认状态…"}</span></header>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {!selected && <p>点开自己的员工卡片，设置个人确认密码或确认本月绩效。</p>}
    {person && <div><h3>{person.name}</h3>
      {person.confirmed_at && person.snapshot && <>{summary(person.snapshot)}<p>已确认 · {new Date(person.confirmed_at).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false })}（北京时间）</p></>}
      {status?.can_confirm && <>
        {(!person.password_set || change) ? <form onSubmit={e => { e.preventDefault(); void operate(person.password_set ? "change" : "setup"); }}>
          <p>{person.password_set ? "修改个人确认密码" : `首次为${person.name}设置个人绩效确认密码。请确认这是你本人的卡片。`}</p>
          {change && <label>原密码<input type="password" autoComplete="current-password" value={old} onChange={e => setOld(e.target.value)} required minLength={6} maxLength={128} disabled={busy} /></label>}
          <label>新密码<input type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} maxLength={128} disabled={busy} /></label>
          <label>再次输入<input type="password" autoComplete="new-password" value={repeat} onChange={e => setRepeat(e.target.value)} required minLength={6} maxLength={128} disabled={busy} /></label>
          <button disabled={busy}>{busy ? "保存中…" : "保存个人密码"}</button>{change && <button type="button" disabled={busy} onClick={() => setChange(false)}>取消</button>}
        </form> : <>
          {!person.confirmed_at && status.window.state === "open" && !preview && <button disabled={busy} onClick={() => void operate("preview")}>{busy ? "正在读取待确认绩效…" : "核对并确认本月绩效"}</button>}
          {!person.confirmed_at && preview && <form onSubmit={e => { e.preventDefault(); void operate("confirm"); }}>{summary(preview.snapshot)}<label>个人确认密码<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} maxLength={128} disabled={busy} /></label><button disabled={busy || status.window.state !== "open"}>{busy ? "确认中…" : "确认以上绩效"}</button><button type="button" disabled={busy} onClick={() => { setPreview(null); setPassword(""); }}>取消</button></form>}
          <button className="performance-confirm-secondary" disabled={busy} onClick={() => { setChange(true); setPreview(null); setPassword(""); }}>修改个人密码</button>
        </>}
      </>}
      {status?.can_reset && person.password_set && <div>{reset ? <><span>重置{person.name}的密码？历史确认记录会保留。</span><button disabled={busy} onClick={() => void operate("reset")}>确认重置</button><button disabled={busy} onClick={() => setReset(false)}>取消</button></> : <button onClick={() => setReset(true)}>重置该员工确认密码</button>}</div>}
      {!status?.can_confirm && !status?.can_reset && <p>请使用geo_admin登录后设置个人密码及确认绩效。</p>}
    </div>}
  </section>;
}
