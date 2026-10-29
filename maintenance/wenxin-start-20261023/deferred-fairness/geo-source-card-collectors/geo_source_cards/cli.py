"""Local, one-process-at-a-time CLI for the three source collectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from .journal import Journal
from .runtime import atomic_json, process_lock, runtime_root
from .session_watch import LoginRequiredError
from .pipeline_control import ensure_running, event, pause, PipelinePaused

BEIJING = timezone(timedelta(hours=8))
MODELS = ("baidu_ai", "wenxin_card", "deepseek")

def deepseek_rate_path(root):
    """Caller holds the account flock; carry legacy batch spacing into shared state."""
    original=Path(root)/'deepseek_last_prompt.json'
    target=Path(os.environ.get('GEO_DEEPSEEK_RATE_STATE',str(original)))
    if target==original:return target
    paths=[original,target]
    if os.environ.get('GEO_DEEPSEEK_SEED_ROOT'):
        paths+=list(Path(os.environ['GEO_DEEPSEEK_SEED_ROOT']).glob('*/collector/deepseek_last_prompt.json'))
    latest=max([json.loads(p.read_text()).get('last_prompt_epoch',0) for p in paths if p.exists()] or [0])
    current=json.loads(target.read_text()).get('last_prompt_epoch',0) if target.exists() else -1
    if latest>current:atomic_json(target,{'last_prompt_epoch':latest})
    return target


def confirmed_no_card(snapshot, question):
    """An empty page or partially rendered card cannot prove absence."""
    url = urlsplit(str(snapshot.get("url") or ""))
    query = parse_qs(url.query).get("wd", [""])[0]
    compact = lambda value: "".join(unicodedata.normalize("NFKC", str(value)).split())
    return bool(
        url.hostname in {"www.baidu.com", "baidu.com"}
        and url.path == "/s"
        and compact(query) == compact(question)
        and compact(snapshot.get("query")) == compact(question)
        and snapshot.get("readyState") == "complete"
        and snapshot.get("cardPresent") is False
        and int(snapshot.get("searchResultsCount") or 0) > 0
    )


def create_collector(model: str, *, show_browser: bool = False) -> Any:
    if model == "deepseek":
        from web_collectors.collector import BrowserCollector

        return BrowserCollector("deepseek", headless=not show_browser)
    os.environ["WENXIN_STEALTH_HEADLESS"] = "0" if show_browser else "1"
    from wenxin_monitor.controller import WenxinWebCollector

    if model == "baidu_ai":

        class StrictBaiduCardCollector(WenxinWebCollector):
            strict_card = True

            def collect_wenxin_search(
                self, question: str, timeout: int = 90
            ) -> dict[str, Any]:
                from wenxin_monitor.controller import BAIDU_AI_SNAPSHOT_JS

                snapshot = self.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
                # Some Baidu answer cards show full prose but expose neither
                # citations nor a reference drawer. Preserve that observation,
                # without inventing sources or passing the full-result gate.
                if (snapshot.get('ok') and snapshot.get('cardPresent') and not snapshot.get('folded')
                    and snapshot.get('readyState')=='complete' and self._query_key(snapshot.get('query'))==self._query_key(question)
                    and not snapshot.get('citationCount')):
                    provenance=self.public_card_references()
                    time.sleep(2)
                    final=self.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
                    if (final.get('body')==snapshot.get('body') and final.get('ok') and not final.get('folded')
                        and self._query_key(final.get('query'))==self._query_key(question)):
                        sources=self._normalize_sources(provenance.get('sources',[]))
                        expected=provenance.get('declared_count',0)
                        common={'capture_mode':'baidu_search_ai','url':final['url'],'body':final['body'],
                                'body_capture_complete':True,'sources':sources,'expected_source_count':expected or None,
                                'page_navigation_id':getattr(self,'_last_navigation_id',''),'fresh_search':True,'verified_question':question,
                                'source_exposure_evidence':provenance,'card_available':True}
                        if expected>0 and len(sources)>=expected:
                            return {**common,'source_capture_complete':True}
                        if not sources and not expected and not provenance.get('drawer_opened'):
                            return {**common,'availability':'body_only','source_capture_complete':False,
                                    'source_exposure':'not_publicly_exposed',
                                    'capture_warning':'百度卡片正文已保存；页面未展示公开引用，不计完整信源成功或负样本'}
                atomic_json(
                    runtime_root()
                    / "diagnostics"
                    / f"baidu-card-{time.time_ns()}.json",
                    {
                        "question": question,
                        "snapshot": snapshot,
                        "status": "card_not_complete",
                    },
                )
                if not self._is_security_verification(snapshot) and confirmed_no_card(
                    snapshot, question
                ):
                    return {
                        "capture_mode": "baidu_search_ai",
                        "availability": "no_card",
                        "url": snapshot["url"],
                        "body": "",
                        "sources": [],
                        "body_capture_complete": True,
                        "source_capture_complete": True,
                        "expected_source_count": 0,
                        "absence_evidence": snapshot,
                        "page_navigation_id": getattr(self, "_last_navigation_id", ""),
                        "fresh_search": bool(getattr(self, "_last_navigation_id", "")),
                        "verified_question": question,
                    }
                raise RuntimeError(
                    "百度 AI 卡片未完整呈现，已保存页面观测，不能用文心卡片代替"
                )

        return StrictBaiduCardCollector()
    return WenxinWebCollector()


def collect_one(collector: Any, model: str, question: str) -> dict[str, Any]:
    if model == "baidu_ai":
        result = collector.collect_search(question, timeout=150)
    elif model == "wenxin_card":
        result = collector.collect_wenxin_search(question, timeout=150)
    else:
        result = collector.collect(question, timeout=240)
    return normalize_result(result,model,question)


def normalize_result(result,model,question):
    if not isinstance(result, dict):
        raise RuntimeError("采集器未返回结构化结果")
    expected_mode = {
        "baidu_ai": "baidu_search_ai",
        "wenxin_card": "baidu_wenxin_search",
    }.get(model)
    if expected_mode and result.get("capture_mode") != expected_mode:
        raise RuntimeError("采集模式不匹配")
    body = str(result.get("body") or result.get("reply") or "").strip()
    no_card = (
        model == "baidu_ai"
        and result.get("availability") == "no_card"
        and confirmed_no_card(result.get("absence_evidence", {}), question)
    )
    if not body and not no_card:
        raise RuntimeError("回答正文为空，本轮不保存")
    sources = []
    seen: set[str] = set()
    for item in result.get("sources") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("href") or "").strip()
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or url in seen:
            continue
        seen.add(url)
        sources.append(
            {
                "url": url,
                "title": str(item.get("title") or "").strip(),
                "media": str(item.get("media") or "").strip(),
            }
        )
    complete = result.get("source_capture_complete")
    if not isinstance(complete, bool):
        complete = None
    expected = result.get("expected_source_count")
    entry_indexes = {
        item.get("index")
        for item in result.get("source_entries") or []
        if isinstance(item, dict) and item.get("url") in seen
    }
    entries_complete = (
        isinstance(expected, int)
        and not isinstance(expected, bool)
        and expected >= 0
        and set(range(1, expected + 1)).issubset(entry_indexes)
    )
    if (
        complete is True
        and isinstance(expected, int)
        and not isinstance(expected, bool)
        and expected >= 0
        and len(sources) < expected
        and not entries_complete
    ):
        complete = False
    if result.get("body_capture_complete") is False:
        raise RuntimeError("回答正文尚未完成")
    return {
        **result,
        "body": body,
        "sources": sources,
        "source_capture_complete": complete,
        "source_capture_status": "unknown"
        if complete is None
        else "complete"
        if complete
        else "incomplete",
        "source_count": len(sources),
        "captured_question": question,
    }


class CaptureDrainRequested(RuntimeError):
    pass


def ensure_capture_allowed():
    marker=os.environ.get('GEO_CAPTURE_PAUSE_FILE')
    if marker and Path(marker).exists():raise CaptureDrainRequested('Drain before next submission')


def report_capture_phase(phase,task=None,**details):
    path=os.environ.get('GEO_CAPTURE_PROGRESS_FILE')
    if path:
        atomic_json(Path(path),{'phase':phase,'changed_at':time.time(),
                               'ordinal':task['ordinal']+1 if task else None,**details})


def wait_for_deepseek_slot(
    state_path: Path,
    min_interval: int = 300,
    *,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
    check_session: Callable[[], None] | None = None,
) -> None:
    """Persist prompt start times so a restart cannot bypass the 5-minute gap."""
    if min_interval < 300:
        raise ValueError("DeepSeek 每次新提问间隔不能少于 300 秒")
    previous = 0.0
    try:
        previous = float(
            json.loads(state_path.read_text(encoding="utf-8")).get("last_prompt_epoch")
            or 0
        )
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(
            "DeepSeek rate-limit state is unreadable; refusing to bypass the interval"
        ) from exc
    if check_session:
        check_session()
    remaining = previous + min_interval - clock()
    next_session_check=clock()+180
    while remaining > 0:
        ensure_capture_allowed()
        sleep(min(remaining,3) if os.environ.get('GEO_CAPTURE_PAUSE_FILE') else min(remaining, 180) if check_session else remaining)
        if check_session and (not os.environ.get('GEO_CAPTURE_PAUSE_FILE') or clock()>=next_session_check):
            check_session()
            next_session_check=clock()+180
        remaining = previous + min_interval - clock()
    ensure_capture_allowed()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(state_path, {"last_prompt_epoch": clock()})


def questions_from_args(args: argparse.Namespace) -> list[str]:
    if args.question:
        return [args.question]
    if args.questions_file:
        lines = Path(args.questions_file).read_text(encoding="utf-8").splitlines()
        return list(dict.fromkeys(line for line in lines if line.strip()))
    raise ValueError("请提供 --question 或 --questions-file")


def wait_for_search_slot(path, interval=60, *, clock=time.time, sleep=time.sleep):
    if interval < 0:
        raise ValueError("Search interval cannot be negative")
    try:
        previous = float(json.loads(path.read_text("utf8"))["last_search_epoch"])
        if not __import__("math").isfinite(previous):
            raise ValueError("Invalid search timestamp")
    except FileNotFoundError:
        previous = 0
    except (KeyError, ValueError, TypeError, OSError) as error:
        raise RuntimeError(
            "Search rate state is unreadable; refusing to bypass interval"
        ) from error
    remaining = previous + interval - clock()
    while remaining > 0:
        ensure_capture_allowed()
        sleep(min(remaining,3) if os.environ.get('GEO_CAPTURE_PAUSE_FILE') else remaining)
        remaining=previous+interval-clock()
    ensure_capture_allowed()
    atomic_json(path, {"last_search_epoch": clock()})


def collect_with_completion_fence(collector, model, question, state_path):
    """Keep the next slot behind this observation's end, even on read failure.

    A reservation before fsync/navigation is not an exact emission timestamp.
    Fencing at completion conservatively guarantees the configured minimum
    between requests without assuming scheduler/fsync latency is constant.
    This never retries an input or changes its question.
    """
    try:
        return collect_one(collector, model, question)
    finally:
        atomic_json(state_path, {"last_prompt_epoch" if model == "deepseek" else "last_search_epoch": time.time(),
                                 "fence": "previous_observation_finished"})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="百度 AI / 文心 / DeepSeek 信源采集")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        help="Login, journal and result directory outside source code",
    )
    parser.add_argument(
        "--batch", help="Reuse this identifier to resume completed/pending tasks safely"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Inspect journal without launching a browser",
    )
    parser.add_argument("--require-sources", action="store_true")
    parser.add_argument(
        "--bounded-search-recovery",
        action="store_true",
        help="Persist cooling and bounded deferred recovery for Baidu/Wenxin only",
    )
    parser.add_argument("--require-complete-sources", action="store_true")
    parser.add_argument(
        "--optional-baidu",
        action="store_true",
        help="Record failed Baidu supplements without blocking required Wenxin capture",
    )
    parser.add_argument(
        "--recover-read-failures",
        action="store_true",
        help="One explicit reload after diagnosed Baidu read-only failures; never DeepSeek",
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--question")
    choice.add_argument("--questions-file", type=Path)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--max-new-captures", type=int,
                        help="Yield after this many durable results, retaining the original batch")
    parser.add_argument('--max-search-attempts',type=int,
                        help='Release the shared browser after bounded read-only attempts, including failures')
    parser.add_argument(
        "--ready", action="store_true", help="仅检查就绪状态，不发起提问"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Wait up to 600 seconds for manual DeepSeek login",
    )
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-deepseek-interval", type=int, default=300)
    parser.add_argument("--min-search-interval", type=int, default=60)
    args = parser.parse_args(argv)
    if not 1 <= args.rounds <= 20:
        parser.error("--rounds 必须为 1 到 20")
    if args.max_new_captures is not None and args.max_new_captures < 1:
        parser.error("--max-new-captures must be positive")
    if args.max_search_attempts is not None and (args.max_search_attempts<1 or args.model=='deepseek'):
        parser.error('--max-search-attempts requires a positive limit and a read-only search model')
    if args.min_deepseek_interval < 300:
        parser.error("--min-deepseek-interval 不能小于 300 秒")
    if args.min_search_interval < 0:
        parser.error("--min-search-interval 不能为负数")
    if not args.status and not args.model:
        parser.error("--model is required for collection/readiness")
    if args.login and args.model != "deepseek":
        parser.error("--login currently supports DeepSeek only")
    if args.login:
        args.show_browser = True
    if (
        not args.status
        and not args.ready
        and not args.login
        and not (args.question or args.questions_file)
    ):
        parser.error("采集时需要 --question 或 --questions-file")
    return args


def run(args: argparse.Namespace) -> int:
    if getattr(args, "runtime_dir", None):
        os.environ["GEO_COLLECTOR_RUNTIME"] = str(args.runtime_dir.resolve())
    root = runtime_root()
    with process_lock(root / "collector.lock"):
        journal = Journal(root / "tasks.sqlite")
        try:
            if getattr(args, "status", False):
                rows = [
                    dict(row)
                    for row in journal.db.execute(
                        "select task_id,batch,model,state,error from captures order by rowid"
                    )
                ]
                print(json.dumps(rows, ensure_ascii=False))
                return 0
            return _run_locked(args, root, journal)
        finally:
            journal.close()


def _answer_signature(result):
    payload = (
        str(result["body"])
        + "\n"
        + "\n".join(sorted(item["url"] for item in result["sources"]))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _run_locked(args, root, journal):
    collector = None
    pipeline = os.environ.get("GEO_PIPELINE_ROOT")
    try:
        if getattr(args, "login", False):
            collector = create_collector(args.model, show_browser=True)
            collector.wait_for_login_cookies(timeout=600)
            print(json.dumps({"model": args.model, "ready": True}, ensure_ascii=False))
            return 0
        if args.ready:
            collector = create_collector(args.model, show_browser=args.show_browser)
            status = (
                collector.check_ready()
                if args.model == "deepseek"
                else collector.account_identity()
            )
            ready = bool(
                status.get("ok", status.get("ready", args.model != "deepseek"))
            )
            print(json.dumps({"model": args.model, "ready": ready}, ensure_ascii=False))
            return 0 if ready else 2
        questions = questions_from_args(args)
        output = args.output or root / "results" / (
            datetime.now(BEIJING).date().isoformat() + ".jsonl"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        batch = getattr(args, "batch", None) or uuid.uuid4().hex
        known = journal.db.execute(
            "select 1 from captures where output=? limit 1", (str(output.resolve()),)
        ).fetchone()
        if output.exists() and output.stat().st_size and not known:
            raise RuntimeError(
                "Output exists outside this journal; choose a new output path to preserve it"
            )
        tasks = journal.plan(batch, args.model, questions, args.rounds, output)
        from .search_recovery import unattended_enabled
        unattended=unattended_enabled(root)
        if unattended:
            journal.automatic_recovery(batch)
            tasks=journal.plan(batch,args.model,questions,args.rounds,output)
            if args.model=='deepseek':
                unresolved=next((task for task in tasks if task['state']=='needs_attention'),None)
                if unresolved:
                    url=journal.original_conversation(unresolved)
                    if not url:
                        report_capture_phase('original_identity_backoff',unresolved)
                        return 2
                    collector=create_collector(args.model,show_browser=args.show_browser)
                    report_capture_phase('original_conversation_readback',unresolved)
                    value=normalize_result(collector.resume(unresolved['question'],url),args.model,unresolved['question'])
                    reused=journal.db.execute("select 1 from captures where state='completed' and model='deepseek' and json_extract(result,'$.url')=?",(value.get('url'),)).fetchone()
                    if reused:raise RuntimeError('Recovered conversation belongs to an already completed task')
                    if not value.get('sources') or value.get('source_capture_complete') is not True:
                        raise RuntimeError('Original answer sources are not yet complete')
                    record={**value,'model':args.model,'question':unresolved['question'],'round':unresolved['round'],
                            'task_id':unresolved['task_id'],'batch':batch,'captured_at':datetime.now(BEIJING).isoformat(timespec='seconds')}
                    journal.complete_readback(unresolved['task_id'],record);journal.export(output)
                    atomic_json(deepseek_rate_path(root),{'last_prompt_epoch':time.time(),'fence':'original_readback_completed'})
                    return 0
        recovery = None
        if (
            getattr(args, "bounded_search_recovery", False) or pipeline
        ) and args.model in {"baidu_ai", "wenxin_card"}:
            from .search_recovery import SearchRecovery

            recovery = SearchRecovery(journal, root, optional_baidu=getattr(args, "optional_baidu", False))
            for task in tasks:
                if task["state"] == "needs_attention":
                    recovery.failure(
                        task,
                        task["error"] or "",
                        json.loads(task["result"]) if task["result"] else None,
                    )
            tasks = journal.plan(batch, args.model, questions, args.rounds, output)
        if getattr(args, "recover_read_failures", False):
            journal.recover_read_failures(batch)
            tasks = journal.plan(batch, args.model, questions, args.rounds, output)
        if any(task["state"] == "needs_attention" for task in tasks):
            raise RuntimeError(
                "Batch has an uncertain/failed capture; inspect --status before sending again"
            )
        print(json.dumps({"batch": batch, "planned": len(tasks)}, ensure_ascii=False))
        journal.export(output)
        seen_cards: dict[str, str] = {}
        saved = 0;search_attempts=0
        from collections import deque

        # A short browser lease must not retry the first failed query forever.
        if getattr(args,'max_search_attempts',None):
            tasks=sorted(tasks,key=lambda t:(t['started'] or 0,t['ordinal'],t['round']))
        pending_tasks = deque(tasks)
        while pending_tasks:
            task = pending_tasks.popleft()
            question, round_number = task["question"], task["round"]
            if task["state"] == "failed_deferred":
                continue
            if task["state"] == "completed":
                old_record = json.loads(task["result"])
                seen_cards.setdefault(
                    _answer_signature(old_record),
                    f"{args.model}:{question}:{round_number}",
                )
                continue
            ensure_running(pipeline)
            ensure_capture_allowed()
            if recovery:
                recovery.wait(pipeline)
            if collector is None:
                collector = create_collector(args.model, show_browser=args.show_browser)
                if args.model == "deepseek":
                    status = collector.check_ready()
                    if not status.get("ok"):
                        error = (
                            LoginRequiredError
                            if status.get("status") == "login_required"
                            else RuntimeError
                        )
                        raise error(str(status.get("message") or "DeepSeek 网页未就绪"))
            if args.model == "deepseek":

                def check_session():
                    ensure_running(pipeline)
                    collector.assert_session()

                collector.before_send = check_session
                last_path=deepseek_rate_path(root)
                previous=json.loads(last_path.read_text()).get('last_prompt_epoch',0) if last_path.exists() else 0
                report_capture_phase('rate_wait',task,next_at=previous+args.min_deepseek_interval)
                wait_for_deepseek_slot(
                    last_path,
                    args.min_deepseek_interval,
                    check_session=check_session,
                )
            else:
                rate=Path(os.environ.get('GEO_SEARCH_RATE_STATE',str(root/'last_search.json')))
                previous=json.loads(rate.read_text()).get('last_search_epoch',0) if rate.exists() else 0
                report_capture_phase('rate_wait',task,next_at=previous+getattr(args,'min_search_interval',60))
                wait_for_search_slot(
                    Path(os.environ.get("GEO_SEARCH_RATE_STATE", str(root / "last_search.json"))),
                    getattr(args, "min_search_interval", 60)
                )
            ensure_capture_allowed()
            journal.start(task["task_id"],submission=args.model=='deepseek')
            report_capture_phase('collecting',task)
            if pipeline:
                event(
                    pipeline,
                    "capture",
                    "开始本题采集",
                    model=args.model,
                    question=question,
                    ordinal=task["ordinal"] + 1,
                    total=len(questions),
                    task_id=task["task_id"],
                )
            result = None
            if args.model=='deepseek':
                journal.prepare_submission(task['task_id'])
                collector.on_send_intent=lambda snapshot:journal.submission(task['task_id'],snapshot,attempted=True)
                collector.on_send_receipt=lambda snapshot:journal.submission(task['task_id'],snapshot,attempted=False)
            try:
                if args.model in {'baidu_ai','wenxin_card'}:search_attempts+=1
                rate_path = deepseek_rate_path(root) if args.model == "deepseek" else Path(os.environ.get("GEO_SEARCH_RATE_STATE", str(root / "last_search.json")))
                result = collect_with_completion_fence(collector, args.model, question, rate_path)
                if unattended and args.model=='baidu_ai' and result.get('availability')=='no_card':
                    raise RuntimeError('Daily Baidu card is still missing; retry the read-only search instead of completing the round')
                if (
                    args.model == "deepseek"
                    and result.get("capture_mode") == "deepseek_web"
                ):
                    reused = journal.db.execute(
                        "select 1 from captures where model='deepseek' and state='completed' "
                        "and json_extract(result,'$.url')=? limit 1",
                        (result.get("url"),),
                    ).fetchone()
                    if reused:
                        raise RuntimeError(
                            "DeepSeek reused a recorded conversation; refusing mixed answers"
                        )
                if (
                    getattr(args, "require_sources", False)
                    and not result["sources"]
                    and result.get("availability") not in {"no_card", "body_only"}
                ):
                    raise RuntimeError("Required source links are missing")
                if (
                    getattr(args, "require_complete_sources", False)
                    and result["source_capture_complete"] is not True
                    and not (args.model=='baidu_ai' and result.get('availability')=='body_only'
                             and result.get('source_exposure')=='not_publicly_exposed'
                             and result.get('body_capture_complete') is True and result.get('source_exposure_evidence'))
                ):
                    raise RuntimeError("Source completeness is not proven")
            except Exception as exc:
                if recovery and not isinstance(exc, PipelinePaused):
                    recovery.evidence(collector, task)
                    recovered = recovery.failure(task, exc, result)
                    if recovered:
                        try:
                            collector.close()
                        finally:
                            collector = None
                        if pipeline:
                            event(
                                pipeline,
                                "capture_recovery",
                                "卡片失败，按持久化冷却与有界延期处理",
                                **recovered,
                            )
                        if not recovered["exhausted"]:
                            (
                                pending_tasks.append
                                if recovered["defer"]
                                else pending_tasks.appendleft
                            )(task)
                        if recovered["status"] == "waiting_verification":
                            raise RuntimeError(
                                "持续百度安全验证，等待人工处理"
                            ) from exc
                        if (getattr(args,'max_search_attempts',None)
                                and search_attempts>=args.max_search_attempts and not recovered['exhausted']):
                            report_capture_phase('yielding_search_browser',task)
                            return 0  # Pending stays pending; no success/absence is invented.
                        if (
                            recovered["exhausted"]
                            and args.model == "baidu_ai"
                            and getattr(args, "optional_baidu", False)
                        ):
                            with journal.db:
                                journal.db.execute(
                                    "update captures set state='capturing' where task_id=? and state='failed_deferred'",
                                    (task["task_id"],),
                                )
                        else:
                            continue
                if (
                    args.model == "baidu_ai"
                    and getattr(args, "optional_baidu", False)
                    and not isinstance(exc, PipelinePaused)
                ):
                    record = {
                        "model": args.model,
                        "question": question,
                        "round": round_number,
                        "task_id": task["task_id"],
                        "batch": batch,
                        "availability": "supplement_unavailable",
                        "body": "",
                        "sources": [],
                        "body_capture_complete": False,
                        "source_capture_complete": False,
                        "error": str(exc),
                        "captured_at": datetime.now(BEIJING).isoformat(
                            timespec="seconds"
                        ),
                    }
                    journal.complete(task["task_id"], record)
                    journal.export(output)
                    saved += 1
                    if pipeline:
                        event(
                            pipeline,
                            "capture_warning",
                            "百度补充数据未取得，保留错误并继续；不冒充无卡片或完整正文",
                            question=question,
                            error_type=type(exc).__name__,
                        )
                    if getattr(args, "max_new_captures", None) and saved >= args.max_new_captures:
                        return 0
                    continue
                from web_collectors.collector import PreSubmissionPageError
                if (
                    (isinstance(exc, (LoginRequiredError, PipelinePaused, PreSubmissionPageError)) or unattended)
                    and args.model == "deepseek"
                    and getattr(collector, "submission_started", True) is False
                ):
                    journal.unsubmitted(task["task_id"])
                else:
                    journal.fail(task["task_id"], exc, result)
                if pipeline:
                    event(
                        pipeline,
                        "capture_error",
                        "本题暂停，未自动重发",
                        model=args.model,
                        question=question,
                        error_type=type(exc).__name__,
                    )
                raise
            signature = _answer_signature(result)
            duplicate_of = (
                seen_cards.get(signature, "")
                if args.model == "baidu_ai" and result.get("availability") != "no_card"
                else ""
            )
            run_id = f"{args.model}:{question}:{round_number}"
            seen_cards.setdefault(signature, run_id)
            record = {
                **result,
                "model": args.model,
                "question": question,
                "round": round_number,
                "task_id": task["task_id"],
                "batch": batch,
                "captured_at": datetime.now(BEIJING).isoformat(timespec="seconds"),
                "duplicate_of": duplicate_of,
            }
            journal.complete(task["task_id"], record)
            journal.export(output)
            if recovery:
                recovery.success()
                try:
                    collector.reset_after_round()
                except Exception:
                    # The result is already durable: never repeat it for a tab error.
                    try:
                        collector.close()
                    finally:
                        collector = None
            saved += 1
            if pipeline:
                event(
                    pipeline,
                    "capture",
                    "本题采集完成",
                    model=args.model,
                    question=question,
                    ordinal=task["ordinal"] + 1,
                    total=len(questions),
                    sources=result["source_count"],
                    availability=result.get("availability", "present"),
                )
            print(
                json.dumps(
                    {
                        "model": args.model,
                        "round": round_number,
                        "source_count": result["source_count"],
                        "duplicate": bool(duplicate_of),
                    },
                    ensure_ascii=False,
                )
            )
            if getattr(args, "max_new_captures", None) and saved >= args.max_new_captures:
                return 0
        print(json.dumps({"saved": saved, "output": str(output)}, ensure_ascii=False))
        unfinished = journal.db.execute(
            "select count(*) from captures where batch=? and state!='completed'",
            (batch,),
        ).fetchone()[0]
        return 2 if unfinished else 0
    except CaptureDrainRequested:
        report_capture_phase('paused_before_submission')
        return 0
    except LoginRequiredError:
        from .search_recovery import unattended_enabled
        if unattended_enabled(root):
            report_capture_phase('waiting_login')
            return 77
        if pipeline:
            pause(
                pipeline,
                "login_required",
                "DeepSeek 登录失效；登录后点击重新检测环境，再点击继续任务",
            )
        raise
    finally:
        if collector is not None:
            collector.close()


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
