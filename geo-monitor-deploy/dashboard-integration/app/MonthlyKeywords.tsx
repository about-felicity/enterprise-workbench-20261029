"use client";

import { useEffect, useState } from "react";

type Stats = {
  valid: number; pending: number; mention: number; recommend: number; first: number;
  evidence: { day: string; question: string; text: string }[];
};
type Version = { number: number; questions: string[]; stats: Stats };
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
const emptyStats: Stats = { valid: 0, pending: 0, mention: 0, recommend: 0, first: 0, evidence: [] };

function applySave(board: Board, saved: SavedTerm, revision: number): Board {
  const before = board.terms.find(term => term.id === saved.id);
  const sameVersion = before?.versions.length === saved.versions.length;
  const term: Term = {
    ...saved,
    versions: saved.versions.map(version => ({
      ...version, stats: before?.versions.find(old => old.number === version.number)?.stats ?? emptyStats,
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

function comparison(term: Term, stats: Stats) {
  if (term.comparison === "new") return "上月无同名词";
  if (term.comparison === "changed") return "问句已换，暂不比较";
  const previous = term.previous_stats;
  if (!previous?.valid || !stats.valid) return "样本不足";
  const delta = 100 * (stats.recommend / stats.valid - previous.recommend / previous.valid);
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)} 个百分点`;
}

export function MonthlyKeywords({ apiBase }: { apiBase: string }) {
  const endpoint = `${apiBase}/api/performance-entry/monthly-keywords`;
  const [month, setMonth] = useState(() => {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit",
    }).formatToParts(new Date());
    return `${parts.find(part => part.type === "year")?.value}-${parts.find(part => part.type === "month")?.value}`;
  });
  const [product, setProduct] = useState("");
  const [model, setModel] = useState("deepseek");
  const [board, setBoard] = useState<Board | null>(null);
  const [refresh, setRefresh] = useState(0);
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

  return <section className="panel monthly-keywords">
    <header className="monthly-keyword-header">
      <div>
        <span className="monthly-keyword-eyebrow">GEO 监控 · 月度词表</span>
        <h3>产品月度二级词</h3>
        <p>管理每月监控问句，查看提及、推荐与首推表现。</p>
      </div>
      {board && (board.can_edit
        ? <button className="monthly-keyword-primary" type="button" disabled={saving || !!draft}
            onClick={() => setDraft({ name: "", questions: "" })}><ActionIcon kind="add" />新增二级词</button>
        : <span className="monthly-keyword-badge">只读 · 历史月份或账号无编辑权限</span>)}
    </header>
    <div className="monthly-keyword-controls">
      <label>月份 <input type="month" value={month} disabled={saving} onChange={event => {
        if (event.target.value) { reset(); setMonth(event.target.value); }
      }} /></label>
      <label>产品 <select value={board?.product || product} disabled={!board || saving} onChange={event => {
        reset(); setProduct(event.target.value);
      }}>{(board?.products || (product ? [product] : [])).map(name => <option key={name}>{name}</option>)}</select></label>
      <label>模型 <select value={model} disabled={!board || saving} onChange={event => {
        reset(); setModel(event.target.value);
      }}>{Object.entries(board?.models || { [model]: model }).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <button type="button" disabled={saving} onClick={() => { setError(""); setRefresh(value => value + 1); }}><ActionIcon kind="refresh" />刷新</button>
    </div>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!board && !error && <p role="status">加载词表中…</p>}
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
      <p>{board.can_edit ? "先添加一个二级词和实际问句，后续可在词表里逐条编辑。" : "切换月份或产品，可查看其他已配置的词表。"}</p>
      {board.can_edit && <button className="monthly-keyword-primary" type="button"
        onClick={() => setDraft({ name: "", questions: "" })}><ActionIcon kind="add" />添加第一个二级词</button>}
    </div>}
    {!!board?.terms.length && <div className="trend-table"><table>
      <thead><tr><th>二级词与问句</th><th>有效样本</th><th>正文提及率</th><th>明确推荐率</th><th>首推率</th><th>推荐率环比</th></tr></thead>
      <tbody>{board.terms.map(term => {
        const version = term.versions[term.versions.length - 1];
        const stats = version.stats;
        return <tr key={term.id}>
          <td><strong>{term.name}</strong> · v{version.number}{!term.active && " · 已停用"}
            <details><summary>查看问句</summary>{version.questions.map(q => <div key={q}>{q}</div>)}</details>
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
          </td>
          <td>{stats.valid} 轮 · {stats.pending} 待分析{stats.valid > 0 && stats.valid < 10 && " · 样本较少"}</td>
          <td>{rate(stats.mention, stats.valid)}</td>
          <td><strong>{rate(stats.recommend, stats.valid)}</strong>
            {!!stats.evidence.length && <details><summary>查看命中证据</summary>
              {stats.evidence.map((item, index) => <blockquote key={index}>{item.day} · {item.question}<br />{item.text}</blockquote>)}
            </details>}
          </td>
          <td>{rate(stats.first, stats.valid)}</td>
          <td>{comparison(term, stats)}</td>
        </tr>;
      })}</tbody>
    </table></div>}
    {!!board?.previous_only.length && <p>
      本月未配置的上月词：{board.previous_only.join("、")}{" "}
      <button type="button" disabled={saving} onClick={() => {
        setProduct(board.product); setMonth(board.previous_month); reset();
      }}>查看上月</button>
    </p>}
  </section>;
}
