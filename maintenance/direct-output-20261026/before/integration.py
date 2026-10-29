"""Adapter for existing research/writer/review tickets and approved downloads.

V2 does not manufacture legacy claim certificates. Old tasks keep their original
validators; V2 deliveries carry a separately versioned, hash-bound review.
"""
import json
import shutil
import time
from pathlib import Path

from ..runtime import atomic_json, atomic_write
from ..staged_editorial import read
from . import VERSION
from .common import cache_root, digest, enabled, text_hash
from . import full_writer, material_manager, quality_reviewer, structure_parser, targeted_repair

WRITER_INPUTS = ["rewrite_context.json", "writing_job.json", "writing_prompt.md",
                 "knowledge.json", "product.json", "category.json"]
WRITER_OUTPUTS = ["draft.md", "article.docx", "claim_map.json", "knowledge_to_sections.json",
                  "writer_done.json", "rewrite_material.json"]


def classify(articles, limit, include_review=False):
    """Preserve the UI's genre pools without the old neutral-fact filter.

    The human-confirmed semantic parser is authoritative; these local labels
    only allocate task quotas. Source quality is reviewed against full text.
    """
    from ..genre_pools import RANK
    from ..reference_design import product_blocks
    import re
    groups = {}
    assignments = []
    for source in articles:
        article = source['article']
        title = article.get('title') or source.get('title', '')
        ranking = bool(RANK.search(title)) or len(product_blocks(article)) >= 2
        label = '测评类' if include_review and re.search('横评|测评|评测', title) else '排行类' if ranking else '科普类'
        groups.setdefault(label, []).append(source)
        assignments.append({'url': source['url'], 'title': title, 'genre': label, 'status': 'ready',
                            'reason': '体裁初分；语义骨架按任务审核策略复核'})
    categories = [{'label': label, 'description': '按确认的原文语义顺序完整仿写，保留产品资料及其归属',
                   'sources': [{'url': s['url'], 'quote': s['article']['text'][:180], 'duplicate_of': '', 'eligible': True} for s in members],
                   'writing_angles': [(s['article'].get('title') or s.get('title') or '参考文章') for s in members[:limit]]}
                  for label, members in groups.items()]
    return {'version': 'three-genre-v1' if include_review else 'two-genre-v1', 'workflow': VERSION,
            'categories': categories, 'assignments': assignments}


def prepare_research(location, observations, product):
    inputs = {"observations": observations, "product": product}
    first = next(s for row in observations for s in row["sources"] if s.get("article", {}).get("status") == "fetched")
    inputs["reference_design"] = {"primary_url": first["url"], "workflow": VERSION}
    atomic_json(location / "research_input.json", inputs)
    atomic_json(location / "stage_job.json", {"job_id": digest(inputs)[:24], "workflow": VERSION})
    atomic_write(location / "research_task.txt", "分析原文语义骨架；按任务策略完成骨架复核后生成全文。\n")


def execute(client, root, job, run):
    stage, meta = job["stage"], job["meta"]
    cache = cache_root(root)
    if stage == "research":
        data = read(run / "research_input.json")
        url = data["reference_design"]["primary_url"]
        source = next(s for row in data["observations"] for s in row["sources"] if s["url"] == url)
        article = source["article"]
        reference = {"url": url, "title": article.get("title") or source.get("title", ""), "text": article["text"]}
        skeleton = structure_parser.parse(client, reference["text"], cache, run / "skeleton-call", meta)
        policy = read(root / 'rewrite_policy.json')
        if policy.get('skeleton_review') == 'automatic':
            skeleton = structure_parser.review_automatically(client, skeleton, cache,
                run / 'skeleton-review-call', meta, policy.get('authorization'))
        return {"workflow": VERSION, "reference": reference, "product": data["product"], "skeleton": skeleton}
    context = read(run / "rewrite_context.json")
    structure_parser.checked(context["skeleton"], context["reference"]["text"], approved=True)
    if context["product"] != read(run / "product.json") or context["category"] != read(run / "category.json"):
        raise ValueError("V2 context and immutable task inputs differ")
    if stage == "writer":
        if meta.get('repair_mode') == 'exact-span-v1':
            return targeted_repair.generate(client, context, read(run / 'rewrite_material.json'), run / 'repair-call', meta,
                (run / 'draft.md').read_text('utf8'), read(run / 'rewrite_feedback.json'))
        material = material_manager.process(client, context["product"], cache, run / "material-call", meta)
        return full_writer.generate(client, context, material, run / "call", meta,
                                    previous=(run / "draft.md").read_text("utf8") if (run / "draft.md").exists() else None,
                                    feedback=read(run / "rewrite_feedback.json") if (run / "rewrite_feedback.json").exists() else None,
                                    policy=read(root / 'rewrite_policy.json').get('review_policy'))
    if stage == "review":
        if meta.get('review_projection_from'):
            source = (root / meta['review_projection_from']).resolve()
            if root.resolve() not in source.parents or not source.is_file():
                raise ValueError('Invalid preserved review path')
            return quality_reviewer.reproject(read(source), context, read(run / 'rewrite_material.json'),
                (run / 'draft.md').read_text('utf8'), run / 'review-calls')
        return quality_reviewer.review(client, context, read(run / "rewrite_material.json"),
                                       (run / "draft.md").read_text("utf8"), run / "review-calls", meta,
                                       policy=read(root / 'rewrite_policy.json').get('review_policy'))
    raise ValueError("Unsupported V2 stage")


def materialize(job, run, answer):
    if job["stage"] == "research":
        structure_parser.checked(answer["skeleton"], answer["reference"]["text"])
        atomic_json(run / "research_result.json", answer)
    elif job["stage"] == "review":
        atomic_json(run / "result.json", answer)
    else:
        from ..word_export import export_docx
        draft = answer["draft_markdown"]
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError("Missing V2 complete draft")
        atomic_write(run / "draft.md", draft)
        export_docx(draft, run / "article.docx")
        atomic_json(run / "rewrite_material.json", answer["material"])
        # Compatibility containers only, explicitly NOT per-sentence evidence.
        atomic_json(run / "claim_map.json", {"workflow": VERSION, "claims": [], "source": "rewrite_material.json"})
        atomic_json(run / "knowledge_to_sections.json", {"workflow": VERSION, "sections": [], "source": "rewrite_context.json"})
        writing = read(run / "writing_job.json")
        atomic_json(run / "writer_done.json", {
            "workflow": VERSION, "job_id": writing["job_id"], "prompt_sha256": writing["prompt_sha256"],
            "status": "completed", "draft_file": "draft.md", "word_file": "article.docx",
            "context_sha256": digest(read(run / "rewrite_context.json")), "draft_sha256": text_hash(draft),
            "material_sha256": answer["material"]["sha256"]})


def publish_writer(root, research, context, meta):
    from ..daily_editorial import publish_ticket
    writer = research.parent / "writer"
    category = read(research.parent / "category.json")
    context = {**context, "category": category}
    structure_parser.checked(context["skeleton"], context["reference"]["text"], approved=True)
    prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
    atomic_json(writer / "rewrite_context.json", context)
    atomic_json(writer / "knowledge.json", {"workflow": VERSION, "reference_design": {
        "primary_url": context["reference"]["url"], "primary_title": context["reference"]["title"]},
        "skeleton": context["skeleton"]["skeleton"]})
    atomic_json(writer / "product.json", context["product"])
    atomic_json(writer / "category.json", category)
    atomic_write(writer / "writing_prompt.md", prompt)
    atomic_json(writer / "writing_job.json", {"job_id": digest(context)[:24], "prompt_sha256": text_hash(prompt), "workflow": VERSION})
    return publish_ticket(root, "writer", writer, WRITER_INPUTS, WRITER_OUTPUTS, meta)


def approved_context(root, result):
    cached = cache_root(root) / "skeleton" / (result["skeleton"]["cache_key"] + ".json")
    value = read(cached)
    structure_parser.checked(value, result["reference"]["text"], approved=True)
    return {**result, "skeleton": value}


def receive(root, job, location):
    from ..daily_editorial import publish_ticket
    ticket = root / "queue" / job["id"] / "ticket.json"
    if job["stage"] == "research":
        result = read(location / "research_result.json")
        # Distinguish pending human review from corrupt cache/schema failures.
        value = read(cache_root(root) / "skeleton" / (result["skeleton"]["cache_key"] + ".json"))
        structure_parser.checked(value, result["reference"]["text"])
        if not value.get("approval"):
            atomic_json(ticket, {**job, "state": "needs_attention", "waiting_skeleton": value["cache_key"],
                                 "error": "新范文语义骨架待人工确认；确认后复用缓存继续，不重新解析。"})
            return
        publish_writer(root, location, approved_context(root, result), job["meta"])
    elif job["stage"] == "writer":
        verify_writer(location)
        review = location.parent / "review"
        for name in ("rewrite_context.json", "rewrite_material.json", "draft.md", "product.json", "category.json"):
            review.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(location / name, review / name)
        publish_ticket(root, "review", review,
                       ["rewrite_context.json", "rewrite_material.json", "draft.md", "product.json", "category.json"],
                       ["result.json"], {k:v for k,v in job["meta"].items() if k not in {'review_projection_from', 'review_output_retry'}})
    else:
        result = read(location / "result.json")
        if result.get("pass") is not True:
            raise ValueError("V2全文审核未通过：" + str(result.get("revise_instruction", "缺少有效审核")))
        finalize(root, location)
    atomic_json(ticket, {**job, "state": "accepted", "accepted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})


def sync_approvals(root):
    """Called under the coordinator lock, never assumes resume means approval."""
    for path in sorted((root / "queue").glob("*/ticket.json")):
        job = read(path)
        if not enabled(job) or job.get("state") != "needs_attention" or not job.get("waiting_skeleton"):
            continue
        location = root / job["location"]
        result = read(location / "research_result.json")
        value = read(cache_root(root) / "skeleton" / (job["waiting_skeleton"] + ".json"))
        structure_parser.checked(value, result["reference"]["text"])
        if not value.get("approval"):
            continue
        publish_writer(root, location, approved_context(root, result), job["meta"])
        atomic_json(path, {**{k: v for k, v in job.items() if k not in {"error", "waiting_skeleton"}},
                           "state": "accepted", "accepted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})


def verify_writer(writer):
    from ..writer_handoff import verify_delivery
    marker = verify_delivery(writer)
    context = read(writer / "rewrite_context.json")
    material = read(writer / "rewrite_material.json")
    structure_parser.checked(context["skeleton"], context["reference"]["text"], approved=True)
    material_manager.verify(material)
    if (not marker or marker.get("workflow") != VERSION or marker.get("context_sha256") != digest(context)
            or marker.get("draft_sha256") != text_hash((writer / "draft.md").read_text("utf8"))
            or marker.get("material_sha256") != material["sha256"] or material["raw_product"] != context["product"]):
        raise ValueError("V2 delivery differs from its immutable inputs")
    return marker


def finalize(root, review):
    from ..daily_editorial import file_hash, safe_name
    writer = review.parent / "writer"
    verify_writer(writer)
    context = read(writer / "rewrite_context.json")
    material = read(writer / "rewrite_material.json")
    result = read(review / "result.json")
    quality_reviewer.verify_final(result, context, material, (writer / "draft.md").read_text("utf8"))
    if any(read(p).get("word_sha256") == file_hash(writer / "article.docx") for p in (root / "revocations").glob("*.json")):
        raise ValueError("Withdrawn Word cannot be republished unchanged")
    day = next(p for p in review.parents if (p / "day.json").exists()).name
    category = context["category"]
    destination = root / "approved" / day / safe_name(category["label"]) / f"{category['number']:02d}"
    destination.mkdir(parents=True, exist_ok=True)
    # Receipt is the publication fence and is written last.
    for name in (*WRITER_OUTPUTS, "rewrite_context.json", "category.json"):
        shutil.copyfile(writer / name, destination / name)
    atomic_json(destination / "semantic_review.json", result)
    atomic_json(destination / "provenance.json", {"workflow": VERSION, "primary_reference": {
        "primary_url": context["reference"]["url"], "primary_title": context["reference"]["title"]},
        "source_sha256": text_hash(context["reference"]["text"]), "product_sha256": digest(context["product"]),
        "skeleton_approval": context["skeleton"]["approval"]})
    files = {p.name: file_hash(p) for p in destination.iterdir() if p.is_file() and p.name != "receipt.json"}
    atomic_json(destination / "receipt.json", {"workflow": VERSION, "status": "accepted_for_user_review",
        "date": day, "category": category["label"], "number": category["number"],
        "word_sha256": files["article.docx"], "files": files, "publication_approved": False,
        "quality_status": "reviewed", "logic_status": "passed"})


def handle_failure(root, job, reason):
    """One content rewrite, only after a complete, valid rejected review."""
    from ..daily_editorial import publish_ticket
    ticket = root / "queue" / job["id"]
    receipt = read(ticket / "receipt.json")
    policy = read(root / 'rewrite_policy.json')
    if (job['stage'] == 'review' and policy.get('review_policy') == quality_reviewer.REVIEW_POLICY
            and receipt.get('state') == 'failed' and receipt.get('error_code') == 'output_incomplete'
            and not job['meta'].get('review_output_retry')):
        replacement = publish_ticket(root, 'review', root / job['location'], list(job['inputs']), job['outputs'],
            {**{k:v for k,v in job['meta'].items() if k != 'review_projection_from'},
             'review_output_retry':1, 'revision':int(job['meta'].get('revision',0))+1, 'replaces':job['id']})
        atomic_json(ticket / 'ticket.json', {**job, 'state':'revision_requested', 'error':reason, 'replaced_by':replacement})
        return
    result = read(root / job["location"] / "result.json") if job["stage"] == "review" and receipt.get("state") == "completed" else None
    valid_rejection = False
    if result is not None:
        from .common import verify
        verify(result)
        quality_reviewer.validate(result["style_check"])
        if result["compliance_check"] is not None:
            quality_reviewer.validate(result["compliance_check"])
        writer = (root / job["location"]).parent / "writer"
        valid_rejection = (result.get("pass") is False and bool(result.get("revise_instruction"))
            and (result["style_check"]["pass"] is False or result["compliance_check"] is not None and result["compliance_check"]["pass"] is False)
            and result["draft_sha256"] == text_hash((writer / "draft.md").read_text("utf8"))
            and result["context_sha256"] == digest(read(writer / "rewrite_context.json"))
            and result["material_sha256"] == read(writer / "rewrite_material.json")["sha256"])
    meta = job["meta"]
    if valid_rejection and result.get('review_protocol') == quality_reviewer.REVIEW_POLICY:
        count = meta.get('targeted_repair_round', 0)
        limit = min(2, max(0, int(policy.get('max_targeted_repairs', 0))))
        if count < limit:
            archive = writer.parent / 'versions' / job['id']
            archive.mkdir(parents=True, exist_ok=True)
            for name in (*WRITER_INPUTS, *WRITER_OUTPUTS):
                shutil.copyfile(writer / name, archive / name)
            atomic_json(archive / 'review.json', result)
            atomic_json(writer / 'rewrite_feedback.json', result)
            replacement = publish_ticket(root, 'writer', writer,
                [*WRITER_INPUTS, 'draft.md', 'rewrite_material.json', 'rewrite_feedback.json'], WRITER_OUTPUTS,
                {**{k:v for k,v in meta.items() if k not in {'review_projection_from','review_output_retry'}},
                 'repair_mode': 'exact-span-v1', 'targeted_repair_round': count + 1,
                 'revision': int(meta.get('revision', 0)) + 1, 'replaces': job['id']})
            atomic_json(ticket / 'ticket.json', {**job, 'state': 'revision_requested', 'error': reason, 'replaced_by': replacement})
        else:
            atomic_json(ticket / 'ticket.json', {**job, 'state': 'needs_attention', 'error': reason})
            atomic_json(ticket / 'auto_repair_blocked.json', {'status': 'TARGETED_REPAIR_LIMIT',
                'max_targeted_repairs': limit, 'reason': '事实定点修复后仍有问题；保留文章和完整诊断'})
        return
    if valid_rejection and meta.get("rewrite_round", 0) == 0:
        archive = writer.parent / "versions" / job["id"]
        archive.mkdir(parents=True, exist_ok=True)
        for name in (*WRITER_INPUTS, *WRITER_OUTPUTS):
            shutil.copyfile(writer / name, archive / name)
        atomic_json(archive / "review.json", result)
        atomic_json(writer / "rewrite_feedback.json", result)
        replacement = publish_ticket(root, "writer", writer,
            [*WRITER_INPUTS, "draft.md", "rewrite_feedback.json"], WRITER_OUTPUTS,
            {**meta, "rewrite_round": 1, "revision": 1, "replaces": job["id"]})
        atomic_json(ticket / "ticket.json", {**job, "state": "revision_requested", "error": reason, "replaced_by": replacement})
    else:
        atomic_json(ticket / "ticket.json", {**job, "state": "needs_attention", "error": reason})
        atomic_json(ticket / "auto_repair_blocked.json", {"status": "REWRITE_V2_STOPPED", "max_rewrites": 1,
                                                        "reason": "一次全文重写后仍未通过" if valid_rejection else reason})
