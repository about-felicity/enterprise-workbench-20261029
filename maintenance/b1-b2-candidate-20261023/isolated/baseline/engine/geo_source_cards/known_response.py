"""Locally reprocess a completed response after a parser or judge-stage failure."""
import hashlib,json,re
from pathlib import Path

def load(root,job,run):
    root=Path(root);run=Path(run);read=lambda p:json.loads(p.read_text('utf8'))
    proof=read(run/'known_response.json');identity=proof.get('source_run','');ticket=proof.get('source_ticket','')
    if not re.fullmatch(r'[a-f0-9]{24}',identity) or not re.fullmatch(r'[a-f0-9]{24}',ticket):raise ValueError('Invalid known-response identity')
    source=root/'api/runs'/identity;old=read(root/'queue'/ticket/'ticket.json')
    if old.get('stage') not in {'writer','review'} or job.get('stage')!=old.get('stage') or old.get('execution',{}).get('run_id')!=identity:raise ValueError('Known response execution ownership changed')
    if any(old['meta'].get(k)!=job['meta'].get(k) for k in ('date','category','number')):raise ValueError('Known response belongs to another article')
    call=source/'call';state=read(call/'api_state.json')
    if state.get('state')!='RESPONDED':raise ValueError('Known response is not a completed paid result')
    raw=(call/'response.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=proof.get('response_sha256'):raise ValueError('Known response bytes changed')
    for name,expected in old['inputs'].items():
        if '/' in name or '\\' in name:raise ValueError('Unsafe known-response input')
        if not (run/name).is_file() or hashlib.sha256((run/name).read_bytes()).hexdigest()!=expected:raise ValueError('Known response input changed: '+name)
    answer=json.loads(raw)
    if not isinstance(answer,dict):raise ValueError('Known response is not an object')
    if job['stage']=='review':
        # Compact review responses refer to locally generated sentence IDs.
        # Rebuild the exact current mapping and draft binding before expanding
        # the saved response, just as a fresh request would; this sends no API.
        from .api_prompts import build_prompt
        build_prompt(job,run)
        if proof.get('logic_source_run'):
            logic_id=proof['logic_source_run']
            if not re.fullmatch(r'[a-f0-9]{24}',logic_id):raise ValueError('Invalid known logic identity')
            logic=root/'api/runs'/logic_id/'logic-call'
            if read(logic/'api_state.json').get('state')!='RESPONDED':raise ValueError('Known logic is not a completed result')
            raw_logic=(logic/'response.json').read_bytes()
            if hashlib.sha256(raw_logic).hexdigest()!=proof.get('logic_response_sha256'):raise ValueError('Known logic bytes changed')
            from .article_logic import build_input,prompt,certificate,deterministic_issues
            from .deepseek_api import request_payload
            data=build_input(run)
            if read(logic/'request.json').get('messages')!=request_payload(prompt(data),0)['messages']:
                raise ValueError('Known whole-article logic input changed')
            text=(run/'draft.md').read_text('utf8');product=read(run/'product.json')
            answer['logic_review']=certificate(json.loads(raw_logic),data,deterministic_issues(text,product))
    return answer
