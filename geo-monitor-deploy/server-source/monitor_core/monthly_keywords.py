"""Versioned monthly GEO question lists and statistics from ingested runs."""
import json
import re
import unicodedata
from datetime import date, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from . import database
from .analytics import _product_fields, recommendation_body
from .owned_products import OWN_PRODUCT_RULES, own_product_mentions


ZONE = ZoneInfo("Asia/Shanghai")
PRODUCTS = tuple(rule["name"] for rule in OWN_PRODUCT_RULES)
MODELS = {"deepseek": "DeepSeek", "doubao": "豆包", "yuanbao": "元宝", "wenxin": "百度 / 文心"}
EDITORS = {"geo_admin", "superadmin"}
FIRST = re.compile(r"^\s*[*#\s]*(?:首推|首选|第一名|第\s*1\s*名|TOP\s*1\b)[：:\s·、.\-]", re.I)
DDL = """CREATE TABLE IF NOT EXISTS geo_monthly_keywords (
    product text NOT NULL, month date NOT NULL, revision integer NOT NULL DEFAULT 0,
    terms jsonb NOT NULL DEFAULT '[]'::jsonb, PRIMARY KEY(product, month)
)"""


class Conflict(ValueError):
    pass


def today_month():
    return datetime.now(ZONE).strftime("%Y-%m")


def scope(product, month):
    if product not in PRODUCTS or not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", month):
        raise ValueError("请选择有效产品和月份")
    start = date.fromisoformat(month + "-01")
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start, end


def question_key(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def read_config(conn, product, start, *, lock=False):
    row = conn.execute(
        "SELECT revision,terms FROM geo_monthly_keywords WHERE product=%s AND month=%s"
        + (" FOR UPDATE" if lock else ""), (product, start),
    ).fetchone()
    return (row["revision"], row["terms"]) if row else (0, [])


def save(payload):
    product, month = str(payload.get("product", "")), str(payload.get("month", ""))
    start, _ = scope(product, month)
    if month < today_month():
        raise ValueError("历史月份仅供查看")
    action, term_id = payload.get("action"), payload.get("id")
    if action not in ("save", "pause", "resume"):
        raise ValueError("无效操作")
    with database.connection() as conn:
        conn.execute(DDL)
        conn.execute("INSERT INTO geo_monthly_keywords(product,month) VALUES(%s,%s) ON CONFLICT DO NOTHING", (product, start))
        revision, terms = read_config(conn, product, start, lock=True)
        if type(payload.get("revision")) is not int or payload["revision"] != revision:
            raise Conflict("词表已被更新，请重新加载后编辑")
        term = next((item for item in terms if item["id"] == term_id), None)
        if term_id and term is None or action != "save" and term is None:
            raise ValueError("二级词不存在")
        now = max(datetime.now(ZONE), datetime.combine(start, time(), ZONE)).timestamp()
        if action == "save":
            name = str(payload.get("name") or "").strip()
            supplied = payload.get("questions")
            if not 1 <= len(name) <= 40 or not isinstance(supplied, list) or not 1 <= len(supplied) <= 30:
                raise ValueError("请填写二级词名称及 1–30 条问句")
            if any(not isinstance(q, str) or not 1 <= len(q.strip()) <= 300 for q in supplied):
                raise ValueError("每条问句须为 1–300 字符")
            questions = list({question_key(q): q.strip() for q in supplied}.values())
            keys = {question_key(q) for q in questions}
            for other in terms:
                if other is term:
                    continue
                if question_key(other["name"]) == question_key(name):
                    raise ValueError("本月已有同名二级词")
                if keys.intersection(question_key(q) for version in other["versions"] for q in version["questions"]):
                    raise ValueError("同一产品当月的问句只能归入一个二级词")
            if term is None:
                if len(terms) >= 60:
                    raise ValueError("每个产品每月最多配置 60 个二级词")
                term = {"id": uuid4().hex, "name": name, "active": True, "versions": []}
                terms.append(term)
                # An initial list can classify exact prompts already received this month.
                now = datetime.combine(start, time(), ZONE).timestamp()
            term["name"] = name
            versions = term["versions"]
            if not versions or keys != {question_key(q) for q in versions[-1]["questions"]}:
                if len(versions) >= 30:
                    raise ValueError("该二级词本月已达到 30 个问句版本")
                if versions and term["active"]:
                    versions[-1]["windows"][-1][1] = now
                versions.append({"number": len(versions) + 1, "questions": questions,
                                 "windows": [[now, None]] if term["active"] else []})
        elif action == "pause" and term["active"]:
            term["versions"][-1]["windows"][-1][1] = now
            term["active"] = False
        elif action == "resume" and not term["active"]:
            term["versions"][-1]["windows"].append([now, None])
            term["active"] = True
        conn.execute("UPDATE geo_monthly_keywords SET terms=%s::jsonb,revision=revision+1 WHERE product=%s AND month=%s",
                     (json.dumps(terms, ensure_ascii=False), product, start))
    return {"ok": True, "revision": revision + 1, "term": term}


def samples(conn, start, end, model, questions):
    return conn.execute("""
        WITH originals AS MATERIALIZED (
            SELECT DISTINCT ON (e.run_id) e.run_id,e.received_at,
                   COALESCE(e.record->>'wire_question',e.record->>'prompt',e.record->>'question') AS prompt
            FROM monitor_ingest_events e
            WHERE e.model_id=%s AND e.run_id<>''
            ORDER BY e.run_id,e.received_at,e.request_id
        )
        SELECT r.run_id,r.day,r.answer,r.payload->>'product_review_status' AS review,
               e.prompt,
               extract(epoch FROM e.received_at) AS observed,
               (SELECT jsonb_agg(p.payload) FROM monitor_products p
                WHERE p.model_id=r.model_id AND p.run_id=r.run_id) AS products
        FROM originals e JOIN monitor_runs r ON r.run_id=e.run_id
        WHERE r.model_id=%s AND r.day >= %s AND r.day < %s
          AND r.status='success' AND r.answer <> ''
          AND r.payload->>'body_capture_complete' IS DISTINCT FROM 'false'
          AND btrim(regexp_replace(normalize(e.prompt, NFKC), '[[:space:]]+', ' ', 'g')) = ANY(%s)
    """, (model, model, start, end, sorted(questions)))


def measure(version, runs, product):
    result = dict(valid=0, pending=0, mention=0, recommend=0, first=0, evidence=[])
    for question in version["questions"]:
        for row in runs.get(question_key(question), ()):
            observed = row["observed"]
            if observed is None or not any(start <= observed and (end is None or observed < end)
                                          for start, end in version["windows"]):
                continue
            if row["review"] not in ("ai_verified", "verified_no_products"):
                result["pending"] += 1
                continue
            result["valid"] += 1
            body = recommendation_body(row["answer"])
            mentioned = product in own_product_mentions(body)
            result["mention"] += int(mentioned)
            if not mentioned:
                continue
            for item in row["products"] or ():
                brand, name, _ = _product_fields(item)
                evidence = str(item.get("evidence") or "").strip()
                if product not in own_product_mentions(f"{brand} {name}") or not evidence or evidence not in body:
                    continue
                result["recommend"] += 1
                result["first"] += int(any(FIRST.search(line) and evidence in line for line in body.splitlines()))
                if len(result["evidence"]) < 8:
                    result["evidence"].append({"day": str(row["day"]), "question": row["prompt"], "text": evidence})
                break
    return result


def board(product, month, model):
    start, end = scope(product, month)
    if model not in MODELS:
        raise ValueError("请选择有效模型")
    previous = date(start.year - (start.month == 1), (start.month - 2) % 12 + 1, 1)
    with database.connection() as conn:
        conn.execute(DDL)
        revision, terms = read_config(conn, product, start)
        _, last_terms = read_config(conn, product, previous)
        runs, previous_runs = {}, {}
        if terms:
            questions = {question_key(question) for term in terms + last_terms
                         for version in term["versions"] for question in version["questions"]}
            for row in samples(conn, previous, end, model, questions):
                if row["prompt"]:
                    group = runs if row["day"] >= start else previous_runs
                    group.setdefault(question_key(row["prompt"]), []).append(row)
    for term in terms:
        for version in term["versions"]:
            version["stats"] = measure(version, runs, product)
        current = term["versions"][-1]
        old = next((item["versions"][-1] for item in last_terms
                    if question_key(item["name"]) == question_key(term["name"])), None)
        term["comparison"] = "new"
        if old:
            if {question_key(q) for q in old["questions"]} != {question_key(q) for q in current["questions"]}:
                term["comparison"] = "changed"
            else:
                term["comparison"] = "same"
                term["previous_stats"] = measure(old, previous_runs, product)
    current_names = {question_key(term["name"]) for term in terms}
    previous_only = [term["name"] for term in last_terms if question_key(term["name"]) not in current_names]
    return {"product": product, "products": PRODUCTS, "models": MODELS,
            "revision": revision, "terms": terms, "previous_only": previous_only,
            "previous_month": previous.strftime("%Y-%m")}
