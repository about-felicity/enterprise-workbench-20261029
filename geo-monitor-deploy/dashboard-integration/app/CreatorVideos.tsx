"use client";

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import type { VideoLedger } from "./api/videoProxy";
import { dashboardBasePath } from "./dashboardPaths";

type Snapshot = {
  day: string;
  captured_at: string;
  likes: number | null;
  comments: number | null;
  favorites: number | null;
  shares: number | null;
  metric_labels?: Partial<Record<keyof typeof metricLabels, string>>;
};

type SourceRecord = {
  workbook: string;
  sheet: string;
  sheet_row: number;
  day: string;
  source_data: Record<string, string | null>;
};

const availabilityLabels = {
  unchecked: "待核查",
  available: "可访问",
  unavailable: "确认不可用",
  unknown: "暂时无法确认",
} as const;

type Availability = keyof typeof availabilityLabels;

type DailyRate = {
  day: string | null;
  total: number;
  available: number;
  unavailable: number;
  unresolved: number;
  unlinked: number;
};
type RateMode = "entry" | "check";

type Work = {
  id: number;
  record_key: string;
  input_url: string;
  platform?: Platform;
  url: string | null;
  title: string | null;
  author: string | null;
  pending: number;
  checking: boolean;
  last_error: string | null;
  last_attempt: string | null;
  last_check_status?: Exclude<Availability, "unchecked"> | null;
  last_confirmed_at?: string | null;
  entry_day: string | null;
  published_at?: string | null;
  creator_id: string | null;
  creator_uid: string | null;
  fee_cents?: number | null;
  uploader?: string | null;
  day_snapshot: Snapshot | null;
  availability: Availability;
  imports: SourceRecord[];
  history: Snapshot[];
};

type WriteRequest = { text: string; fee: string } | { refresh: number } | { fee_work_id: number; fee: string } |
  { delete_work_id: number; record_key: string };
type FeeFeedback = { id: number; message: string; error?: boolean };

const metricLabels = { likes: "点赞", comments: "评论", favorites: "收藏", shares: "转发" } as const;
const platformLabels = { douyin: "抖音", xiaohongshu: "小红书" } as const;
type Platform = keyof typeof platformLabels;
const feePattern = "[0-9]{1,7}([.][0-9]{1,2})?";
const feeFormat = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY" });
const pageSize = 20;
const sortOptions = {
  newest: "默认顺序", likesDesc: "点赞从高到低", likesAsc: "点赞从低到高",
  commentsDesc: "评论从高到低", commentsAsc: "评论从低到高",
} as const;
type Sort = keyof typeof sortOptions;

function values(snapshot?: Snapshot, source?: SourceRecord) {
  const raw = source?.source_data;
  return snapshot ?? {
    likes: raw?.["点赞数"] ?? raw?.["点赞量"] ?? raw?.["点赞"],
    comments: raw?.["评论数"] ?? raw?.["评论"],
    favorites: null,
    shares: null,
  };
}

function metrics(snapshot?: Snapshot, source?: SourceRecord) {
  const result = values(snapshot, source);
  return (Object.keys(metricLabels) as (keyof typeof metricLabels)[]).map((key) => (
    <td className="cv-metric" key={key} data-label={metricLabels[key]}>
      {snapshot?.metric_labels?.[key] ?? result[key]?.toLocaleString("zh-CN") ?? "—"}
    </td>
  ));
}

function accountIds(work: Work) {
  return [work.creator_id, ...work.imports.map((record) => record.source_data["抖音账号"]), work.creator_uid].filter(Boolean) as string[];
}

function dayData(work: Work, day: string) {
  return {
    snapshot: day ? (work.day_snapshot?.day === day ? work.day_snapshot : undefined) : work.history[0],
    source: day ? work.imports.find((record) => record.day === day) : work.imports[0],
  };
}

function compareMetric(a: Work, b: Work, sort: Exclude<Sort, "newest">, day: string) {
  const key = sort.startsWith("likes") ? "likes" : "comments";
  const value = (work: Work) => {
    const { snapshot, source } = dayData(work, day);
    const count = values(snapshot, source)[key];
    return typeof count === "number" || /^\d+$/.test(count ?? "") ? Number(count) : null;
  };
  const first = value(a);
  const second = value(b);
  if (first === null || second === null) return Number(first === null) - Number(second === null);
  return sort.endsWith("Desc") ? second - first : first - second;
}

export default function CreatorVideos({ ledger = "creator-videos" }: { ledger?: VideoLedger }) {
  const employee = ledger === "employee-videos";
  const paidMedia = ledger === "paid-media-videos";
  const authorLabel = employee || paidMedia ? "作者" : "达人";
  const feeLabel = paidMedia ? "应付媒体费用" : "应付达人费用";
  const [works, setWorks] = useState<Work[] | null>(null);
  const [unlinked, setUnlinked] = useState<SourceRecord[]>([]);
  const [failureRates, setFailureRates] = useState<Record<RateMode, DailyRate[]>>({ entry: [], check: [] });
  const [filter, setFilter] = useState<Availability | "">("");
  const [platformFilter, setPlatformFilter] = useState<Platform | "">("");
  const [search, setSearch] = useState("");
  const [creatorId, setCreatorId] = useState("");
  const [entryDay, setEntryDay] = useState("");
  const [dataDay, setDataDay] = useState("");
  const [loadedDay, setLoadedDay] = useState("");
  const [sort, setSort] = useState<Sort>("newest");
  const [page, setPage] = useState(1);
  const [text, setText] = useState("");
  const [fee, setFee] = useState("");
  const [uploader, setUploader] = useState("");
  const [canDelete, setCanDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [feeFeedback, setFeeFeedback] = useState<FeeFeedback | null>(null);
  const writeVersion = useRef(0);
  const request = useCallback(async (body?: WriteRequest, signal?: AbortSignal) => {
    const version = writeVersion.current;
    const query = dataDay ? `?day=${encodeURIComponent(dataDay)}` : "";
    const response = await fetch(`${dashboardBasePath()}/api/geo-capture/${ledger}${query}`, {
      cache: "no-store",
      signal,
      ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
    if (response.status === 401) throw new Error("工作台登录已失效，请重新登录后刷新");
    if (!response.headers.get("content-type")?.includes("application/json")) {
      throw new Error(`视频接口未返回数据（HTTP ${response.status}）`);
    }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "暂时无法读取作品");
    if (body) writeVersion.current += 1;
    else if (version !== writeVersion.current) return;
    setWorks(result.works);
    setUnlinked(result.unlinked ?? []);
    setFailureRates(result.failure_rates ?? { entry: [], check: [] });
    setCanDelete(result.can_delete === true);
    if (employee) setUploader(result.current_uploader ?? "");
    setLoadedDay(dataDay);
  }, [dataDay, employee, ledger]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        await request(undefined, controller.signal);
        if (active) setError("");
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "读取失败");
      } finally {
        if (active) timeout = setTimeout(poll, 6000);
      }
    }
    void poll();
    return () => { active = false; controller.abort(); clearTimeout(timeout); };
  }, [request]);

  async function update(body: WriteRequest) {
    setBusy(true);
    const feeWorkId = "fee_work_id" in body ? body.fee_work_id : null;
    if (feeWorkId !== null) setFeeFeedback(null);
    else { setNotice(""); setActionError(""); }
    try {
      await request(body);
      if ("text" in body) {
        setText("");
        setFee("");
        setNotice("已提交。新作品以今天（北京时间）为录入日期。");
      } else if ("refresh" in body) {
        setNotice("已安排优先核查，作品状态和互动数据会自动更新。");
      } else if ("fee_work_id" in body) {
        setFeeFeedback({ id: body.fee_work_id, message: "费用已保存" });
      } else {
        setSelected((current) => current === body.delete_work_id ? null : current);
        setNotice("作品记录已删除。");
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "提交失败";
      if (feeWorkId !== null) setFeeFeedback({ id: feeWorkId, message, error: true });
      else setActionError(message);
    } finally {
      setBusy(false);
    }
  }

  const count = (status: Availability) => works?.filter((work) => (work.availability ?? "unchecked") === status).length ?? 0;
  const term = search.trim().toLocaleLowerCase();
  const idTerm = creatorId.trim().toLocaleLowerCase();
  const loadingDay = loadedDay !== dataDay;
  const visible = (loadingDay ? [] : works)?.filter((work) => (!filter || (work.availability ?? "unchecked") === filter) &&
    (!platformFilter || (work.platform ?? "douyin") === platformFilter) &&
    (!entryDay || work.entry_day === entryDay) &&
    (!dataDay || work.day_snapshot?.day === dataDay || work.imports.some((record) => record.day === dataDay)) &&
    (!idTerm || accountIds(work).some((id) => id.toLocaleLowerCase().includes(idTerm))) &&
    (!term || [work.title, work.author, work.uploader, work.imports?.[0]?.source_data["用户名"], work.url, work.input_url]
      .some((value) => value?.toLocaleLowerCase().includes(term)))) ?? [];
  if (sort !== "newest") visible.sort((a, b) => compareMetric(a, b, sort, dataDay));
  const pages = Math.max(1, Math.ceil(visible.length / pageSize));
  const currentPage = Math.min(page, pages);
  const start = (currentPage - 1) * pageSize;
  const rows = visible.slice(start, start + pageSize);

  function changeFilter(value: Availability | "") {
    setFilter(value);
    setPage(1);
  }

  return (
    <section className="cv-page">
      <div className="cv-overview" aria-label="作品概览">
        {([["跟踪中", works?.length ?? 0, ""], ["可访问", count("available"), "available"], ["确认不可用", count("unavailable"), "unavailable"]] as const).map(([label, value, status]) => (
          <button className="cv-stat" type="button" key={label} data-tone={status} aria-pressed={filter === status} onClick={() => changeFilter(status)}>
            <span>{label}</span><strong>{works ? value : "—"}</strong>
          </button>
        ))}
        <div className="cv-stat" data-tone="missing"><span>缺少链接</span><strong>{works ? unlinked.length : "—"}</strong></div>
      </div>

      {works && <FailureRates rates={failureRates} />}

      <form className="cv-form" onSubmit={(event) => { event.preventDefault(); void update({ text, fee }); }}>
        <div className="cv-formHeading">
          <h2>添加作品</h2>
          {employee && uploader && <span>上传账号 <strong>{uploader}</strong></span>}
        </div>
        <div className="cv-formInput">
          <label className="cv-srOnly" htmlFor="creator-video-links">抖音或小红书分享文案及作品链接</label>
          <textarea id="creator-video-links" rows={2} value={text} maxLength={10000}
            placeholder="粘贴抖音或小红书分享文案或链接，多条可分行粘贴"
            onChange={(event) => setText(event.target.value)} />
          {!employee && <label className="cv-feeField">每条应付费用（元）
            <input inputMode="decimal" pattern={feePattern} maxLength={10} placeholder="选填"
              value={fee} onChange={(event) => setFee(event.target.value)} />
          </label>}
          <button className="cv-primary" type="submit" disabled={busy || !text.trim()}>＋ 添加作品</button>
        </div>
        {notice && <p className="cv-notice" role="status">{notice}</p>}
      </form>
      {actionError && <p className="cv-error" role="alert">{actionError}</p>}
      {error && <p className="cv-error" role="alert">{error}</p>}

      <section className="cv-ledger" aria-label="作品台账">
        <header className="cv-toolbar">
          <h2>作品台账</h2>
          <div className="cv-filters">
            <label>搜索作品或{employee ? "上传人" : authorLabel}<input type="search" placeholder={`作品标题、${employee ? "上传人" : `${authorLabel}名`}`}
              value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
            <label>{authorLabel} ID / 平台账号<input type="search" placeholder="输入 ID 或平台账号" value={creatorId}
              onChange={(event) => { setCreatorId(event.target.value); setPage(1); }} /></label>
            <label>平台<select aria-label="平台" value={platformFilter} onChange={(event) => { setPlatformFilter(event.target.value as Platform | ""); setPage(1); }}>
              <option value="">全部平台</option>
              {Object.entries(platformLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>录入日期<input type="date" value={entryDay} onChange={(event) => { setEntryDay(event.target.value); setPage(1); }} /></label>
            <label>数据日期<input type="date" value={dataDay} onChange={(event) => { setDataDay(event.target.value); setPage(1); }} /></label>
            <label>作品状态<select value={filter} onChange={(event) => changeFilter(event.target.value as Availability | "")}>
              <option value="">全部状态</option>
              {(Object.keys(availabilityLabels) as Availability[]).map((status) => (
                <option key={status} value={status}>{availabilityLabels[status]}（{count(status)}）</option>
              ))}
            </select></label>
            <label>排序<select value={sort} onChange={(event) => { setSort(event.target.value as Sort); setPage(1); }}>
              {Object.entries(sortOptions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
          </div>
        </header>
        {dataDay && <p className="cv-dayNotice">查看 {dataDay} 的互动数据，作品状态显示最近一次核查结果。</p>}
        {(!works || loadingDay) && !error && <p className="cv-empty">正在读取作品…</p>}
        {works && !loadingDay && !rows.length && <p className="cv-empty">{works.length ? "没有符合条件的作品。" : "还没有跟踪作品。"}</p>}
        {!!rows.length && (
          <div className="cv-tableWrap">
            <table className="cv-table" aria-label={employee ? "员工视频作品数据" : paidMedia ? "付费媒体作品数据" : "达人作品数据"}>
              <colgroup><col /><col className="cv-statusCol" /><col span={4} className="cv-metricCol" /><col className="cv-feeCol" /><col className="cv-timeCol" /><col className={`cv-actionsCol${canDelete ? " cv-actionsCol--deletable" : ""}`} /></colgroup>
              <thead><tr><th>作品 / {authorLabel}</th><th>作品状态</th>{Object.values(metricLabels).map((label) => <th key={label}>{label}</th>)}<th>{employee ? "上传人" : feeLabel}</th><th>发布时间</th><th>操作</th></tr></thead>
              <tbody>
                {rows.map((work) => {
                  const { snapshot, source } = dayData(work, dataDay);
                  const status = work.availability ?? "unchecked";
                  const checkFailed = work.last_check_status === "unknown";
                  const statusLabel = checkFailed && (status === "available" || status === "unavailable")
                    ? `上次${availabilityLabels[status]}` : availabilityLabels[status];
                  const author = work.author || work.imports[0]?.source_data["用户名"];
                  const platform = work.platform ?? "douyin";
                  const platformLabel = platformLabels[platform];
                  const timestamp = work.published_at;
                  const open = selected === work.id;
                  return (
                    <Fragment key={work.id}>
                      <tr className="cv-workRow" data-open={open}>
                        <td className="cv-workCell">
                          <a href={work.url || work.input_url} target="_blank" rel="noreferrer" title={work.title || undefined}>
                            {work.title || (author ? `${author}的${platformLabel}作品` : `${platformLabel}作品`)}
                          </a>
                          <div className="cv-workAuthor">
                            <span className="cv-platform" data-platform={platform}>{platformLabel}</span>
                            <span>{author || `${authorLabel}待识别`}</span>
                          </div>
                          <span>{work.entry_day ? `录入 ${work.entry_day}` : "录入日期不详"}{accountIds(work)[0] && ` · ID ${accountIds(work)[0]}`}</span>
                        </td>
                        <td className="cv-statusCell">
                          <span className="cv-badge" data-tone={status}>{statusLabel}</span>
                          {work.checking ? <small>正在核查</small> : !!work.pending ? <small>等待核查</small> :
                            work.last_attempt && <small title={checkFailed && work.last_error ? work.last_error : work.last_attempt.slice(0, 16).replace("T", " ")}>
                              {checkFailed ? "核查失败" : "核查"} {work.last_attempt.slice(5, 16).replace("T", " ")}
                            </small>}
                        </td>
                        {metrics(snapshot, source)}
                        {employee ? <td className="cv-uploaderCell">
                          <span className="cv-feeCaption" aria-hidden="true">上传人</span>
                          {work.uploader || "—"}
                        </td> : <td className="cv-feeCell">
                          <span className="cv-feeCaption" aria-hidden="true">{feeLabel}</span>
                          {work.fee_cents == null ? <small>未录入</small> : feeFormat.format(work.fee_cents / 100)}
                        </td>}
                        <td className="cv-timeCell" title={timestamp?.slice(0, 16).replace("T", " ")}>
                          {timestamp ? <time dateTime={timestamp}>{timestamp.slice(0, 10)}<small>{timestamp.slice(11, 16)}</small></time> : "—"}
                        </td>
                        <td className="cv-actions">
                          <button type="button" aria-expanded={open} onClick={() => { setFeeFeedback(null); setSelected(open ? null : work.id); }}>{open ? "收起" : "详情"}</button>
                          <button type="button" disabled={busy || !!work.pending || work.checking} onClick={() => void update({ refresh: work.id })}>刷新</button>
                          {canDelete && <button className="cv-deleteButton" type="button" disabled={busy} onClick={() => {
                            if (window.confirm(`确认删除“${work.title || work.author || "这条作品"}”？\n作品及采集记录将从台账移除。`)) {
                              void update({ delete_work_id: work.id, record_key: work.record_key });
                            }
                          }}>删除</button>}
                        </td>
                      </tr>
                      {open && <tr className="cv-detailRow"><td colSpan={9}><WorkDetails work={work} employee={employee} busy={busy}
                        authorLabel={authorLabel} feeLabel={feeLabel}
                        feeFeedback={feeFeedback?.id === work.id ? feeFeedback : null}
                        onFeeSave={(fee) => void update({ fee_work_id: work.id, fee })} /></td></tr>}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!!visible.length && <footer className="cv-pagination">
          <span>第 {start + 1}–{start + rows.length} 条，共 {visible.length} 条</span>
          <div>
            <button type="button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>上一页</button>
            <span>{currentPage} / {pages}</span>
            <button type="button" disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>下一页</button>
          </div>
        </footer>}
      </section>
      {(count("unavailable") > 0 || unlinked.length > 0) && <details className="cv-sources">
        <summary>失效作品链接（{count("unavailable") + unlinked.length} 条）</summary>
        <div className="cv-invalidLinks">
          <h3>确认不可用（{count("unavailable")} 条）</h3>
          {works?.filter((work) => work.availability === "unavailable").map((work) => (
            <div className="cv-invalidItem" key={work.id}>
              <a href={work.url || work.input_url} target="_blank" rel="noreferrer">
                {work.title || work.author || work.imports[0]?.source_data["用户名"] || work.input_url}
              </a>
              <small>{work.last_check_status === "unknown" ? "上次确认不可用，复核失败" : work.last_error || "作品不可访问"}{work.entry_day && ` · 录入 ${work.entry_day}`}</small>
            </div>
          ))}
          {!!unlinked.length && <SourceRecords title={`缺少可核查链接（${unlinked.length} 条）`} records={unlinked} />}
        </div>
      </details>}
    </section>
  );
}

function FailureRates({ rates }: { rates: Record<RateMode, DailyRate[]> }) {
  const [mode, setMode] = useState<RateMode>("entry");
  const rows = rates[mode];
  return (
    <section className="cv-rates" aria-label="每日失效率">
      <header className="cv-toolbar">
        <h2>每日失效率</h2>
        <div className="cv-rateModes" aria-label="失效率统计方式">
          <button type="button" aria-pressed={mode === "entry"} onClick={() => setMode("entry")}>按录入日期</button>
          <button type="button" aria-pressed={mode === "check"} onClick={() => setMode("check")}>按核查日期</button>
        </div>
      </header>
      {rows.length ? <div className="cv-rateTableWrap" tabIndex={0} role="region" aria-label="每日失效率列表">
        <table aria-label="每日失效率数据">
          <thead><tr><th>{mode === "entry" ? "录入日期" : "核查日期"}</th><th>失效率</th><th>确认不可用</th><th>可访问</th><th>待确认</th>{mode === "entry" && <th>缺链接</th>}<th>合计</th></tr></thead>
          <tbody>{rows.map((row) => {
            const confirmed = row.available + row.unavailable;
            const rate = confirmed ? (row.unavailable / confirmed * 100).toFixed(1) + "%" : "—";
            return <tr key={row.day ?? "unknown"}>
              <th scope="row">{row.day ?? "日期不详"}</th>
              <td><strong>{rate}</strong>{confirmed > 0 && <small>{row.unavailable} / {confirmed}</small>}</td>
              <td>{row.unavailable}</td><td>{row.available}</td><td>{row.unresolved}</td>
              {mode === "entry" && <td>{row.unlinked}</td>}<td>{row.total}</td>
            </tr>;
          })}</tbody>
        </table>
      </div> : <p className="cv-empty">暂无日期记录。</p>}
    </section>
  );
}

function WorkDetails({ work, employee, busy, authorLabel, feeLabel, feeFeedback, onFeeSave }: {
  work: Work; employee: boolean; busy: boolean; authorLabel: string; feeLabel: string;
  feeFeedback: FeeFeedback | null; onFeeSave: (fee: string) => void;
}) {
  const capturedAt = work.history[0]?.captured_at;
  const platform = work.platform ?? "douyin";
  return (
    <section className="cv-details" aria-label="作品详情">
      <h3>作品详情</h3>
      <p className="cv-fullTitle">{work.title || "待获取作品文案"}</p>
      <p className="cv-detailMeta">
        {work.entry_day && <span>录入日期 {work.entry_day}</span>}
        {capturedAt && <span>最近采集 {capturedAt.slice(0, 16).replace("T", " ")}</span>}
        {employee && work.uploader && <span>上传人 {work.uploader}</span>}
        {!!accountIds(work).length && <span>{authorLabel} ID / {platform === "douyin" ? "抖音号" : "小红书号"} {accountIds(work).join(" / ")}</span>}
        {work.last_check_status === "unknown" && work.last_confirmed_at && <span>上次确认 {work.last_confirmed_at.slice(0, 16).replace("T", " ")}</span>}
        {work.last_attempt && <span>{work.last_check_status === "unknown" ? "核查失败" : "核查时间"} {work.last_attempt.slice(0, 16).replace("T", " ")}</span>}
        {work.last_error && <span>{work.last_error}</span>}
        <a href={work.url || work.input_url} target="_blank" rel="noreferrer">打开{platformLabels[platform]} ↗</a>
      </p>
      {!employee && <form className="cv-feeEditor" onSubmit={(event) => {
        event.preventDefault();
        onFeeSave(String(new FormData(event.currentTarget).get("fee") ?? ""));
      }}>
        <label className="cv-feeField">{feeLabel}（元）
          <input key={work.fee_cents ?? "empty"} name="fee" inputMode="decimal" pattern={feePattern} maxLength={10}
            placeholder="未录入" defaultValue={work.fee_cents == null ? "" : (work.fee_cents / 100).toFixed(2)} />
        </label>
        <button type="submit" disabled={busy}>保存费用</button>
        {feeFeedback && <span className={feeFeedback.error ? "cv-error" : "cv-notice"}
          role={feeFeedback.error ? "alert" : "status"}>{feeFeedback.message}</span>}
      </form>}
      {!!work.history.length && <>
        <h3>采集历史</h3>
        <div className="cv-history">
          <table aria-label="采集历史">
            <thead><tr><th>日期</th>{Object.values(metricLabels).map((label) => <th key={label}>{label}</th>)}</tr></thead>
            <tbody>{work.history.map((row) => <tr key={row.day}><td>{row.day}</td>{metrics(row)}</tr>)}</tbody>
          </table>
        </div>
      </>}
      {!!work.imports?.length && <SourceRecords title="导入的原始记录" records={work.imports} />}
    </section>
  );
}

function SourceRecords({ title, records }: { title: string; records: SourceRecord[] }) {
  return (
    <details className="cv-sources">
      <summary>{title}</summary>
      {records.map((record) => (
        <article className="cv-sourceRecord" key={`${record.workbook}:${record.sheet}:${record.sheet_row}`}>
          <h3>{record.source_data["用户名"] || "未填写达人"} <small>{record.sheet} 第 {record.sheet_row} 行</small></h3>
          <dl>{Object.entries(record.source_data).filter(([key, value]) => key !== "用户名" && value).map(([key, value]) => (
            <div key={key}><dt>{key}</dt><dd>{value}</dd></div>
          ))}</dl>
        </article>
      ))}
    </details>
  );
}
