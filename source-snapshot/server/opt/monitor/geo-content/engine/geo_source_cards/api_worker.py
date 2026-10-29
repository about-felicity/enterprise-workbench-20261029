"""Server-side Flash execution of the validated editorial queue."""

import argparse
import json
import secrets
import shutil
import time
from datetime import datetime
from pathlib import Path

from .api_budget import LIMITS, Budget
from .api_prompts import build_prompt, expand_references
from .daily_editorial import BEIJING, file_hash, safe_name, tick
from .deepseek_api import APIError, DeepSeekClient
from .execution_runs import authorize
from .pipeline_control import PipelinePaused, ensure_running, event, pause, state
from .prompt_compaction import research_key
from .runtime import atomic_json, atomic_write, process_lock
from .staged_editorial import read
from .word_export import export_docx


def materialize(job, location, answer):
    from .rewrite_v2.common import enabled
    if enabled(job):
        from .rewrite_v2.integration import materialize as materialize_v2
        return materialize_v2(job, location, answer)
    if job["stage"] == "research" and "units" in answer:
        # Cached answers contain compact evidence IDs. Rebuild their index from
        # this immutable run's inputs, including after RESPONDED crash recovery.
        # Building a prompt is local and does not invoke the API.
        build_prompt(job, location)
        blueprint = read(location/'research_input.json').get('reference_design', {})
        if blueprint.get('genre') in {'ranking', 'science', 'review'}:
            from .genre_outline import bind,captured_neutral_details
            before = answer
            answer = captured_neutral_details(answer, blueprint, read(location/"evidence_spans.json"))
            answer = bind(answer, blueprint)
            if answer.get('units') != before.get('units'):
                kept = {u['id']:u['kind'] for u in answer['units']}
                atomic_json(location/'research_projection.json', {
                    'reason':'Preserve evidence; unverified medical guidance remains risk and is excluded from the writing outline',
                    'removed_ids':[u['id'] for u in before['units'] if u['id'] not in kept],
                    'demoted_ids':[u['id'] for u in before['units'] if u['id'] in kept and u['kind'] != kept[u['id']]],
                    'derived_neutral_properties':[{'id':u['id'],'source_unit':u['derived_from'],'text':u['text'],'evidence':u['evidence']} for u in answer['units'] if u.get('derived_from')],
                    'original_answer_preserved':True})
    if job['stage']=='writer' and job.get('meta',{}).get('paragraph_repair'):
        from .paragraph_repair import apply
        answer=apply(location,answer)
    if job['stage']=='writer' and (location/'compilation.json').is_file() and not job.get('meta',{}).get('paragraph_repair'):
        from .article_compiler import validate_document
        validate_document(answer,read(location/'compilation.json'),complete=True)
        doc=answer['document']
        atomic_json(location/'statement_annotations.json',{'compilation_sha256':read(location/'compilation.json')['sha256'],
            'statements':[{k:p[k] for k in ('text','statement_type','claim_ids','evidence_ids')} for p in
                doc.get('introduction',[])+[p for s in doc['sections'] for p in s['paragraphs']]+doc.get('conclusion',[])]})
    if job['stage']=='writer' and 'document' in answer:
        from .consumer_prompts import document_answer
        answer=document_answer(answer,location)
    answer = expand_references(job["stage"], location, answer)
    if job['stage']=='review' and not ((location/'writer_done.json').is_file() and read(location/'writer_done.json').get('compilation')):
        from .delta_review import merge
        answer=merge(location,answer)
    if job["stage"] == "writer":
        applied_compilation=read(location/'compilation.json') if (location/'compilation.json').is_file() else (read(location/'paragraph_repair.json').get('compiled_contract') if (location/'paragraph_repair.json').is_file() else None)
        from .append_repair import MARKER, apply
        note = location/'revision_note.txt'
        if note.is_file() and MARKER in note.read_text('utf8') and ('additions' in answer or not job.get('meta',{}).get('consumer_rewrite')):
            base_path = location/'append_base.json'
            if not base_path.exists():
                atomic_json(base_path, {'draft':(location/'draft.md').read_text('utf8'),
                    'claims':read(location/'claim_map.json'), 'sections':read(location/'knowledge_to_sections.json')})
            base = read(base_path)
            answer = apply(base['draft'], base['claims'], base['sections'], answer)
        from .draft_length import fit_draft
        from .genre_length import policy

        original = answer["draft_markdown"]
        knowledge = read(location / 'knowledge.json') if (location / 'knowledge.json').exists() else {}
        # Long-form contracts reject unsuitable drafts; deleting paragraphs can
        # remove the explanation that makes a recommendation understandable.
        answer, removed = (answer, []) if policy(knowledge.get('reference_design')) else fit_draft(answer)
        if removed:
            atomic_json(
                location / "length_edit.json",
                {
                    "original_markdown": original,
                    "removed_paragraphs": removed,
                    "requires_independent_review": True,
                },
            )
        draft = answer["draft_markdown"]
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError("Missing complete draft")
        atomic_write(location / "draft.md", draft.strip() + "\n")
        atomic_json(location / "claim_map.json", answer["claim_map"])
        atomic_json(
            location / "knowledge_to_sections.json", answer["knowledge_to_sections"]
        )
        export_docx(
            (location / "draft.md").read_text("utf8"), location / "article.docx"
        )
        writing = read(location / "writing_job.json")
        atomic_json(
            location / "writer_done.json",
            {
                "job_id": writing["job_id"],
                "prompt_sha256": writing["prompt_sha256"],
                "status": "completed",
                "draft_file": "draft.md",
                "word_file": "article.docx",
                **({'document_projection':read(location/'document_projection.json')} if (location/'document_projection.json').exists() else {}),
                **({'compilation':applied_compilation} if applied_compilation else {}),
                **({'agent_workflow':{'roles':['Structure Analyzer','Article Writer','Article Reviewer'],
                    'article_structure':applied_compilation.get('article_structure'),
                    'section_generation':read(location/'section_calls/manifest.json') if (location/'section_calls/manifest.json').is_file() else None}}
                    if applied_compilation else {}),
                **({'paragraph_repair_audit':read(location/'paragraph_repair_audit.json'),
                    'paragraph_repair_spec':read(location/'paragraph_repair.json')}
                   if job.get('meta',{}).get('paragraph_repair') else {}),
            },
        )
    else:
        name = "research_result.json" if job["stage"] == "research" else "result.json"
        atomic_json(location / name, answer)


class Worker:
    def __init__(self, root, client, *, target_article=None):
        self.root = Path(root).resolve()
        self.client = client
        self.target_article = target_article
        identity = self.root / "api/identity.json"
        if not identity.exists():
            atomic_json(identity, {"client": secrets.token_hex(12)})
        self.identity = read(identity)["client"]

    def select(self, date):
        with process_lock(self.root / "coordinator.lock"):
            paths = sorted(
                (self.root / "queue").glob("*/ticket.json"),
                key=lambda p: (
                    read(p)["meta"]["date"],
                    {"taxonomy": 0, "review": 1, "writer": 2, "research": 3}.get(
                        read(p)["stage"], 4
                    ),
                    read(p).get("created_at", ""),
                ),
            )
            for path in paths:
                job = read(path)
                if (
                    self.target_article is not None
                    and tuple(
                        job["meta"].get(k) for k in ("date", "category", "number")
                    )
                    != self.target_article
                ):
                    continue
                if job["meta"]["date"] > date or job["state"] != "pending":
                    continue
                atomic_json(
                    self.root / "api/active.json",
                    {
                        "ticket": job["id"],
                        "run_id": secrets.token_hex(12),
                        "state": "AUTHORIZING",
                        "stage": job["stage"],
                        "started_epoch": time.time(),
                    },
                )
                job.update(
                    state="claimed",
                    client=self.identity,
                    claimed_at=datetime.now(BEIJING).isoformat(),
                )
                atomic_json(path, job)
                return job
        return None

    def once(self, date):
        ensure_running(self.root)
        tick(self.root)
        active_path = self.root / "api/active.json"
        if active_path.exists():
            active = read(active_path)
            job = read(self.root / "queue" / active["ticket"] / "ticket.json")
            if (
                self.target_article is not None
                and tuple(
                    job["meta"].get(key) for key in ("date", "category", "number")
                )
                != self.target_article
            ):
                return {
                    "status": "blocked_other_article_execution",
                    "ticket": active["ticket"],
                }
            if active["state"] == "SUBMITTED" and job["state"] in {
                "accepted",
                "revision_requested",
                "needs_attention",
            }:
                archive = self.root / "api/history" / (active["run_id"] + ".json")
                archive.parent.mkdir(parents=True, exist_ok=True)
                active_path.replace(archive)
            elif job.get('meta', {}).get('workflow') == 'rewrite-v2' and active['state'] == 'REQUESTING':
                # V2 has nested parser/material/style/compliance calls. Re-enter
                # the same execution; each call checks its persisted send intent.
                # A saved writer response alone is not the full stage answer.
                return self.execute(job, active)
            elif active["state"] == "AUTHORIZING" or (
                active["state"] == "REQUESTING"
                and not (
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).exists()
            ):
                # No API send-intent exists yet, so continuing cannot duplicate a call.
                if job["state"] == "pending":
                    with process_lock(self.root / "coordinator.lock"):
                        job.update(
                            state="claimed",
                            client=self.identity,
                            claimed_at=datetime.now(BEIJING).isoformat(),
                        )
                        atomic_json(
                            self.root / "queue" / job["id"] / "ticket.json", job
                        )
                return self.execute(job, active)
            elif (
                active["state"] == "REQUESTING"
                and (
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).is_file()
                and read(
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).get("http_status")
                in {401, 402}
                and state(self.root).get("resumed_epoch", 0)
                > active.get("started_epoch", 0)
            ):
                run = self.root / "api/runs" / active["run_id"]
                (run / "call").rename(run / ("rejected-call-" + str(time.time_ns())))
                active["started_epoch"] = time.time()
                atomic_json(active_path, active)
                return self.execute(job, active)
            elif (
                active["state"] == "REQUESTING"
                and (
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).is_file()
                and read(
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).get("state")
                == "INVALID_RESPONSE"
            ):
                failure = read(
                    self.root / "api/runs" / active["run_id"] / "call/api_state.json"
                ).get("failure_code")
                if failure == "output_incomplete":
                    return self.failed(job, active, failure)
                return self.failed(job, active, "invalid_response")
            elif (
                active["state"] == "REQUESTING"
                and (
                    self.root / "api/runs" / active["run_id"] / "call/response.json"
                ).is_file()
            ):
                run = self.root / "api/runs" / active["run_id"]
                # Completed response is already durable and tied to immutable run
                # inputs. Do not re-send an old expensive payload after upgrades.
                answer = read(run / "call/response.json")
                atomic_json(run / "answer.json", answer)
                active["state"] = "RESPONDED"
                atomic_json(active_path, active)
                return self.finish(job, active)
            elif active["state"] != "RESPONDED":
                return {
                    "status": "blocked_unknown_execution",
                    "ticket": active["ticket"],
                    "state": active["state"],
                }
            else:
                return self.finish(job, active)
        from .auto_repair import schedule
        schedule(self.root, date, self.target_article)
        job = self.select(date)
        if job is None:
            failed = [
                read(path)
                for path in (self.root / "queue").glob("*/ticket.json")
                if read(path).get("state") == "needs_attention"
                and read(path)["meta"]["date"] <= date
            ]
            current = [j for j in failed if j['meta']['date'] == date]
            historical = len(failed)-len(current)
            if current:
                known=all((self.root/'queue'/j['id']/'receipt.json').is_file() and
                          read(self.root/'queue'/j['id']/'receipt.json').get('state') in {'completed','failed'} for j in current)
                return {
                    "status": "completed_with_failures" if known else "needs_attention",
                    "date": date,
                    "failed_tickets": len(current),
                    "historical_failed_tickets": historical,
                }
            return {"status": "idle", "date": date, "failed_tickets":0,
                    "historical_failed_tickets":historical}
        return self.execute(job, read(active_path))

    def execute(self, job, active):
        ensure_running(self.root)
        active_path = self.root / "api/active.json"
        run_id = active["run_id"]
        job = authorize(self.root, job["id"], self.identity, run_id)
        active = {**active, "execution": job["execution"]}
        location = self.root / job["location"]
        run = self.root / "api/runs" / run_id
        run.mkdir(parents=True, exist_ok=True)
        from .rewrite_v2.common import enabled as v2_enabled
        if job["stage"] in {"writer", "review"} and not v2_enabled(job):
            from .staged_editorial import source_map, validate_research

            from .staged_editorial import research_for_writer
            research = research_for_writer(location.parent/'writer')
            if (research / "research_result.json").exists():
                try:
                    validate_research(
                        read(research / "research_result.json"),
                        source_map(
                            read(research / "research_input.json")["observations"]
                        ),
                        read(research / "stage_job.json")["job_id"],
                        primary_url=read(research/'research_input.json').get('reference_design', {}).get('primary_url'),
                    )
                    if job['stage']=='writer':
                        from .consumer_prompts import require_writer_material
                        require_writer_material(read(location/'knowledge.json'),read(location/'product.json'),read(research/'research_result.json').get('knowledge_units',[]))
                except ValueError as error:
                    event(
                        self.root,
                        "quality",
                        "研究知识未通过写作前检查",
                        detail=str(error),
                        ticket=job["id"],
                    )
                    # This is a local article input failure before any API send.
                    # Keep its receipt/evidence and let unrelated articles proceed.
                    atomic_json(run / "preflight_rejection.json", {
                        "ticket": job["id"], "request_sent": False,
                        "reason": str(error), "at": time.time(),
                    })
                    return self.failed(job, active, "research_material_insufficient", detail=str(error))
        for name, expected in job["inputs"].items():
            if (
                safe_name(name) != name
                or "/" in name
                or "\\" in name
                or (location / name).is_symlink()
                or file_hash(location / name) != expected
            ):
                raise ValueError("Task input is unsafe or changed")
            shutil.copyfile(location / name, run / name)
        active.update(state="REQUESTING", execution=job["execution"])
        atomic_json(active_path, active)
        atomic_json(
            self.root / "api/health.json",
            {
                **active,
                "status": "requesting",
                "checked_epoch": time.time(),
                "model": "deepseek-flash",
            },
        )
        try:
            cache = (
                self.root / "api/research_cache" / (research_key(run) + ".json")
                if job["stage"] == "research"
                else None
            )
            if v2_enabled(job):
                from .rewrite_v2.integration import execute as execute_v2
                answer = execute_v2(self.client, self.root, job, run)
            elif (job['stage'] in {'writer','review'} and job.get('meta',{}).get('known_response_replay')
                    and (job['stage']=='writer' or 'known_response.json' in job['inputs'])):
                from .known_response import load as load_known_response
                answer=load_known_response(self.root,job,run)
                event(self.root,'recovery','本地复核已完整收到的原写作答复，无新增写作API调用',ticket=job['id'])
            elif cache and cache.is_file() and not (run / "revision_note.txt").exists():
                answer = read(cache)
                event(
                    self.root,
                    "research",
                    "复用已通过逐字证据校验的同类分析",
                    ticket=job["id"],
                )
            else:
                local_taxonomy = job['stage'] == 'taxonomy' and read(run/'input.json').get('classification_version') in {'two-genre-v1','three-genre-v1'}
                event(
                    self.root,
                    job["stage"],
                    "开始本地体裁分类（不调用付费API）" if local_taxonomy else "开始 API 阶段（预算检查后才发送）",
                    ticket=job["id"],
                    category=job["meta"].get("category"),
                    number=job["meta"].get("number"),
                )
                if local_taxonomy:
                    from .genre_pools import classify
                    if (self.root/'rewrite_policy.json').is_file() and read(self.root/'rewrite_policy.json').get('workflow') == 'rewrite-v2':
                        from .rewrite_v2.integration import classify
                    taxonomy_input = read(run / "input.json")
                    answer = classify(taxonomy_input['articles'], taxonomy_input['max_per_category'], include_review=taxonomy_input.get('include_review',False))
                elif job['stage'] == 'taxonomy' and len(read(run/'input.json')['articles']) > 24:
                    from .taxonomy_batches import classify
                    answer = classify(self.client, run, job['meta'])
                else:
                    billing_meta = dict(job['meta'])
                    if job['stage']=='research' and read(run/'research_input.json').get('reference_design',{}).get('version') in {'two-genre-v1','three-genre-v1'}:
                        # Every genre article has its own primary research. Only
                        # actual common taxonomy/legacy research is shared.
                        billing_meta['cost_scope'] = 'article'
                    maximum=LIMITS[job['stage']]
                    if job['stage']=='writer' and job.get('meta',{}).get('paragraph_repair'):
                        spec=read(run/'paragraph_repair.json')
                        size=sum(len(p['text']) for p in spec['paragraphs'] if p['id'] in spec['editable_ids'])
                        maximum=min(maximum,max(1200,min(6000,size*2+600)))
                    if job.get('meta',{}).get('consumer_rewrite'):
                        if job['stage']=='review':maximum=min(maximum,1800)
                        elif job['stage']=='writer':
                            maximum=min(maximum,6000)
                            if (run/'revision_note.txt').exists() and '[APPEND_REPAIR_V1]' in (run/'revision_note.txt').read_text('utf8'):
                                maximum=min(maximum,2400)
                    append_mode=(run/'revision_note.txt').is_file() and '[APPEND_REPAIR_V1]' in (run/'revision_note.txt').read_text('utf8')
                    if job['stage']=='writer' and not job.get('meta',{}).get('paragraph_repair') and not append_mode and (run/'knowledge.json').is_file() and (run/'product.json').is_file():
                        from .article_compiler import prepare
                        prepare(run,location)  # no-material stop before Analyzer sends
                        knowledge=read(run/'knowledge.json');reference=knowledge.get('reference_design',{})
                        if reference.get('primary_url') or reference.get('version') in {'two-genre-v1','three-genre-v1'}:
                            from .structure_analyzer import analyze
                            analyze(self.client,run,location,knowledge,billing_meta)
                    value=build_prompt(job,run)
                    from .section_writer import enabled,generate
                    if job['stage']=='writer' and not job.get('meta',{}).get('paragraph_repair') and not append_mode and enabled(run):
                        answer=generate(self.client,run,billing_meta)
                    else:
                        answer=self.client.complete(value,run/'call',max_tokens=maximum,stage=job['stage'],meta=billing_meta)
        except ValueError as error:
            if v2_enabled(job):
                return self.failed(job, active, 'rewrite_v2_invalid_output', detail=str(error))
            from .article_compiler import CompilationBlocked
            from .structure_analyzer import StructureInputError
            if isinstance(error,StructureInputError):return self.failed(job,active,'structure_source_unavailable',detail=str(error))
            if not isinstance(error,CompilationBlocked):raise
            atomic_json(run/'compilation_rejection.json',{'ticket':job['id'],'request_sent':False,**error.report})
            return self.failed(job,active,'topic_not_feasible',detail=error.report['status']+': '+'；'.join(error.report['reasons']))
        except APIError as error:
            if error.code == 'article_budget_exceeded' and not error.uncertain:
                atomic_json(run/'preflight_rejection.json',{'ticket':job['id'],'request_sent':False,'reason':error.code,'at':time.time()})
                return self.failed(job,active,error.code)
            if error.code not in {"invalid_response","output_incomplete","section_generation_exhausted","section_material_insufficient"}:
                raise
            return self.failed(job, active, error.code)
        atomic_json(run / "answer.json", answer)
        active["state"] = "RESPONDED"
        atomic_json(active_path, active)
        return self.finish(job, active)

    def finish(self, job, active):
        run = self.root / "api/runs" / active["run_id"]
        if (
            job.get("execution") != active["execution"]
            or job.get("client") != self.identity
        ):
            raise ValueError("Execution ownership changed")
        receipt_path = self.root / "queue" / job["id"] / "receipt.json"
        if receipt_path.exists():
            receipt = read(receipt_path)
            if (
                receipt.get("execution") != active["execution"]
                or receipt.get("client") != self.identity
            ):
                raise ValueError("Receipt ownership changed")
            active["state"] = "SUBMITTED"
            atomic_json(self.root / "api/active.json", active)
            tick(self.root)
            return {"status": "reconciled_receipt", "ticket": job["id"]}
        # Materialization is repeatable only after a durable successful API response.
        answer = read(run / "answer.json")
        try:
            compiled_review=job['stage']=='review' and (run/'writer_done.json').is_file() and read(run/'writer_done.json').get('compilation')
            from .rewrite_v2.common import enabled as v2_enabled
            if v2_enabled(job):
                pass  # V2's independent sequential reviews are already complete.
            elif compiled_review:
                from .review_quality import process
                answer=process(self.client,run,answer,job['meta'])
            elif job['stage']=='review' and not answer.get('failures') and len(answer.get('checks',{}))==7 and all(answer['checks'].values()) and 'logic_review' not in answer:
                reviewer=getattr(self.client,'review_logic',None)
                if callable(reviewer):
                    # Known malformed audits fail this article; unknown sends
                    # propagate to the protected job-level recovery gate.
                    answer['logic_review']=reviewer(run,run/'logic-call',job['meta'])
                    atomic_json(run/'answer.json',answer)
            materialize(job, run, answer)
        except APIError as error:
            if error.code not in {'article_budget_exceeded','output_incomplete','invalid_response'} or error.uncertain:raise
            atomic_json(run/'logic-known-rejection.json',{'ticket':job['id'],'request_sent':error.code!='article_budget_exceeded','reason':error.code,'at':time.time()})
            return self.failed(job,active,error.code if error.code=='article_budget_exceeded' else 'logic_'+error.code)
        except (KeyError, TypeError, ValueError) as error:
            atomic_json(
                run / "materialization_error.json",
                {"error_type": type(error).__name__, "message": str(error)[:500]},
            )
            event(
                self.root,
                "quality",
                "API返回结构校验失败，保留响应且不作为成品",
                ticket=job["id"],
                error_type=type(error).__name__,
                detail=str(error)[:500],
            )
            return self.failed(job, active, "invalid_stage_schema", detail=str(error)[:500])
        delivery = self.root / "queue" / job["id"] / "delivery"
        delivery.mkdir(parents=True, exist_ok=True)
        files = {}
        for name in job["outputs"]:
            path = run / name
            if not path.is_file() or path.is_symlink():
                raise ValueError("Missing API stage output")
            files[name] = file_hash(path)
            shutil.copyfile(path, delivery / name)
        receipt = {
            "ticket": job["id"],
            "state": "completed",
            "client": self.identity,
            "execution": active["execution"],
            "files": files,
        }
        atomic_json(receipt_path, receipt)
        active["state"] = "SUBMITTED"
        atomic_json(self.root / "api/active.json", active)
        tick(self.root)
        decision = read(self.root / "queue" / job["id"] / "ticket.json")
        atomic_json(self.root/'api/health.json',{'status':decision['state'],'ticket':job['id'],'stage':job['stage'],'checked_epoch':time.time()})
        if job["stage"] == "research" and decision["state"] == "accepted":
            atomic_json(
                self.root / "api/research_cache" / (research_key(run) + ".json"), answer
            )
        event(
            self.root,
            job["stage"],
            "阶段处理完成",
            ticket=job["id"],
            state=decision["state"],
            error=decision.get("error"),
        )
        return {
            "status": decision["state"],
            "ticket": job["id"],
            "stage": job["stage"],
            "error": decision.get("error"),
        }

    def failed(self, job, active, code, *, detail=None):
        atomic_json(
            self.root / "queue" / job["id"] / "receipt.json",
            {
                "ticket": job["id"],
                "state": "failed",
                "client": self.identity,
                "execution": active["execution"],
                "error_code": code,
                **({"detail": detail} if detail else {}),
            },
        )
        active["state"] = "SUBMITTED"
        atomic_json(self.root / "api/active.json", active)
        tick(self.root)
        decision = read(self.root / "queue" / job["id"] / "ticket.json")
        atomic_json(self.root/'api/health.json',{'status':'completed_with_failures','ticket':job['id'],'error_code':code,'checked_epoch':time.time()})
        return {
            "status": decision["state"],
            "ticket": job["id"],
            "stage": job["stage"],
            "error": decision.get("error"),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--key-file", required=True, type=Path)
    parser.add_argument("--date")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--test-budget",
        action="store_true",
        help="Count every request against the persistent development-test cap",
    )
    parser.add_argument(
        "--before-five", action="store_true", help="Explicit pilot execution only"
    )
    args = parser.parse_args()
    root = args.root.resolve()
    budget = Budget(root, test=args.test_budget)
    client = DeepSeekClient(args.key_file, budget=budget)
    try:
        with process_lock(root / "api/worker.lock"):
            worker = Worker(root, client)
            while True:
                today = datetime.now(BEIJING)
                date = args.date or today.date().isoformat()
                try:
                    result = worker.once(date)
                except PipelinePaused:
                    result = {"status": "paused", "date": date}
                except (APIError, OSError, ValueError, KeyError) as error:
                    if isinstance(error, APIError) and not state(root).get("paused"):
                        pause(
                            root,
                            "api_error",
                            "API 请求停止："
                            + error.code
                            + "；须核对后重新检测环境并继续任务",
                        )
                    result = {
                        "status": "blocked",
                        "error_type": type(error).__name__,
                        "error": str(error)
                        if isinstance(error, APIError)
                        else type(error).__name__,
                    }
                atomic_json(
                    root / "api/health.json",
                    {**result, "checked_epoch": time.time(), "model": "deepseek-flash"},
                )
                print(json.dumps(result, ensure_ascii=False), flush=True)
                if args.once:
                    return 2 if result["status"].startswith("blocked") else 0
                time.sleep(10 if result["status"] not in {"idle", "paused"} else 30)
    finally:
        client.close()
        budget.close()


if __name__ == "__main__":
    raise SystemExit(main())
