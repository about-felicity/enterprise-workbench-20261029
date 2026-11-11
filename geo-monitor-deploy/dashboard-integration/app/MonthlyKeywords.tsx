"use client";

import { useEffect, useState } from "react";
import { beijingDate } from "./beijingCalendar";
import { dashboardBasePath } from "./dashboardPaths";

export type Stats = {
  valid: number; pending: number; mention: number; recommend: number; first: number;
  evidence: { day: string; question: string; text: string }[];
  last_received_at?: number | null;
};
type Version = { number: number; questions: string[]; stats: Stats; days?: Record<string, Stats> };
type Term = {
  id: string; name: string; active: boolean; versions: Version[];
  comparison: "same" | "changed" | "new"; previous_stats?: Stats;
};
type Board = {
  product: string; products: string[]; models: Record<string, string>;
  terms: Term[]; revision: number; can_edit: boolean; csrf: string;
  previous_only: string[]; previous_month: string;
};
type SavedTerm = Pick<Term, "id" | "name" | "active"> & {
  versions: Pick<Version, "number" | "questions">[];
};
export const emptyStats: Stats = { valid: 0, pending: 0, mention: 0, recommend: 0, first: 0, evidence: [] };
type PlannedQuestion = { question: string; remaining: number; unavailable: number };
type Lane = { id: string; daily: { date: string; progress_available: boolean; questions: PlannedQuestion[] } };
const modelLanes: Record<string, string[]> = {
  doubao: ["doubao1", "doubao2", "doubao3", "doubao4"], yuanbao: ["yuanbao"],
  baidu: ["baidu_ai"], wenxin: ["wenxin_card"], wenxin_all: ["baidu_ai", "wenxin_card"],
};
const receiptClock = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function shownStats(version: Version, day: string) {
  return day ? version.days?.[day] ?? emptyStats : version.stats;
}

export function monthLastDay(month: string) {
  const [year, number] = month.split("-").map(Number);
  return `${month}-${new Date(Date.UTC(year, number, 0)).getUTCDate()}`;
}

export function questionKey(question: string) {
  return question.normalize("NFKC").trim().replace(/\s+/g, " ");
}

export function useKeywordPlan(today: string, enabled: boolean, refresh: number) {
  const [plan, setPlan] = useState<Lane[]>([]);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    fetch(`${dashboardBasePath()}/api/geo-capture/panel?date=${today}`, { cache: "no-store", signal: controller.signal })
      .then(async response => response.ok ? await response.json() : null)
      .then(data => {
        if (!controller.signal.aborted) setPlan(Array.isArray(data?.models) ? data.models : []);
      })
      .catch(() => { if (!controller.signal.aborted) setPlan([]); });
    return () => controller.abort();
  }, [enabled, today, refresh]);
  return plan;
}

export function planByQuestion(lanes: Lane[], today: string, model: string) {
  const planned = new Map<string, PlannedQuestion>();
  for (const lane of lanes) {
    if (!(modelLanes[model] || []).includes(lane.id) || lane.daily?.date !== today || !lane.daily.progress_available) continue;
    for (const question of lane.daily.questions || []) {
      const key = questionKey(question.question);
      const previous = planned.get(key);
      planned.set(key, { ...question, remaining: question.remaining + (previous?.remaining ?? 0),
        unavailable: (question.unavailable ?? 0) + (previous?.unavailable ?? 0) });
    }
  }
  return planned;
}

function applySave(board: Board, saved: SavedTerm, revision: number): Board {
  const before = board.terms.find(term => term.id === saved.id);
  const sameVersion = before?.versions.length === saved.versions.length;
  const term: Term = {
    ...saved,
    versions: saved.versions.map(version => ({
      ...version,
      stats: before?.versions.find(old => old.number === version.number)?.stats ?? emptyStats,
      days: before?.versions.find(old => old.number === version.number)?.days,
    })),
    comparison: before && sameVersion ? before.comparison : "new",
    previous_stats: before && sameVersion ? before.previous_stats : undefined,
  };
  return { ...board, revision, terms: before
    ? board.terms.map(item => item.id === saved.id ? term : item)
    : [...board.terms, term] };
}

function ActionIcon({ kind }: { kind: "add" | "edit" | "refresh" }) {
  return <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor"
    strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {kind === "add" ? <path d="M8 3.5v9M3.5 8h9" />
      : kind === "edit" ? <path d="m10.5 3 2.5 2.5M3 13l.6-3.1 7-7a1.8 1.8 0 0 1 2.5 2.5l-7 7L3 13Z" />
        : <path d="M13 5a5.4 5.4 0 0 0-9-1M13 2.5V5h-2.5M3 11a5.4 5.4 0 0 0 9 1M3 13.5V11h2.5" />}
  </svg>;
}

function rate(hits: number, valid: number) {
  return valid ? `${(100 * hits / valid).toFixed(1)}%（${hits}/${valid}）` : "—";
}

function RateMetric({ hits, valid }: { hits: number; valid: number }) {
  if (!valid) return <span className="monthly-keyword-no-rate" aria-label="暂无有效样本">—</span>;
  return <div className="monthly-keyword-rate">
    <strong>{(100 * hits / valid).toFixed(1)}%</strong>
    <small>{hits} / {valid} 轮</small>
  </div>;
}

function comparison(term: Term, stats: Stats) {
  if (term.comparison === "new") return "上月无同名词";
  if (term.comparison === "changed") return "问句已换，暂不比较";
  const previous = term.previous_stats;
  if (!previous?.valid || !stats.valid) return "样本不足";
  const delta = 100 * (stats.recommend / stats.valid - previous.recommend / previous.valid);
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)} 个百分点`;
}

export function MonthlyKeywords({ apiBase, initialMonth, initialProduct, initialModel }: {
  apiBase: string; initialMonth?: string; initialProduct?: string; initialModel?: string;
}) {
  const endpoint = `${apiBase}/api/performance-entry/monthly-keywords`;
  const today = beijingDate();
  const currentMonth = today.slice(0, 7);
  const [month, setMonth] = useState(initialMonth ?? currentMonth);
  const [day, setDay] = useState("");
  const [product, setProduct] = useState(initialProduct ?? "");
  const [model, setModel] = useState(initialModel ?? "doubao");
  const [board, setBoard] = useState<Board | null>(null);
  const [refresh, setRefresh] = useState(0);
  const plan = useKeywordPlan(today, month === currentMonth, refresh);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<{ id?: string; name: string; questions: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ month, model, ...(product ? { product } : {}) });
    fetch(`${endpoint}?${query}`, { cache: "no-store", signal: controller.signal })
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "词表加载失败");
        if (!controller.signal.aborted) {
          setBoard(current => current && current.revision > data.revision ? current : data);
          setNotice(current => current === "已保存 · 统计将在后台刷新" ? "已保存" : current);
        }
      })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message); });
    return () => controller.abort();
  }, [endpoint, month, model, product, refresh]);

  function reset() {
    setBoard(null);
    setDraft(null);
    setError("");
    setNotice("");
  }

  async function write(action: "save" | "pause" | "resume", term?: Term) {
    if (!board?.can_edit || saving) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": board.csrf },
        body: JSON.stringify({
          action, month, product: board.product, revision: board.revision,
          id: term?.id ?? draft?.id,
          ...(action === "save" && draft ? {
            name: draft.name, questions: draft.questions.split("\n").map(q => q.trim()).filter(Boolean),
          } : {}),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 409) setRefresh(value => value + 1);
        throw new Error(data.error || "保存失败");
      }
      setDraft(null);
      if (data.term) setBoard(current => current ? applySave(current, data.term, data.revision) : current);
      setNotice("已保存 · 统计将在后台刷新");
      setRefresh(value => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const totals = board?.terms.reduce((total, term) => {
    const stats = shownStats(term.versions[term.versions.length - 1], day);
    return {
      active: total.active + Number(term.active),
      valid: total.valid + stats.valid,
      pending: total.pending + stats.pending,
    };
  }, { active: 0, valid: 0, pending: 0 });
  const planned = planByQuestion(month === currentMonth && (!day || day === today) ? plan : [], today, model);

  return <section className="panel monthly-keywords" aria-labelledby="monthly-keyword-title">
    <header className="monthly-keyword-header">
      <div>
        <h3 id="monthly-keyword-title">产品月度二级词</h3>
      </div>
      {board && (board.can_edit
        ? <button className="monthly-keyword-primary" type="button" disabled={saving || !!draft}
            onClick={() => setDraft({ name: "", questions: "" })}><ActionIcon kind="add" />新增二级词</button>
        : <span className="monthly-keyword-badge">只读 · 历史月份或账号无编辑权限</span>)}
    </header>
    <div className="monthly-keyword-controls">
      <label>月份 <input type="month" value={month} disabled={saving} onChange={event => {
        if (event.target.value) { reset(); setDay(""); setMonth(event.target.value); }
      }} /></label>
      <label>产品 <select value={board?.product || product} disabled={!board || saving} onChange={event => {
        reset(); setProduct(event.target.value);
      }}>{(board?.products || (product ? [product] : [])).map(name => <option key={name}>{name}</option>)}</select></label>
      <label>模型 <select value={model} disabled={!board || saving} onChange={event => {
        reset(); setModel(event.target.value);
      }}>{Object.entries(board?.models || { [model]: model }).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <label>采集日期 <input type="date" value={day} min={month + "-01"}
        max={month === currentMonth ? today : monthLastDay(month)} disabled={!board || saving}
        onChange={event => {
          if (!event.target.value || (event.target.validity.valid && event.target.value.startsWith(month + "-"))) {
            setDay(event.target.value);
          }
        }} /></label>
      {day && <button type="button" onClick={() => setDay("")}>看整月</button>}
      <button type="button" disabled={saving} onClick={() => { setError(""); setRefresh(value => value + 1); }}><ActionIcon kind="refresh" />刷新</button>
      <a className="keyword-capture-link" href="#capture">采集进度 →</a>
    </div>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!board && !error && <p role="status">加载词表中…</p>}
    {!!board?.terms.length && totals && <>
      <dl className="monthly-keyword-overview" aria-label="当前产品和平台的样本汇总">
        <div><dt>已启用二级词</dt><dd>{totals.active}<small> / {board.terms.length} 个</small></dd></div>
        <div><dt>{day ? "当日有效样本" : "本月有效样本"}</dt><dd>{totals.valid}<small> 轮</small></dd></div>
        <div><dt>已回传待分析</dt><dd>{totals.pending}<small> 轮</small></dd></div>
      </dl>
    </>}
    {draft && board?.can_edit && <form className="monthly-keyword-form" onSubmit={event => {
      event.preventDefault(); void write("save");
    }}>
      <h4>{draft.id ? "编辑二级词" : "新增二级词"}</h4>
      <label>二级词名称 <input required maxLength={40} value={draft.name}
        onChange={event => setDraft({ ...draft, name: event.target.value })} /></label>
      <label>实际问句（每行一条） <textarea required rows={4} maxLength={9030} value={draft.questions}
        onChange={event => setDraft({ ...draft, questions: event.target.value })} /></label>
      <p>改名保留原统计。换问句建立新版本，已有轮次留在旧版本。</p>
      <div><button className="monthly-keyword-primary" disabled={saving}>保存</button>{" "}<button type="button" disabled={saving}
        onClick={() => setDraft(null)}>取消</button></div>
    </form>}
    {board?.terms.length === 0 && !draft && <div className="monthly-keyword-empty">
      <strong>本月还没有二级词</strong>
      {board.can_edit && <button className="monthly-keyword-primary" type="button"
        onClick={() => setDraft({ name: "", questions: "" })}><ActionIcon kind="add" />添加第一个二级词</button>}
    </div>}
    {!!board?.terms.length && <div className="monthly-keyword-table"><table aria-label="二级词监控结果">
      <thead><tr><th scope="col">二级词与问句</th><th scope="col">样本与日期</th><th scope="col">正文提及率</th><th scope="col">明确推荐率</th><th scope="col">首推率</th><th scope="col">推荐率月度环比</th></tr></thead>
      <tbody>{board.terms.map(term => {
        const version = term.versions[term.versions.length - 1];
        const stats = shownStats(version, day);
        const slots = term.active ? version.questions.map(q => planned.get(questionKey(q))) : [];
        const remaining = slots.reduce((sum, slot) => sum + (slot?.remaining ?? 0), 0);
        const unavailable = slots.reduce((sum, slot) => sum + (slot?.unavailable ?? 0), 0);
        const receipt = stats.last_received_at ? new Date(stats.last_received_at * 1000) : null;
        const emptyLabel = remaining ? "今日待采" : unavailable ? "今日未取得" : day ? "当天暂无回传" : "暂无回传";
        return <tr key={term.id}>
          <th scope="row">
            <div className="monthly-keyword-term">
              <strong>{term.name}</strong>
              <span className="monthly-keyword-version">v{version.number}</span>
              <span className="monthly-keyword-state" data-active={term.active}>{term.active ? "已启用" : "已停用"}</span>
            </div>
            <ul className="monthly-keyword-questions">{version.questions.map(q => <li key={q}>{q}</li>)}</ul>
            {term.versions.length > 1 && <details><summary>旧版本记录</summary>
              {term.versions.slice(0, -1).map(old => <div key={old.number}>
                v{old.number} · {old.questions.join(" / ")} · 推荐率 {rate(old.stats.recommend, old.stats.valid)}
              </div>)}
            </details>}
            {board.can_edit && <div className="monthly-keyword-row-actions">
              <button type="button" disabled={saving || !!draft} onClick={() => setDraft({
                id: term.id, name: term.name, questions: version.questions.join("\n"),
              })}><ActionIcon kind="edit" />编辑二级词</button>
              <button className="monthly-keyword-quiet" type="button" disabled={saving || !!draft}
                onClick={() => void write(term.active ? "pause" : "resume", term)}>{term.active ? "停用" : "重新启用"}</button>
            </div>}
          </th>
          <td data-label="样本与日期">
            {stats.valid ? <strong className="monthly-keyword-sample">{stats.valid} 轮有效</strong>
              : <span className="monthly-keyword-sample" data-empty="true">{stats.pending ? "已回传" : emptyLabel}</span>}
            {stats.pending > 0 && <small>{stats.pending} 轮待分析</small>}
            {stats.valid > 0 && stats.valid < 10 && <small>样本较少</small>}
            {receipt && <small className="monthly-keyword-receipt">最近回传 <time dateTime={receipt.toISOString()}>{beijingDate(receipt)} {receiptClock.format(receipt)}</time></small>}
            {remaining > 0 && <small>今日还剩 {remaining} 轮</small>}
            {unavailable > 0 && <small>今日未取得 {unavailable} 轮</small>}
          </td>
          <td data-label="正文提及率"><RateMetric hits={stats.mention} valid={stats.valid} /></td>
          <td data-label="明确推荐率"><RateMetric hits={stats.recommend} valid={stats.valid} />
            {!!stats.evidence.length && <details><summary>查看命中证据</summary>
              {stats.evidence.map((item, index) => <blockquote key={index}>{item.day} · {item.question}<br />{item.text}</blockquote>)}
            </details>}
          </td>
          <td data-label="首推率"><RateMetric hits={stats.first} valid={stats.valid} /></td>
          <td data-label="推荐率月度环比"><span className="monthly-keyword-comparison">{comparison(term, version.stats)}</span></td>
        </tr>;
      })}</tbody>
    </table></div>}
    {!!board?.previous_only.length && <p>
      本月未配置的上月词：{board.previous_only.join("、")}{" "}
      <button type="button" disabled={saving} onClick={() => {
        setProduct(board.product); setMonth(board.previous_month); setDay(""); reset();
      }}>查看上月</button>
    </p>}
  </section>;
}
