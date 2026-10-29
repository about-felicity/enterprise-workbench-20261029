"""Immutable batch provenance for new editorial jobs (no network/model calls)."""
import hashlib

VERSION = "daily-source-contract-v1"
POLICY = "标题痛点、正文主题与结构、竞品名单及其介绍必须依据本批次当日抓取原文；不得用往日素材或模型记忆补齐。自有产品为用户明确授权的唯一新增推荐，事实仅来自approved品牌知识库。当天指采集批次日期，不是原文发布日期；历史回放保留原批次日期。"


def fingerprint(source):
    article = source["article"]
    return hashlib.sha256((article.get("title", "") + "\n" + article["text"]).encode()).hexdigest()


def bind(blueprint, sources, date):
    from datetime import date as Date
    Date.fromisoformat(date)
    if blueprint["primary_url"] not in {s["url"] for s in sources}:
        raise ValueError("Primary source is outside daily batch")
    return {**blueprint, "source_contract": {"version": VERSION, "batch_date": date,
        "policy": POLICY, "sources": {s["url"]: fingerprint(s) for s in sources}}}


def validate(blueprint, rows):
    contract = blueprint.get("source_contract")
    if not contract:
        return  # Legacy artifacts are not silently rewritten or certified.
    sources = {s["url"]: s for row in rows for s in row["sources"]}
    actual = {url: fingerprint(s) for url, s in sources.items()}
    if actual != contract["sources"] or blueprint["primary_url"] not in actual:
        raise ValueError("Daily source contract mismatch: source added, removed or changed")
