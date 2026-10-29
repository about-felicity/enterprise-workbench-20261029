"""Extractive input projection: preserve literal evidence; do not invent summaries."""

import copy
import hashlib
import json
import re

VERSION = "extractive-v13-daily-source-contract"


def excerpts(text, *, limit=1600, query=""):
    text = str(text)
    if len(text) <= limit:
        return text
    # Sentence/chunk boundaries retain original punctuation for evidence checking.
    chunk_limit = min(240, max(40, limit // 3))
    chunks = re.findall(r"[^\n。！？]{1," + str(chunk_limit) + r"}[\n。！？]?", text)
    terms = set(re.findall(r"[\u4e00-\u9fff]{2}|[a-zA-Z]{3,}", query.lower()))
    scored = []
    seen = set()
    for i, chunk in enumerate(chunks):
        compact = re.sub(r"\s+", "", chunk)
        if len(compact) < 12 or compact in seen:
            continue
        seen.add(compact)
        score = sum(term in chunk.lower() for term in terms) + (2 if i < 4 else 0)
        # Keep concrete comparisons and paragraphs that explain conditions.
        score += sum(
            term in chunk
            for term in ("适合", "选择", "相比", "如果", "但是", "规格", "体验", "注意")
        )
        score += sum(
            term in chunk
            for term in ("规格", "容量", "香型", "价格", "包装", "渠道", "洗感", "预算")
        )
        scored.append((score, i, chunk))
    selected, size = [], 0
    for _, i, chunk in sorted(scored, key=lambda x: (-x[0], x[1])):
        if size + len(chunk) > limit:
            continue
        selected.append((i, chunk))
        size += len(chunk)
    return "\n[…]\n".join(chunk for _, chunk in sorted(selected))


def compact_input(stage, data):
    result = copy.deepcopy(data)
    if stage == "taxonomy":
        articles = result["articles"]
        result["questions"] = list(
            dict.fromkeys(s.get("question", "") for s in articles if s.get("question"))
        )
        per_source_limit = min(850, max(120, 24000 // max(1, len(articles))))
        # Every source remains visible; exceed the budget by source count -> pause,
        # never silently drop a source from taxonomy coverage.
        for source in articles:
            article = source.get("article", {})
            source["article"] = {
                "title": article.get("title", source.get("title", ""))[:80],
                "text": excerpts(
                    article.get("text", ""),
                    limit=per_source_limit,
                    query=source.get("question", ""),
                ),
            }
            for key in list(source):
                if key not in {
                    "url",
                    "media_registry_name",
                    "article",
                }:
                    del source[key]
    elif stage == "research":
        sources = {}
        questions = []
        for row in data["observations"]:
            questions.append(row.get("question", ""))
            for source in row["sources"]:
                article = source.get("article", {})
                sources[source["url"]] = {
                    "url": source["url"],
                    "title": article.get("title", source.get("title", "")),
                    "text": excerpts(
                        article.get("text", ""),
                        limit=1000,
                        query=row.get("question", ""),
                    ),
                }
        result = {
            "questions": list(dict.fromkeys(questions)),
            "sources": list(sources.values()),
            "product": data["product"],
        }
        if len(result["sources"]) > 6:
            from .editorial_analysis import cosine, tfidf_vectors

            candidates = result["sources"]
            vectors = tfidf_vectors([s["text"] for s in candidates])
            selected = [
                max(range(len(candidates)), key=lambda i: len(candidates[i]["text"]))
            ]
            while len(selected) < 6:
                selected.append(
                    max(
                        (i for i in range(len(candidates)) if i not in selected),
                        key=lambda i: min(
                            1 - cosine(vectors[i], vectors[j]) for j in selected
                        ),
                    )
                )
            result["sources"] = [candidates[i] for i in sorted(selected)]
            result["sampling"] = {
                "total_sources": len(candidates),
                "selected_sources": 6,
                "method": "extractive_tfidf_maximum_diversity",
                "scope": "Representative deep analysis; all original sources remain stored and classified.",
            }
    result["excerpt_policy"] = (
        "原文节选，[…]表示省略。证据只能在单个连续节选中逐字引用，不能跨省略拼接；不足则报告失败，不能编造。"
    )
    return result


def research_key(location):
    data = json.loads((location / "research_input.json").read_text("utf8"))
    return hashlib.sha256(
        (VERSION + json.dumps(data, ensure_ascii=False, sort_keys=True)).encode()
    ).hexdigest()
