"""Auditable article-to-source mappings, without another model call."""

import hashlib
import html
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def build(writer):
    writer = Path(writer)
    from .staged_editorial import research_for_writer
    research = research_for_writer(writer)
    inputs = read(research / "research_input.json")
    knowledge = read(research / "research_result.json")
    units = {unit["id"]: unit for unit in knowledge["knowledge_units"]}
    claims = read(writer / "claim_map.json")["claims"]
    sections = read(writer / "knowledge_to_sections.json")["sections"]
    used = {identity for claim in claims for identity in claim.get("evidence_ids", [])}
    used.update(identity for section in sections for identity in section.get("knowledge_ids", []))
    urls = {e["url"] for identity in used if identity in units for e in units[identity].get("evidence", [])}
    sources = {}
    for observation in inputs["observations"]:
        for source in observation.get("sources", []):
            url, article = source.get("url"), source.get("article", {})
            if url not in urls or article.get("status") != "fetched":
                continue
            text = article.get("text", "")
            sources[url] = {"url": url, "title": article.get("title") or source.get("title") or url,
                            "text": text, "text_sha256": hashlib.sha256(text.encode("utf8")).hexdigest(),
                            "knowledge_ids": sorted(k for k in used if k in units and any(e["url"] == url for e in units[k].get("evidence", [])))}
    product = read(writer / "product.json")
    return {"schema_version": 1,
            "primary_reference": {k: inputs.get("reference_design", {}).get(k) for k in ("primary_url", "primary_title", "genre")},
            "draft_sha256": hashlib.sha256((writer / "draft.md").read_bytes()).hexdigest(),
            "mapping_scope": "recorded_claims_and_outline_not_independent_fact_verification",
            "claims": claims, "sections": sections,
            "knowledge_units": [units[k] for k in sorted(used) if k in units],
            "product_facts": {f"PF{i}": fact for i, fact in enumerate(product.get("facts", []), 1) if f"PF{i}" in used},
            "sources": list(sources.values()), "missing_source_urls": sorted(urls - sources.keys())}


def overview_html(packet):
    esc = lambda value: html.escape(str(value))
    units = {unit["id"]: unit for unit in packet.get("knowledge_units", [])}
    parts = ["<h2>正文与信源对照</h2><p>本篇综合多篇信源写作，通常没有唯一仿写原文。以下来自已保存的事实映射与提纲；出处可追溯不代表来源主张已独立证实。下拉选择信源，可查看采集时保存的全文。</p>"]
    for index, claim in enumerate(packet.get("claims", []), 1):
        parts.append(f'<h3>{index}. 正文声明</h3><p>{esc(claim.get("text", ""))}</p>')
        for identity in claim.get("evidence_ids", []):
            if identity in units:
                unit = units[identity]
                parts.append(f'<p><b>{esc(identity)} · 来源信息</b>：{esc(unit.get("content", ""))}</p>')
                for evidence in unit.get("evidence", []):
                    url = evidence.get("url", "")
                    parts.append(f'<blockquote>{esc(evidence.get("quote", ""))}</blockquote>')
                    if url.startswith(("https://", "http://")):
                        parts.append(f'<p><a href="{html.escape(url, quote=True)}">打开原网页</a></p>')
            elif identity in packet.get("product_facts", {}):
                fact = packet["product_facts"][identity]
                parts.append(f'<p><b>{esc(identity)} · 产品知识库</b>：{esc(fact.get("text") or fact.get("claim") or fact.get("content") or str(fact))}</p>')
    if packet.get("missing_source_urls"):
        parts.append("<p>部分来源全文未保存，请核对原网页；不能据此认定证据完整。</p>")
    return "".join(parts)


def original_html(source):
    title = html.escape(source.get("title", "未命名信源"))
    text = html.escape(source.get("text", "未保存全文")).replace("\n", "<br>")
    url = source.get("url", "")
    link = f'<a href="{html.escape(url, quote=True)}">打开原网页</a>' if url.startswith(("http://", "https://")) else ""
    return f'<h2>{title}</h2><p>采集时保存的原文快照 · {link}</p><p>{text}</p>'
