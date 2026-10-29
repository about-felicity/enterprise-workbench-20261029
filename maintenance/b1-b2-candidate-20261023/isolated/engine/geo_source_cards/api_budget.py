"""Transactional, fail-closed spending reservations in CNY (peak list prices)."""

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from .pipeline_control import BEIJING, event, settings

# Verified from official Chinese pricing 2026-10-08. Peak prices are used even
# off peak, so reported amounts are conservative estimates, not billing claims.
PRICE_DATE = "2026-10-08"
INPUT_MISS, INPUT_HIT, OUTPUT = 2.0, 0.04, 8.0
LIMITS = {"taxonomy": 6000, "research": 4800, "writer": 8000, "review": 3500}


class BudgetExceeded(RuntimeError):
    pass

class ArticleBudgetExceeded(BudgetExceeded):
    """A known unsent request exceeds only its own article allowance."""
    pass


def usage_cost(usage):
    if not isinstance(usage, dict) or not all(
        type(usage.get(k)) is int and usage[k] >= 0
        for k in ("prompt_tokens", "completion_tokens")
    ):
        return None
    hits = usage.get("prompt_cache_hit_tokens", 0)
    if type(hits) is not int or not 0 <= hits <= usage["prompt_tokens"]:
        return None
    return (
        (usage["prompt_tokens"] - hits) * INPUT_MISS
        + hits * INPUT_HIT
        + usage["completion_tokens"] * OUTPUT
    ) / 1_000_000


def settled_price_factor(start_epoch, end_epoch):
    """Use half price only when the whole observed request stayed off peak.

    Holidays are deliberately treated as weekdays (conservative, never cheaper).
    Unknown timing or a clock reversal retains the peak estimate.
    """
    if end_epoch < start_epoch or end_epoch - start_epoch > 43200:
        return 1.0
    start, end = (datetime.fromtimestamp(t, BEIJING) for t in (start_epoch, end_epoch))
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        if day.weekday() < 5:
            for low, high in ((9, 12), (14, 18)):
                if start < day.replace(hour=high) and end >= day.replace(hour=low):
                    return 1.0
        day += timedelta(days=1)
    return 0.5


class Budget:
    def __init__(self, root, *, test=False):
        self.root, self.test = Path(root), test
        production = self.root.parent / "runtime-api"
        self.ledger_root = (
            production
            if test and (production / "settings.json").is_file()
            else self.root
        )
        path = self.ledger_root / "api/costs.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("pragma journal_mode=WAL")
        self.db.execute("pragma synchronous=FULL")
        self.db.execute(
            "create table if not exists costs(id text primary key,date text,batch_date text,category text,article text,stage text,test integer,state text,reserved real,charged real,usage text,created real)"
        )

    def reserve(self, payload, directory, meta, stage):
        if (
            datetime.now(BEIJING).date() - datetime.fromisoformat(PRICE_DATE).date()
        ).days > 30:
            raise BudgetExceeded("价格版本超过30天，须重新核对后恢复")
        # UTF-8 bytes plus framing is a deliberately conservative token bound.
        upper = (
            len(json.dumps(payload["messages"], ensure_ascii=False).encode("utf8"))
            + 256
        ) * INPUT_MISS / 1_000_000 + payload["max_tokens"] * OUTPUT / 1_000_000
        config = settings(self.ledger_root)
        identity = hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest()
        date = datetime.now(BEIJING).date().isoformat()
        category = meta.get("category", "")
        article = (
            "shared"
            if stage == 'taxonomy' or (stage == 'research' and meta.get('cost_scope') != 'article')
            else str(meta.get("number", 0))
        )
        self.db.execute("begin immediate")
        try:
            previous = self.db.execute(
                "select * from costs where id=?", (identity,)
            ).fetchone()
            if previous:
                if previous["state"] == "settled" and previous["charged"] == 0.0:
                    self.db.execute(
                        "update costs set id=? where id=?",
                        (identity + "-rejected-" + str(time.time_ns()), identity),
                    )
                else:
                    raise BudgetExceeded("请求已有费用预留，须核对发送状态")
            total = (
                "select coalesce(sum(coalesce(charged,reserved)),0) from costs where "
            )
            daily = self.db.execute(total + "date=?", (date,)).fetchone()[0]
            trial = self.db.execute(total + "test=1").fetchone()[0]
            # Full common cost charged conservatively against each candidate.
            per_article = self.db.execute(
                total
                + "batch_date=? and (category='' or (category=? and (article='shared' or article=?)))",
                (meta["date"], category, article),
            ).fetchone()[0]
            for used, limit, label in (
                (daily, config["daily_budget_cny"], "每日"),
                (per_article, config["article_budget_cny"], "单篇含共享分析"),
            ):
                if used + upper > limit + 1e-9:
                    raise BudgetExceeded(
                        f"{label}预算不足，预计上限 {used + upper:.4f} 元，限额 {limit:.2f} 元"
                    )
            if self.test and trial + upper > config["test_budget_cny"] + 1e-9:
                raise BudgetExceeded("开发测试总预算不足；不会自动重置")
            self.db.execute(
                "insert into costs values(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    date,
                    meta["date"],
                    category,
                    article,
                    stage,
                    int(self.test),
                    "reserved",
                    upper,
                    None,
                    None,
                    time.time(),
                ),
            )
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return identity

    def settle(self, identity, usage=None, *, rejected=False):
        cost = 0.0 if rejected else usage_cost(usage)
        request = self.db.execute(
            "select created from costs where id=?", (identity,)
        ).fetchone()
        if cost is not None and request:
            cost *= settled_price_factor(request["created"], time.time())
        with self.db:
            self.db.execute(
                "update costs set state=?,charged=?,usage=? where id=?",
                (
                    "settled" if cost is not None else "usage_unknown",
                    cost,
                    json.dumps(usage),
                    identity,
                ),
            )
        event(
            self.root,
            "cost",
            "API费用已记录" if cost is not None else "用量未知，保留全部预算预留",
            estimated_cny=cost,
            usage=usage,
            request=identity[:12],
            task=dict(
                self.db.execute(
                    "select batch_date,category,article,stage from costs where id=?",
                    (identity,),
                ).fetchone()
            ),
        )

    def summary(self):
        rows = [
            dict(row)
            for row in self.db.execute(
                "select * from costs order by created desc limit 100"
            )
        ]
        for row in rows:
            row["usage"] = json.loads(row["usage"] or "null")
        totals = self.db.execute(
            "select count(*),coalesce(sum(charged),0),coalesce(sum(case when charged is null then reserved else 0 end),0),coalesce(sum(case when test=1 then charged else 0 end),0) from costs"
        ).fetchone()
        return {
            "pricing": "CNY usage estimate; off-peak discount only for verified request intervals; reservations at peak rate",
            "price_date": PRICE_DATE,
            "calls": rows,
            "call_count": totals[0],
            "estimated_cny": round(totals[1], 6),
            "reserved_cny": round(totals[2], 6),
            "test_estimated_cny": round(totals[3], 6),
            "by_stage": [
                dict(r)
                for r in self.db.execute(
                    "select stage,count(*) calls,round(sum(coalesce(charged,reserved)),6) estimated_cny from costs group by stage"
                )
            ],
        }

    def close(self):
        self.db.close()
