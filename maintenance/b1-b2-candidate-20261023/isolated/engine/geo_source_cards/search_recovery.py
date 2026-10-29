"""Durable bounded recovery for read-only card searches, never chat submissions."""

import json
import time

from .pipeline_control import ensure_running
from .runtime import atomic_json


class SecurityVerificationError(RuntimeError):
    """A real verification page was observed; no challenge is solved here."""


def security_backoff_seconds(streak, retry_wait=20):
    return min(900, max(180, int(retry_wait)) * 2 ** min(max(0, streak - 1), 3))


def classified(error):
    text = str(error)
    if isinstance(error, SecurityVerificationError) or "百度安全验证" in text:
        return "verification"
    if any(
        s in text
        for s in (
            "Page.goto: Timeout",
            "Page.goto: net::ERR_NAME_NOT_RESOLVED",
            "Page.evaluate: Execution context was destroyed",
            "文心入口回答未完整",
            "文心正文滚动后未能确认完成",
            "百度 AI 卡片未完整呈现",
            "百度 AI 回答未能完全展开",
            "Source completeness is not proven",
            "Required source links are missing",
        )
    ):
        return "read_error"
    return None


class SearchRecovery:
    def __init__(self, journal, root, *, clock=time.time, optional_baidu=False):
        self.db, self.root, self.clock = journal.db, root, clock
        self.optional_baidu = optional_baidu
        self.db.executescript("""
        create table if not exists search_recovery_attempts(
          id integer primary key, task_id text not null, kind text not null,
          error text not null, previous_result text, epoch real not null);
        create table if not exists search_recovery_control(
          id integer primary key check(id=1), streak integer not null,
          cooldown_until real not null, blocked integer not null);
        insert or ignore into search_recovery_control values(1,0,0,0);
        """)

    def control(self):
        return dict(
            self.db.execute(
                "select * from search_recovery_control where id=1"
            ).fetchone()
        )

    def publish(self, **extra):
        atomic_json(
            self.root / "search_recovery.json",
            {**self.control(), **extra, "checked_epoch": self.clock()},
        )

    def failure(self, task, error, partial=None):
        kind = classified(error)
        if task["model"] not in {"baidu_ai", "wenxin_card"} or not kind:
            return None
        previous = self.control()
        if previous["blocked"]:
            raise RuntimeError("等待人工处理百度验证；不会因重启自动恢复")
        with self.db:
            live = self.db.execute(
                "select state from captures where task_id=?", (task["task_id"],)
            ).fetchone()
            if not live or live[0] not in {"capturing", "needs_attention"}:
                raise RuntimeError("Cannot recover a completed or unknown task")
            self.db.execute(
                "insert into search_recovery_attempts(task_id,kind,error,previous_result,epoch) values(?,?,?,?,?)",
                (
                    task["task_id"],
                    kind,
                    str(error),
                    json.dumps(partial, ensure_ascii=False),
                    self.clock(),
                ),
            )
            count = self.db.execute(
                "select count(*) from search_recovery_attempts where task_id=?",
                (task["task_id"],),
            ).fetchone()[0]
            optional_read = self.optional_baidu and task["model"] == "baidu_ai" and kind == "read_error"
            limit = 2 if optional_read else 5 if task["model"] == "baidu_ai" else 2
            exhausted = count >= limit * (1 if optional_read else 4)
            streak = (
                previous["streak"] + 1 if kind == "verification" else previous["streak"]
            )
            delay = security_backoff_seconds(streak) if kind == "verification" else 20
            # Persistent challenge requires operator handling, not endless probing.
            blocked = streak >= 4
            until = max(previous["cooldown_until"], self.clock() + delay)
            self.db.execute(
                "update search_recovery_control set streak=?,cooldown_until=?,blocked=? where id=1",
                (streak, until, int(blocked)),
            )
            self.db.execute(
                "update captures set state=?,error=?,result=? where task_id=?",
                (
                    "failed_deferred" if exhausted else "pending",
                    str(error),
                    json.dumps(partial, ensure_ascii=False) if partial else None,
                    task["task_id"],
                ),
            )
        result = {
            "kind": kind,
            "attempt": count,
            "cycle": (count - 1) // limit,
            "defer": count % limit == 0,
            "exhausted": exhausted,
            "status": "waiting_verification"
            if blocked
            else "failed_deferred"
            if exhausted
            else "cooling_down",
            "task_id": task["task_id"],
            "error": str(error),
            "attempt_limit": limit * (1 if optional_read else 4),
        }
        self.publish(**result)
        return result

    def wait(self, pipeline, *, sleep=time.sleep):
        while True:
            ensure_running(pipeline)
            current = self.control()
            if current["blocked"]:
                raise RuntimeError("等待人工处理百度验证；不会因重启自动恢复")
            remaining = current["cooldown_until"] - self.clock()
            if remaining <= 0:
                return
            sleep(min(5, remaining))

    def success(self):
        with self.db:
            self.db.execute(
                "update search_recovery_control set streak=0,cooldown_until=0,blocked=0 where id=1"
            )
        self.publish(status="ready")

    def evidence(self, collector, task):
        folder = self.root / "recovery_evidence" / task["task_id"] / str(time.time_ns())
        folder.mkdir(parents=True)
        try:
            page = collector.page
            snapshot = page.evaluate(
                "({url:location.href,title:document.title,pageText:document.body.innerText.slice(0,3000)})"
            )
            atomic_json(folder / "snapshot.json", snapshot)
            browser_page = getattr(page, "page", None)
            if browser_page is not None:
                browser_page.screenshot(path=str(folder / "page.png"), full_page=False)
        except Exception as error:
            atomic_json(
                folder / "capture_error.json", {"error_type": type(error).__name__}
            )
