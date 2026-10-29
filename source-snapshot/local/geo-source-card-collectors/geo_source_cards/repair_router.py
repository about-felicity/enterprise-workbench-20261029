"""Bind review findings to text and route repairs before a paid rewrite."""
import json,re
from pathlib import Path
from .article_logic import segments,text_hash
from .argument_plan import digest
from .quality_checks import findings as local_issues
from .runtime import atomic_json

VERSION='repair-router-v1'
BLOCKED={'NEED_MORE_EVIDENCE','REVIEW_DISPUTED','REPAIR_EXHAUSTED'}


class RepairBlocked(ValueError):pass


def route(text,knowledge,product,review,reason='',attempts=0,feasibility=None):
    ps=segments(text);by_id={p['id']:p for p in ps};bound=review.get('draft_sha256')==text_hash(text)
    findings=[];unresolved=[]
    # Source-less LLM opinions never gain authority by being in failures[].
    if bound:
        if review.get('arbitration'):
            from .review_arbitration import enforce
            enforce(review,text,knowledge,product)
        logic={} if review.get('arbitration') else review.get('logic_review',{})
        for issue in review.get('review_issues',[]):
            ids=issue.get('paragraph_ids',[])
            if not ids or not set(ids)<=by_id.keys():unresolved.append('仲裁问题缺少有效定位');continue
            findings.append({**issue,'type':issue['kind'],'origin':'arbitration'})
        for issue in logic.get('review',{}).get('issues',[])+logic.get('local_issues',[]):
            ids=issue.get('paragraph_ids',[])
            if not ids or not set(ids)<=by_id.keys() or not issue.get('reason'):
                unresolved.append('逻辑审稿缺少有效的正文定位');continue
            findings.append({'type':issue.get('kind','unsupported_inference'),'paragraph_ids':ids,'reason':issue['reason'],
                             'origin':'logic_review','evidence_ids':issue.get('evidence_ids',[]),'repair':issue.get('repair','')})
        spans={f'C{i}':m.group() for i,m in enumerate(re.finditer(r'[^\n。！？]+[。！？]?',text),1) if m.group().strip()}
        for failure in ([] if review.get('arbitration') else review.get('failures',[])):
            quoted=[spans[c] for c in re.findall(r'\bC\d+\b',str(failure)) if c in spans]
            quoted+=re.findall(r'[“「](.{8,200}?)[”」]',str(failure))
            ids=[p['id'] for p in ps if any(q in p['text'] for q in quoted)]
            if not ids:unresolved.append(str(failure));continue
            findings.append({'type':'unsupported_fact','paragraph_ids':ids,'reason':str(failure),'origin':'fact_review','evidence_ids':[]})
    for issue in local_issues(text,knowledge,product):findings.append({**issue,'type':issue['kind'],'origin':'deterministic'})
    if reason and not findings:
        ids=[p['id'] for p in ps if len(p['text'])>=12 and p['text'][:60] in reason]
        if ids:findings.append({'type':'local_correction','paragraph_ids':ids,'reason':reason,'origin':'deterministic','evidence_ids':[]})
    # Legacy text errors with no stable location are not silently declared false.
    if feasibility and feasibility['status'] in {'NEED_MORE_EVIDENCE','CONFLICT'}:action='NEED_MORE_EVIDENCE'
    elif feasibility and feasibility['status']=='DEGRADED':action='REPLAN'
    elif bound and unresolved:action='REVIEW_DISPUTED'
    elif attempts>=2:action='REPAIR_EXHAUSTED'
    elif re.search(r'NEED_MORE_EVIDENCE|CONFLICT:|主参考缺少|产品资料不足',reason):action='NEED_MORE_EVIDENCE'
    elif re.search(r'DEGRADED:|排名依据不存在|没有共同比较标准|标题本身无法|invalid_ranking_basis',reason+' '+json.dumps(findings,ensure_ascii=False)):action='REPLAN'
    elif not findings:
        action='REWRITE' if not review else 'REVIEW_DISPUTED'
    else:action='PATCH'
    affected={i for f in findings for i in f.get('paragraph_ids',[]) if i in by_id};scopes=[]
    headings=[p['id'] for p in ps if p['kind']=='heading']
    def section_for(identity):
        pos=list(by_id).index(identity)
        return next((h for h in reversed(headings) if list(by_id).index(h)<=pos),None)
    for f in findings:
        sections={section_for(i) for i in f['paragraph_ids']}
        scope='sentence' if f['type'] in {'unsupported_fact','name_error','identifier_error'} else 'paragraph'
        if f['type'] in {'order_error','scope_shift','topic_drift'}:scope='multi-section' if len(sections)>1 else 'section'
        if f['type']=='contradiction' and len(sections)>1:scope='multi-section'
        if scope in {'section','multi-section'}:
            affected.update(p['id'] for p in ps if section_for(p['id']) in sections)
        f.update(issue_id=f'I{len(scopes)+1:03d}',severity='major',repair_scope=scope,
                 text=[by_id[i]['text'] for i in f['paragraph_ids']],affected_sections=sorted(filter(None,sections)))
        scopes.append(scope)
    # Global ranking/scope failures invalidate all sections and closing claims.
    if action=='REPLAN':affected=set(by_id)
    result={'version':VERSION,'draft_sha256':text_hash(text),'evidence_sha256':digest({'knowledge':knowledge,'product':product}),
            'action':action,'scope':'multi-section' if 'multi-section' in scopes else 'section' if 'section' in scopes else 'paragraph',
            'editable_ids':sorted(affected),'issues':findings,'unresolved_review':unresolved,
            'review_disputes':review.get('review_disputes',[]) if bound else [],
            'attempts':attempts,'max_repairs':2,'requires_fresh_fact_and_logic_review':True,
            'review_verdict_overridden':False,'feasibility':feasibility}
    from .editorial_schema import validate_record
    for issue in findings:validate_record('Issue',issue)
    validate_record('Repair',result)
    return result


def prepare(writer,reason='',attempts=0):
    writer=Path(writer);read=lambda p:json.loads(p.read_text('utf8')) if p.is_file() else {}
    text=(writer/'draft.md').read_text('utf8')
    knowledge,product=read(writer/'knowledge.json'),read(writer/'product.json')
    from .article_compiler import compile_article
    from .consumer_prompts import evidence_units
    assessment=compile_article(knowledge,product,evidence_units(writer))['feasibility']
    result=route(text,knowledge,product,read(writer.parent/'review/result.json'),reason,attempts,assessment)
    if result['action']=='REPLAN':
        # Replan the invalid comparison, preserving the evidence/roster and
        # giving Writer an explicit new plan rather than guessing new facts.
        from .article_compiler import compile_article
        compiled=compile_article(knowledge,product,evidence_units(writer))
        result['replan']={'version':'evidence-scoped-replan-v1','base_sha256':text_hash(text),
            'goal':compiled['feasibility']['proposed_scope'],
            'comparison_dimensions':compiled['feasibility']['available_dimensions'],
            'forbidden_conclusions':compiled['feasibility']['forbidden_conclusions'],
            'sections':compiled['sections'],'repair_instruction':'按可用属性重新组织比较依据，逐项复核所有受影响章节及开头结尾；删除无依据排名结论，不发明比较数据',
            'fresh_review_required':True}
        atomic_json(writer/'replan.json',result['replan'])
    atomic_json(writer/'repair_route.json',result)
    if result['action'] in BLOCKED:raise RepairBlocked(result['action']+': 返修路由已停止自动付费重写，详见repair_route.json')
    return result
