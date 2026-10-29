"""Fact result + independent whole-article review + evidence-bound arbitration."""
import copy,json
from pathlib import Path
from .runtime import atomic_json
FACT_CHECKS={'category_fit','structure_fit','innovation_present','product_gate_respected','no_invented_tests','no_unsupported_claims','consumer_article'}


def verify_final(answer,text,knowledge,product,*,location=None):
    from .argument_plan import digest
    from .article_logic import text_hash
    pipeline=answer.get('quality_pipeline',{})
    if pipeline.get('version')=='review-quality-v2':
        from .review_inputs import fingerprint
        location=location or pipeline.get('source_location')
        if location is None or pipeline.get('review_inputs_sha256')!=fingerprint(location,text=text,knowledge=knowledge,product=product):
            raise ValueError('Stale final review sources/mappings/contracts; fresh review required')
    else:
        raise ValueError('Stale legacy final review lacks source binding')
    if (pipeline.get('version')!='review-quality-v2' or pipeline.get('independent_logic_executed') is not True
        or pipeline.get('draft_sha256')!=text_hash(text)
        or pipeline.get('evidence_sha256')!=digest({'knowledge':knowledge,'product':product})):
        raise ValueError('Stale or incomplete final review: current draft/evidence and independent logic review required')


def process(client,location,answer,meta):
    from .api_prompts import expand_references
    from .quality_checks import findings,semantic_candidates
    from .review_arbitration import run
    location=Path(location)
    knowledge=json.loads((location/'knowledge.json').read_text('utf8'));product=json.loads((location/'product.json').read_text('utf8'))
    from .argument_plan import digest
    evidence_hash=digest({'knowledge':knowledge,'product':product})
    from .review_inputs import fingerprint
    def invalid(reason):
        atomic_json(location/'review_cache_status.json',{'status':'needs_reaudit','reason':reason,'new_request_started_by_invalidation':False,'old_evidence_preserved':True})
        raise ValueError('Stale review inputs: '+reason)
    try:input_hash=fingerprint(location)
    except ValueError as e:invalid(str(e))
    binding=location/'review_inputs.json'
    if binding.exists():
        prior=json.loads(binding.read_text('utf8'))
        if prior.get('sha256')!=input_hash:invalid('original sources, body, maps or contracts changed')
    elif any((location/n).exists() for n in ('quality_pipeline.json','fact-original.json','logic-call/logic_certificate.json','arbitration-call/certificate.json','arbitration-call/batches.json')):
        invalid('legacy review cache has no complete source fingerprint')
    else:atomic_json(binding,{'version':'review-inputs-v2','sha256':input_hash})
    marker=location/'quality_pipeline.json'
    if marker.is_file():
        from .article_logic import text_hash
        from .argument_plan import digest
        state=json.loads(marker.read_text('utf8'))
        if state['answer_sha256']!=digest(answer):raise ValueError('Stale review pipeline result')
        try:verify_final(answer,(location/'draft.md').read_text('utf8'),knowledge,product,location=location)
        except ValueError as e:invalid(str(e))
        if answer.get('arbitration'):
            from .review_arbitration import enforce
            enforce(answer,(location/'draft.md').read_text('utf8'),knowledge,product,location=location)
        return answer
    original=location/'fact-original.json'
    if original.exists():answer=json.loads(original.read_text('utf8'))
    else:atomic_json(original,answer)
    answer=expand_references('review',location,copy.deepcopy(answer))
    checks=answer.get('checks');claims=answer.get('claims')
    if (not isinstance(checks,dict) or set(checks)!=FACT_CHECKS or any(type(v) is not bool for v in checks.values())
            or not isinstance(claims,list) or any(type(c.get('supported')) is not bool for c in claims)
            or not isinstance(answer.get('failures'),list)):
        raise ValueError('Malformed fact review: complete boolean checks/claims required')
    if not all(checks.values()) and not answer['failures']:raise ValueError('Fact rejection lacks actionable findings')
    knowledge=json.loads((location/'knowledge.json').read_text('utf8'));product=json.loads((location/'product.json').read_text('utf8'))
    text=(location/'draft.md').read_text('utf8')
    local=findings(text,knowledge,product)
    candidates=semantic_candidates(text)
    cached=location/'logic-call/logic_certificate.json'
    if cached.exists():
        from .article_logic import build_input
        answer['logic_review']=json.loads(cached.read_text('utf8'))
        if answer['logic_review'].get('input_sha256')!=digest(build_input(location)):raise ValueError('Stale cached logic inputs')
    else:
        reviewer=getattr(client,'review_logic',None)
        if not callable(reviewer):raise ValueError('Independent whole-article logic reviewer required')
        answer['logic_review']=reviewer(location,location/'logic-call',meta)
        atomic_json(cached,answer['logic_review'])
        atomic_json(location/'answer.json',answer)
    if answer.get('failures') or answer['logic_review'].get('status')!='passed' or local or candidates:
        answer=run(client,location,answer,[*local,*candidates],meta)
    else:answer['review_issues']=[];answer['review_disputes']=[];answer['quality_status']='reviewed'
    from .article_logic import text_hash
    if fingerprint(location)!=input_hash:invalid('inputs changed while review was executing')
    from .review_inputs import writer_for
    answer['quality_pipeline']={'version':'review-quality-v2','source_location':str(writer_for(location).resolve()),'review_inputs_sha256':input_hash,'draft_sha256':text_hash(text),'evidence_sha256':evidence_hash,'independent_logic_executed':True,'disputes_do_not_certify_truth':True}
    atomic_json(location/'review.json',answer)
    atomic_json(location/'answer.json',answer)
    from .argument_plan import digest
    atomic_json(marker,{'answer_sha256':digest(answer),'draft_sha256':text_hash(text)})
    return answer
