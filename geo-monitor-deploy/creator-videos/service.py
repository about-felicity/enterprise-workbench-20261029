from collections import deque
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import logging
from math import ceil
import os
import re
import sqlite3
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

from collector import (CHINA, CheckError, canonical_link, links_from_text, platform_from_link,
                       snapshot, xhs_has_token, xhs_post_id)
from check_budget import CheckBudget


DB = Path(os.environ.get("CREATOR_VIDEO_DB", "/var/lib/geo-creator-videos/videos.sqlite"))
EMPLOYEE_MODE = os.environ.get("CREATOR_VIDEO_MODE") == "employee"
PORT = int(os.environ.get("CREATOR_VIDEO_PORT", "8812"))
CHECK_INTERVAL = timedelta(minutes=15)
UNRESOLVED_RETRY_INTERVAL = timedelta(minutes=5)
MANUAL_PRIORITY_SECONDS = 60
TRANSPORT_FAILURE_WINDOW = 90
TRANSPORT_PAUSE_SECONDS = 60
BROWSER_STALL_SECONDS = 120
BROWSER_CONTEXT_OPTIONS = {"locale": "zh-CN", "timezone_id": "Asia/Shanghai"}
LOG = logging.getLogger(__name__)
CLAIM_LOCK = threading.Lock()
CLAIMED = set()
BROWSER_PROGRESS = {}
CHECK_TIMES = deque(maxlen=256)
BROWSER_BUDGET = CheckBudget(os.environ.get("CREATOR_VIDEO_SLOT_DIR"),
                             os.environ.get("CREATOR_VIDEO_LEDGER", "creator"))
CHECK_WORKERS = len(BROWSER_BUDGET.slots)
PLATFORMS = ("douyin", "xiaohongshu")
METRICS = ("likes", "comments", "favorites", "shares")


class TransportCooldown:
    """Track distinct failures while holding CLAIM_LOCK."""

    def __init__(self):
        self.failures = {}
        self.until = 0

    def record_failure(self, work_id, at):
        if at < self.until:
            return False
        self.failures = {failed_id: seen for failed_id, seen in self.failures.items()
                         if at - seen <= TRANSPORT_FAILURE_WINDOW}
        self.failures[work_id] = at
        if len(self.failures) < 3:
            return False
        self.until = at + TRANSPORT_PAUSE_SECONDS
        self.failures.clear()
        return True

    def record_success(self):
        self.failures.clear()


TRANSPORT_COOLDOWN = TransportCooldown()
XHS_TRANSPORT_COOLDOWN = TransportCooldown()


def transport_cooldown(platform):
    return XHS_TRANSPORT_COOLDOWN if platform == "xiaohongshu" else TRANSPORT_COOLDOWN


def stored_post_id(platform, post_id):
    # The existing unique index also protects legacy Douyin IDs.
    return f"xhs:{post_id}" if platform == "xiaohongshu" and post_id else post_id


def public_post_id(post_id):
    return post_id.removeprefix("xhs:") if post_id else None


def fee_in_cents(value):
    if not isinstance(value, str):
        raise ValueError("费用必须为金额文本")
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,2})?", value):
        raise ValueError("费用须为 0 到 9,999,999.99 元，最多两位小数")
    yuan, _, fraction = value.partition(".")
    return int(yuan) * 100 + int(fraction.ljust(2, "0"))


def imported_fee(data):
    value = data.get("费用")
    if value is not None:
        try:
            return fee_in_cents(str(value))
        except ValueError:
            pass  # Preserve the original cell in work_imports for manual review.
    return None


def now():
    return datetime.now(CHINA)


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as db:
        db.executescript("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY, input_url TEXT NOT NULL UNIQUE, post_id TEXT UNIQUE,
                url TEXT, author TEXT, title TEXT, pending INTEGER NOT NULL DEFAULT 1,
                last_attempt TEXT, last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
                day TEXT NOT NULL, captured_at TEXT NOT NULL, likes INTEGER,
                comments INTEGER, favorites INTEGER, shares INTEGER, metric_labels TEXT,
                PRIMARY KEY(work_id, day)
            );
            CREATE TABLE IF NOT EXISTS work_imports (
                workbook TEXT NOT NULL, sheet TEXT NOT NULL, sheet_row INTEGER NOT NULL,
                day TEXT NOT NULL, input_url TEXT, work_id INTEGER REFERENCES works(id),
                source_data TEXT NOT NULL, PRIMARY KEY(workbook, sheet, sheet_row)
            );
            CREATE INDEX IF NOT EXISTS snapshots_by_day ON snapshots(day, work_id);
            CREATE TABLE IF NOT EXISTS availability_checks (
                work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
                day TEXT NOT NULL, checked_at TEXT NOT NULL,
                availability TEXT NOT NULL CHECK (availability IN ('available', 'unavailable', 'unknown')),
                PRIMARY KEY(work_id, day)
            );
            CREATE TABLE IF NOT EXISTS deleted_works (
                record_key TEXT PRIMARY KEY, work_id INTEGER NOT NULL,
                deleted_at TEXT NOT NULL, deleted_by TEXT NOT NULL, record_json TEXT NOT NULL
            );
        """)
        db.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(works)")}
        if "platform" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN platform TEXT NOT NULL DEFAULT 'douyin' CHECK (platform IN ('douyin', 'xiaohongshu'))")
        if "metric_labels" not in {row["name"] for row in db.execute("PRAGMA table_info(snapshots)")}:
            db.execute("""
                CREATE TABLE snapshots_v2 (
                    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
                    day TEXT NOT NULL, captured_at TEXT NOT NULL, likes INTEGER,
                    comments INTEGER, favorites INTEGER, shares INTEGER, metric_labels TEXT,
                    PRIMARY KEY(work_id, day)
                )
            """)
            db.execute("INSERT INTO snapshots_v2 SELECT *, NULL FROM snapshots")
            db.execute("DROP TABLE snapshots")
            db.execute("ALTER TABLE snapshots_v2 RENAME TO snapshots")
            db.execute("CREATE INDEX snapshots_by_day ON snapshots(day, work_id)")
        if "record_key" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN record_key TEXT")
        db.execute("UPDATE works SET record_key = lower(hex(randomblob(16))) WHERE record_key IS NULL")
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS works_record_key AFTER INSERT ON works
            WHEN NEW.record_key IS NULL BEGIN
                UPDATE works SET record_key = lower(hex(randomblob(16))) WHERE id = NEW.id;
            END
        """)
        if "availability" not in columns:
            db.execute("""
                ALTER TABLE works ADD COLUMN availability TEXT NOT NULL DEFAULT 'unchecked'
                    CHECK (availability IN ('unchecked', 'available', 'unavailable', 'unknown'))
            """)
        if "entry_day" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN entry_day TEXT")
            db.execute("""
                UPDATE works SET entry_day = coalesce(
                    (SELECT min(day) FROM work_imports WHERE work_id = works.id),
                    (SELECT min(day) FROM snapshots WHERE work_id = works.id),
                    substr(last_attempt, 1, 10)
                )
            """)
        if "creator_id" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN creator_id TEXT")
            db.execute("UPDATE works SET pending = 1 WHERE availability = 'available'")
        if "creator_uid" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN creator_uid TEXT")
        if "published_at" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN published_at TEXT")
            db.execute("UPDATE works SET pending = 1 WHERE availability = 'available'")
        if EMPLOYEE_MODE:
            if "uploader" not in columns:
                db.execute("ALTER TABLE works ADD COLUMN uploader TEXT")
            if "uploaded_at" not in columns:
                db.execute("ALTER TABLE works ADD COLUMN uploaded_at TEXT")
        elif "fee_cents" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN fee_cents INTEGER CHECK (fee_cents BETWEEN 0 AND 999999999)")
            for record in import_rows(db):
                if record["work_id"] is not None and (fee := imported_fee(record["source_data"])) is not None:
                    db.execute("UPDATE works SET fee_cents = ? WHERE id = ? AND fee_cents IS NULL",
                               (fee, record["work_id"]))
        db.execute("""
            INSERT OR IGNORE INTO availability_checks
            SELECT id, substr(last_attempt, 1, 10), last_attempt, availability FROM works
            WHERE last_attempt IS NOT NULL AND availability IN ('available', 'unavailable', 'unknown')
        """)
        if "last_check_status" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN last_check_status TEXT CHECK (last_check_status IN ('available', 'unavailable', 'unknown'))")
            db.execute("ALTER TABLE works ADD COLUMN last_confirmed_at TEXT")
            db.execute("""
                UPDATE works SET last_check_status = availability
                WHERE last_attempt IS NOT NULL AND availability <> 'unchecked'
            """)
            db.execute("""
                WITH evidence(work_id, checked_at, availability) AS (
                    SELECT work_id, checked_at, availability FROM availability_checks WHERE availability <> 'unknown'
                    UNION ALL SELECT work_id, captured_at, 'available' FROM snapshots
                    UNION ALL SELECT id, last_attempt, availability FROM works
                        WHERE last_attempt IS NOT NULL AND availability IN ('available', 'unavailable')
                ), ranked AS (
                    SELECT *, row_number() OVER (PARTITION BY work_id
                        ORDER BY checked_at DESC, (availability = 'unavailable') DESC) AS rank
                    FROM evidence
                )
                UPDATE works SET (availability, last_confirmed_at) = (
                    SELECT availability, checked_at FROM ranked WHERE work_id = works.id AND rank = 1
                ) WHERE id IN (SELECT work_id FROM ranked WHERE rank = 1)
            """)
        if "check_failures" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN check_failures INTEGER NOT NULL DEFAULT 0")
        if "next_check_at" not in columns:
            db.execute("ALTER TABLE works ADD COLUMN next_check_at INTEGER")
        db.execute("""
            UPDATE works SET next_check_at = CASE
                WHEN pending = 1 THEN :at
                ELSE coalesce(CAST(strftime('%s', last_attempt) AS INTEGER) + CASE
                    WHEN last_check_status = 'unknown' THEN :retry_interval ELSE :check_interval END, :at)
                END
            WHERE next_check_at IS NULL
        """, {"at": int(now().timestamp()), "retry_interval": int(UNRESOLVED_RETRY_INTERVAL.total_seconds()),
              "check_interval": int(CHECK_INTERVAL.total_seconds())})
        db.execute("CREATE INDEX IF NOT EXISTS works_by_check_time ON works(next_check_at, id)")
        db.commit()


def import_records(workbook, records):
    due = int(now().timestamp())
    with closing(connect()) as db, db:
        for record in records:
            link = record["url"]
            if link and canonical_link(link) != link:
                raise ValueError("导入记录含无效作品链接")
            key = (workbook, record["source"], record["row"])
            existing = db.execute("""
                SELECT input_url, work_id FROM work_imports
                WHERE workbook = ? AND sheet = ? AND sheet_row = ?
            """, key).fetchone()
            work_id = None
            if link:
                if existing and existing["input_url"] == link:
                    work_id = existing["work_id"]
                if work_id is None:
                    platform = platform_from_link(link)
                    post_id = stored_post_id(platform, xhs_post_id(link))
                    db.execute("INSERT OR IGNORE INTO works(input_url, entry_day, next_check_at, platform, post_id) VALUES (?, ?, ?, ?, ?)",
                               (link, record["day"], due, platform, post_id))
                    work_id = db.execute("SELECT id FROM works WHERE input_url = ? OR post_id = ?", (link, post_id)).fetchone()["id"]
                db.execute("""
                    UPDATE works SET entry_day = min(coalesce(entry_day, ?), ?),
                        fee_cents = coalesce(fee_cents, ?) WHERE id = ?
                """, (record["day"], record["day"], imported_fee(record["data"]), work_id))
                db.execute("UPDATE works SET pending = 1, next_check_at = min(next_check_at, ?) "
                           "WHERE id = ? AND availability = 'unchecked'", (due, work_id))
            db.execute("""
                INSERT INTO work_imports VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workbook, sheet, sheet_row) DO UPDATE SET
                    day = excluded.day, input_url = excluded.input_url,
                    work_id = excluded.work_id, source_data = excluded.source_data
            """, (*key, record["day"], link, work_id, json.dumps(record["data"], ensure_ascii=False)))


def import_rows(db):
    for row in db.execute("SELECT * FROM work_imports ORDER BY day DESC, sheet_row, workbook, sheet"):
        record = dict(row)
        record["source_data"] = json.loads(record["source_data"])
        yield record


def failure_rates(db):
    def counts(source):
        return [dict(row) for row in db.execute(f"""
            SELECT day, count(*) AS total,
                sum(availability = 'available') AS available,
                sum(availability = 'unavailable') AS unavailable,
                sum(availability IN ('unknown', 'unchecked')) AS unresolved,
                sum(availability = 'unlinked') AS unlinked
            FROM ({source}) GROUP BY day ORDER BY day DESC
        """)]

    return {
        "entry": counts("""
            SELECT entry_day AS day, availability FROM works
            UNION ALL
            SELECT day, 'unlinked' FROM work_imports WHERE work_id IS NULL
        """),
        "check": counts("SELECT day, availability FROM availability_checks"),
    }


def works(day=None):
    def snapshot_data(item):
        result = dict(item)
        result["metric_labels"] = json.loads(result["metric_labels"] or "{}")
        return result

    with CLAIM_LOCK:
        checking = CLAIMED.copy()
    with closing(connect()) as db:
        sources = {}
        for record in import_rows(db):
            sources.setdefault(record["work_id"], []).append(record)
        rows = db.execute("SELECT * FROM works ORDER BY id DESC").fetchall()
        selected = {item["work_id"]: snapshot_data(item) for item in db.execute("""
            SELECT work_id, day, captured_at, likes, comments, favorites, shares, metric_labels
            FROM snapshots WHERE day = ?
        """, (day,))} if day else {}
        return {"works": [
            {**{key: row[key] for key in row.keys() if key not in {"check_failures", "next_check_at"}},
             "post_id": public_post_id(row["post_id"]),
             "checking": row["id"] in checking, "imports": sources.get(row["id"], []),
             "day_snapshot": selected.get(row["id"]), "history": [
                snapshot_data(item) for item in db.execute("""
                    SELECT day, captured_at, likes, comments, favorites, shares, metric_labels
                    FROM snapshots WHERE work_id = ? ORDER BY day DESC LIMIT 31
                """, (row["id"],))
            ]} for row in rows
        ], "unlinked": sources.get(None, []), "failure_rates": failure_rates(db)}


def add(text, fee="", uploader=None):
    links = links_from_text(text)
    if not 1 <= len(links) <= 50:
        raise ValueError("请粘贴 1–50 条抖音或小红书作品链接，也可粘贴完整分享文案")
    with closing(connect()) as db, db:
        uploaded = now()
        day = uploaded.date().isoformat()
        due = int(uploaded.timestamp())
        fields = "uploader, uploaded_at" if EMPLOYEE_MODE else "fee_cents"
        extra = (uploader, uploaded.isoformat(timespec="microseconds")) if EMPLOYEE_MODE else (fee_in_cents(fee),)
        for link in links:
            platform = platform_from_link(link)
            post_id = stored_post_id(platform, xhs_post_id(link))
            db.execute(f"""
                INSERT OR IGNORE INTO works(input_url, entry_day, next_check_at, platform, post_id, {fields})
                VALUES (?, ?, ?, ?, ?, {','.join('?' for _ in extra)})
            """, (link, day, due, platform, post_id, *extra))
            if not EMPLOYEE_MODE and extra[0] is not None:
                db.execute("UPDATE works SET fee_cents = ? WHERE fee_cents IS NULL AND (input_url = ? OR post_id = ?)",
                           (extra[0], link, post_id))
            if post_id and xhs_has_token(link):
                db.execute("""
                    UPDATE works SET input_url = ?, url = ?, pending = 1, next_check_at = min(next_check_at, ?)
                    WHERE post_id = ? AND input_url <> ?
                """, (link, link, due, post_id, link))


def set_fee(work_id, fee):
    cents = fee_in_cents(fee)
    with closing(connect()) as db, db:
        result = db.execute("UPDATE works SET fee_cents = ? WHERE id = ?", (cents, work_id))
        if not result.rowcount:
            raise ValueError("找不到这条作品，请刷新台账后重试")


def refresh(work_id):
    due = int(now().timestamp()) - MANUAL_PRIORITY_SECONDS
    with closing(connect()) as db, db:
        db.execute("UPDATE works SET pending = 1, next_check_at = min(coalesce(next_check_at, ?), ?) WHERE id = ?",
                   (due, due, work_id))


def delete_work(work_id, record_key, actor):
    if actor != "superadmin":
        raise PermissionError("仅 superadmin 可以删除视频记录")
    if not isinstance(record_key, str) or not re.fullmatch(r"[0-9a-f]{32}", record_key):
        raise ValueError("作品版本无效，请刷新台账后重试")
    with CLAIM_LOCK, closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM works WHERE id = ? AND record_key = ?", (work_id, record_key)).fetchone()
        if not row:
            deleted = db.execute("SELECT work_id FROM deleted_works WHERE record_key = ?", (record_key,)).fetchone()
            if deleted and deleted["work_id"] == work_id:
                return
            raise ValueError("作品已变更，请刷新台账后重试")
        archive = {"work": dict(row)}
        for table in ("snapshots", "availability_checks", "work_imports"):
            archive[table] = [dict(item) for item in db.execute(f"SELECT * FROM {table} WHERE work_id = ?", (work_id,))]
        db.execute("INSERT INTO deleted_works VALUES (?, ?, ?, ?, ?)", (
            record_key, work_id, now().isoformat(timespec="seconds"), actor, json.dumps(archive, ensure_ascii=False),
        ))
        db.execute("DELETE FROM work_imports WHERE work_id = ?", (work_id,))
        db.execute("DELETE FROM works WHERE id = ? AND record_key = ?", (work_id, record_key))


def next_work(excluded=(), platforms=PLATFORMS):
    if not platforms:
        return None
    placeholders = ",".join("?" for _ in excluded)
    platform_params = ",".join("?" for _ in platforms)
    exclude = f"AND id NOT IN ({placeholders})" if excluded else ""
    with closing(connect()) as db:
        return db.execute(f"""
            SELECT * FROM works
            WHERE next_check_at <= ? AND platform IN ({platform_params}) {exclude}
            ORDER BY next_check_at, id LIMIT 1
        """, (int(now().timestamp()), *platforms, *excluded)).fetchone()


def claim_work():
    with CLAIM_LOCK:
        platforms = tuple(platform for platform in PLATFORMS
                          if time.monotonic() >= transport_cooldown(platform).until
                          and time.time() >= BROWSER_BUDGET.paused_until(platform))
        row = next_work(tuple(CLAIMED), platforms)
        if row:
            CLAIMED.add(row["id"])
        return row


def save(row, result=None, error=None, availability="unknown"):
    at = now()
    with closing(connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM works WHERE id = ? AND record_key = ?",
                             (row["id"], row["record_key"])).fetchone()
        if not current or current["input_url"] != row["input_url"]:
            return
        platform = current["platform"]
        if result:
            result = {**result, "post_id": stored_post_id(platform, result["post_id"])}
            other = db.execute("SELECT id, entry_day, url FROM works WHERE post_id = ? AND id <> ?",
                               (result["post_id"], row["id"])).fetchone()
            if other:
                days = [day for day in (row["entry_day"], other["entry_day"]) if day]
                first_day = min(days, default=None)
                if EMPLOYEE_MODE:
                    first = db.execute("""
                        SELECT uploader, uploaded_at FROM works WHERE id IN (?, ?) AND uploaded_at IS NOT NULL
                        ORDER BY uploaded_at, id LIMIT 1
                    """, (row["id"], other["id"])).fetchone()
                    db.execute("UPDATE works SET entry_day = ?, uploader = ?, uploaded_at = ? WHERE id = ?",
                               (first_day, *(first or (None, None)), other["id"]))
                else:
                    db.execute("""
                        UPDATE works SET entry_day = ?,
                            fee_cents = coalesce(fee_cents, (SELECT fee_cents FROM works WHERE id = ?))
                        WHERE id = ?
                    """, (first_day, row["id"], other["id"]))
                db.execute("UPDATE work_imports SET work_id = ? WHERE work_id = ?", (other["id"], row["id"]))
                db.execute("""
                    UPDATE works SET published_at = coalesce(published_at, (SELECT published_at FROM works WHERE id = ?))
                    WHERE id = ?
                """, (row["id"], other["id"]))
                db.execute("""
                    INSERT INTO availability_checks
                    SELECT ?, day, checked_at, availability FROM availability_checks WHERE work_id = ?
                    ON CONFLICT(work_id, day) DO UPDATE SET checked_at = excluded.checked_at,
                        availability = excluded.availability
                    WHERE (availability_checks.availability = 'unknown' AND excluded.availability <> 'unknown')
                       OR (excluded.checked_at > availability_checks.checked_at
                           AND (excluded.availability <> 'unknown' OR availability_checks.availability = 'unknown'))
                """, (other["id"], row["id"]))
                db.execute("""
                    INSERT INTO snapshots
                    SELECT ?, day, captured_at, likes, comments, favorites, shares, metric_labels
                    FROM snapshots WHERE work_id = ?
                    ON CONFLICT(work_id, day) DO UPDATE SET captured_at = excluded.captured_at,
                        likes = excluded.likes, comments = excluded.comments, favorites = excluded.favorites,
                        shares = excluded.shares, metric_labels = excluded.metric_labels
                    WHERE excluded.captured_at > snapshots.captured_at
                """, (other["id"], row["id"]))
                if platform == "xiaohongshu" and other["url"] and not xhs_has_token(result["url"]):
                    result["url"] = other["url"]
                db.execute("DELETE FROM works WHERE id = ?", (row["id"],))
                row = other
            db.execute("""
                UPDATE works SET post_id = :post_id, url = :url, author = :author, title = :title,
                    published_at = coalesce(:published_at, published_at),
                    creator_id = coalesce(:creator_id, creator_id), creator_uid = coalesce(:creator_uid, creator_uid)
                WHERE id = :id
            """, {"creator_id": None, "creator_uid": None, "published_at": None, **result, "id": row["id"]})
            availability = "available"
            missing_metrics = [label for key, label in zip(METRICS, ("点赞", "评论", "收藏", "转发"))
                               if key not in result]
            if any(key in result for key in METRICS):
                db.execute("""
                    INSERT INTO snapshots VALUES (:id, :day, :at, :likes, :comments, :favorites, :shares, :labels)
                    ON CONFLICT(work_id, day) DO UPDATE SET captured_at = excluded.captured_at,
                        likes = excluded.likes, comments = excluded.comments,
                        favorites = excluded.favorites, shares = excluded.shares, metric_labels = excluded.metric_labels
                """, {**{key: result.get(key) for key in METRICS}, "id": row["id"], "day": at.date().isoformat(),
                      "at": at.isoformat(timespec="seconds"), "labels": json.dumps(result.get("metric_labels", {}), ensure_ascii=False)})
            else:
                error = "作品可访问，平台暂未返回互动数据"
            if platform == "xiaohongshu" and 0 < len(missing_metrics) < len(METRICS):
                error = f"小红书暂未返回{'、'.join(missing_metrics)}数据"
        checked_at = at.isoformat(timespec="seconds")
        failures = 0
        if availability == "unknown":
            previous = db.execute("SELECT check_failures FROM works WHERE id = ?", (row["id"],)).fetchone()[0]
            failures = min(previous + 1, CHECK_INTERVAL // UNRESOLVED_RETRY_INTERVAL)
        interval = min(CHECK_INTERVAL, UNRESOLVED_RETRY_INTERVAL * failures) if failures else CHECK_INTERVAL
        db.execute("""
            UPDATE works SET pending = 0, last_attempt = :at, last_error = :error,
                last_check_status = :status, check_failures = :failures, next_check_at = :next_at,
                availability = CASE WHEN :status <> 'unknown' OR availability = 'unchecked'
                                    THEN :status ELSE availability END,
                last_confirmed_at = CASE WHEN :status <> 'unknown' THEN :at ELSE last_confirmed_at END
            WHERE id = :id
        """, {"at": checked_at, "error": error, "status": availability, "id": row["id"],
              "failures": failures, "next_at": int((at + interval).timestamp())})
        db.execute("""
            INSERT INTO availability_checks VALUES (?, ?, ?, ?)
            ON CONFLICT(work_id, day) DO UPDATE SET checked_at = excluded.checked_at,
                availability = excluded.availability
            WHERE excluded.availability <> 'unknown' OR availability_checks.availability = 'unknown'
        """, (row["id"], at.date().isoformat(), checked_at, availability))


def read_work(context, link, expected_post_id=None):
    page = context.new_page()
    try:
        return snapshot(page, link, expected_post_id)
    finally:
        page.close()


def route_check_request(route):
    if route.request.resource_type in {"image", "media", "font"}:
        route.abort()
    else:
        route.continue_()


@contextmanager
def check_context(browser):
    with browser.new_context(**BROWSER_CONTEXT_OPTIONS) as context:
        context.route("**/*", route_check_request)
        yield context


def check_work(row, context):
    link = row["url"] or row["input_url"]
    platform = row["platform"]
    expected_post_id = public_post_id(row["post_id"])
    try:
        return read_work(context, link, expected_post_id)
    except CheckError as first:
        page_unavailable = first.category == "page_unavailable"
        confirm_change = row["pending"] or row["availability"] != "unavailable"
        if first.category == "share_unavailable" and link == row["input_url"]:
            raise
        if first.category in {"transport", "timeout", "rate_limit"}:
            raise
        if first.availability != "unknown" and not (page_unavailable and confirm_change):
            raise
        LOG.info("Video check retry for work %s: %s", row["id"], first)
        expected_post_id = expected_post_id or first.post_id
        if expected_post_id and first.category in {"navigation", "detail", "page_unavailable", "share_unavailable"}:
            link = row["input_url"]
        time.sleep(2)
        if time.time() < BROWSER_BUDGET.paused_until(platform):
            if page_unavailable:
                raise CheckError(f"{first}，待复核", category="detail") from first
            raise
        # Use a fresh full context to confirm an unavailable page or recover incomplete details.
        with context.browser.new_context(**BROWSER_CONTEXT_OPTIONS) as retry_context:
            try:
                return read_work(retry_context, link, expected_post_id)
            except CheckError as retry:
                if confirm_change and retry.category == "page_unavailable" and not page_unavailable:
                    raise CheckError(f"{retry}，待复核", category="detail") from retry
                raise


def save_check_error(row, error):
    platform = row["platform"]
    cooldown = transport_cooldown(platform)
    if error.availability == "unknown":
        LOG.warning("Video check unresolved for work %s: %s", row["id"], error)
    if error.category == "rate_limit":
        BROWSER_BUDGET.pause(error.retry_after or TRANSPORT_PAUSE_SECONDS, platform)
    elif error.category == "transport":
        with CLAIM_LOCK:
            paused = cooldown.record_failure(row["id"], time.monotonic())
        if paused:
            LOG.warning("Pausing new video checks for %s seconds after repeated connection failures",
                        TRANSPORT_PAUSE_SECONDS)
    elif error.availability == "unavailable":
        with CLAIM_LOCK:
            cooldown.record_success()
        if row["availability"] != "unavailable":
            LOG.info("Video unavailable confirmed for work %s: %s", row["id"], error)
    save(row, error=str(error), availability=error.availability)


def mark_browser_progress(work_id):
    with CLAIM_LOCK:
        BROWSER_PROGRESS[threading.get_ident()] = (time.monotonic(), work_id)


def stalled_browser_work(at):
    with CLAIM_LOCK:
        return [work_id for started, work_id in BROWSER_PROGRESS.values()
                if at - started >= BROWSER_STALL_SECONDS]


def watch_browsers():
    while True:
        time.sleep(5)
        stalled = stalled_browser_work(time.monotonic())
        if stalled:
            LOG.error("Video browser stalled for %s; restarting collector to release its slots", stalled)
            # The work stays due in SQLite. systemd stops all Chrome children
            # and restarts this ledger, releasing its advisory browser locks.
            os._exit(1)


def collect_batch(chromium):
    row = claim_work()
    if row is None:
        return
    mark_browser_progress(row["id"])
    try:
        with chromium.launch(
            executable_path=os.environ.get("CREATOR_VIDEO_CHROME", "/usr/bin/google-chrome"),
            headless=True,
        ) as browser, check_context(browser) as context:
            for index in range(20):
                if time.time() < BROWSER_BUDGET.paused_until(row["platform"]):
                    break
                started = time.monotonic()
                try:
                    result = check_work(row, context)
                except CheckError as exc:
                    save_check_error(row, exc)
                else:
                    save(row, result=result)
                    with CLAIM_LOCK:
                        transport_cooldown(row["platform"]).record_success()
                with CLAIM_LOCK:
                    CLAIMED.discard(row["id"])
                    CHECK_TIMES.append(round(time.monotonic() - started, 2))
                row = None
                if index == 19:
                    break
                mark_browser_progress(None)
                time.sleep(3)
                row = claim_work()
                if row is None:
                    break
                mark_browser_progress(row["id"])
    finally:
        with CLAIM_LOCK:
            BROWSER_PROGRESS.pop(threading.get_ident(), None)
            if row is not None:
                CLAIMED.discard(row["id"])


def collect():
    from playwright.sync_api import sync_playwright

    while True:
        try:
            with sync_playwright() as p:
                while True:
                    with BROWSER_BUDGET.browser_slot() as slot:
                        if slot:
                            collect_batch(p.chromium)
                    time.sleep(3)
        except Exception:
            LOG.exception("Creator video collection failed")
            time.sleep(30)


def queue_health():
    at = now()
    cutoff = (at - CHECK_INTERVAL).isoformat(timespec="seconds")
    with closing(connect()) as db:
        queue = dict(db.execute("""
            SELECT count(*) AS total, count(*) FILTER (WHERE pending = 1) AS pending,
                count(*) FILTER (WHERE next_check_at <= :at) AS due,
                min(next_check_at) FILTER (WHERE pending = 0 AND next_check_at <= :at) AS oldest_due,
                count(*) FILTER (WHERE last_attempt >= :cutoff) AS checked_last_15_minutes,
                count(*) FILTER (WHERE last_check_status = 'unknown') AS unresolved
            FROM works
        """, {"at": int(at.timestamp()), "cutoff": cutoff}).fetchone())
    with CLAIM_LOCK:
        checking = len(CLAIMED)
        timings = sorted(CHECK_TIMES)
        transport_pause = max(0, ceil(TRANSPORT_COOLDOWN.until - time.monotonic()))
    oldest_due = queue.pop("oldest_due")
    return {**queue, "checking": checking,
            "oldest_regular_due_seconds": int(at.timestamp()) - oldest_due if oldest_due is not None else 0,
            "platform_pause_seconds": max(0, ceil(BROWSER_BUDGET.paused_until() - at.timestamp())),
            "transport_pause_seconds": transport_pause, "timed_checks": len(timings),
            "check_seconds_p95": timings[ceil(0.95 * len(timings)) - 1] if timings else None}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_works(self, write=False):
        url = urlsplit(self.path)
        if url.path != "/works":
            self.respond(404, {"error": "接口不存在"})
            return
        actor = self.headers.get("X-Geo-User", "")
        if EMPLOYEE_MODE and not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", actor):
            self.respond(401, {"error": "请先登录工作台"})
            return
        try:
            day = parse_qs(url.query).get("day", [None])[0]
            if day and date.fromisoformat(day).isoformat() != day:
                raise ValueError("数据日期格式不正确")
            if not write:
                self.send_works(day, actor)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                raise ValueError("分享文案过长或为空")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("请求格式不正确")
            if "delete_work_id" in data:
                if type(data["delete_work_id"]) is not int or not 0 < data["delete_work_id"] < 2**63:
                    raise ValueError("作品编号无效")
                delete_work(data["delete_work_id"], data.get("record_key"), actor)
            elif isinstance(data.get("text"), str):
                add(data["text"], data.get("fee", ""), actor if EMPLOYEE_MODE else None)
            elif not EMPLOYEE_MODE and type(data.get("fee_work_id")) is int and 0 < data["fee_work_id"] < 2**63:
                set_fee(data["fee_work_id"], data.get("fee"))
            elif type(data.get("refresh")) is int and 0 < data["refresh"] < 2**63:
                refresh(data["refresh"])
            else:
                raise ValueError("请提供分享文案或作品编号")
        except PermissionError as exc:
            self.respond(403, {"error": str(exc)})
            return
        except ValueError as exc:
            self.respond(400, {"error": str(exc)})
            return
        self.send_works(day, actor)

    def send_works(self, day, actor):
        payload = works(day)
        payload["can_delete"] = actor == "superadmin"
        if EMPLOYEE_MODE:
            payload["current_uploader"] = actor
        self.respond(200, payload)

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, queue_health())
        else:
            self.handle_works()

    def do_POST(self):
        self.handle_works(write=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize()
    if len(sys.argv) == 4 and sys.argv[1] == "--import":
        if EMPLOYEE_MODE:
            raise SystemExit("Employee videos must be submitted by a signed-in account")
        import_records(sys.argv[2], json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")))
        raise SystemExit(0)
    for index in range(CHECK_WORKERS):
        threading.Thread(target=collect, name=f"creator-check-{index + 1}", daemon=True).start()
    threading.Thread(target=watch_browsers, name="video-browser-watchdog", daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
