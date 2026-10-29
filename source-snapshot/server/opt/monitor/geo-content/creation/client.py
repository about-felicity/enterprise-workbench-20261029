"""Retry read-only balance checks; never add a retry to paid completion sends."""
import hashlib,json,re,time
from pathlib import Path
from geo_source_cards.deepseek_api import APIError,DeepSeekClient
from geo_source_cards.runtime import atomic_json

def recover_format_metadata(content):
    """Only accept a complete object followed by the redundant JSON-mode marker."""
    if not isinstance(content,str):raise ValueError('Missing JSON content')
    result,end=json.JSONDecoder().raw_decode(content.lstrip())
    tail=content.lstrip()[end:]
    if not isinstance(result,dict) or not re.fullmatch(r'\s*,\s*"type"\s*:\s*"json_object"\s*}\s*',tail):raise ValueError('Not the known redundant response-format suffix')
    return result

def recover_structural_json(content):
    """Only two observed single-delimiter errors; preserve every content byte."""
    if not isinstance(content,str):raise ValueError('Missing JSON content')
    try:json.loads(content)
    except json.JSONDecodeError:pass
    else:raise ValueError('Already valid JSON')
    candidates=[]
    for m in re.finditer(r',\s*"conclusion"\s*:',content):
        candidates.append(('missing_sections_array_close',content[:m.start()]+']'+content[m.start():]))
    if content.rstrip().endswith('}'):
        candidates.append(('redundant_final_object_close',content.rstrip()[:-1]))
    valid={}
    for reason,value in candidates:
        try:result=json.loads(value)
        except (ValueError,TypeError):continue
        if not isinstance(result,dict):continue
        document=result.get('document')
        shape=(set(result)=={'document'} and isinstance(document,dict) and set(document)=={'title','introduction','sections','conclusion'} and isinstance(document['sections'],list))
        research=set(result)=={'units','angle','sections','gate'} and isinstance(result['units'],list) and isinstance(result['sections'],list)
        if shape or research:valid[value]=(result,reason)
    if len(valid)!=1:raise ValueError('Not an unambiguous known single-delimiter error')
    return next(iter(valid.values()))

class CreationClient(DeepSeekClient):
    def __init__(self,key_file,*,session=None,budget=None):
        import os
        if session is None and os.environ.get('GEO_CREATION_MODEL_SOCKET'):
            from .go_transport import GoSession
            session=GoSession(os.environ['GEO_CREATION_MODEL_SOCKET'])
        super().__init__(key_file,session=session,budget=budget)

    def review_logic(self,location,directory,meta):
        from geo_source_cards.article_logic import build_input,prompt,certificate,deterministic_issues
        folder=Path(directory);data=build_input(location)
        value=prompt(data);maximum=2400
        budget=getattr(self,'budget',None);remaining=getattr(budget,'remaining',None)
        available=remaining(meta,'review') if callable(remaining) else None
        if isinstance(available,(int,float)):
            from geo_source_cards.deepseek_api import request_payload
            from geo_source_cards.api_budget import INPUT_MISS,OUTPUT
            size=len(json.dumps(request_payload(value,0)['messages'],ensure_ascii=False).encode('utf8'))+256
            affordable=int((available-size*INPUT_MISS/1000000-0.000001)*1000000/OUTPUT)
            maximum=max(1600,min(maximum,affordable))
            atomic_json(folder/'output_budget_plan.json',{'remaining_cny':available,'input_byte_bound':size,
                'max_tokens':maximum,'minimum_complete_audit_tokens':1600,'ledger_reservation_still_required':True})
        result=self.complete(value,folder,max_tokens=maximum,stage='review',meta=meta)
        text=(Path(location)/'draft.md').read_text('utf-8-sig')
        product=json.loads((Path(location)/'product.json').read_text('utf-8-sig'))
        cert=certificate(result,data,deterministic_issues(text,product))
        atomic_json(folder/'logic_certificate.json',cert)
        return cert

    def complete(self,prompt,directory,**kwargs):
        try:return super().complete(prompt,directory,**kwargs)
        except APIError as error:
            if error.code!='invalid_response':raise
            folder=Path(directory)
            state=json.loads((folder/'api_state.json').read_text())
            answer=json.loads((folder/'answer.json').read_text())
            if state.get('error_type')!='JSONDecodeError' or answer.get('finish_reason')!='stop':raise
            try:
                result=recover_format_metadata(answer.get('content'));reason='redundant-json-mode-marker'
            except (ValueError,TypeError):
                try:result,reason=recover_structural_json(answer.get('content'))
                except (ValueError,TypeError):raise error from None
            projection={'reason':reason,'raw_answer_preserved':True,'raw_content_sha256':hashlib.sha256(answer['content'].encode()).hexdigest(),'new_paid_requests':0,'downstream_validation_required':True}
            atomic_json(folder/'json_response_projection.json',projection)
            atomic_json(folder/'response.json',result)
            atomic_json(folder/'api_state.json',{**state,'state':'RESPONDED','finished_epoch':time.time(),'usage':answer.get('usage'),'format_projection':reason})
            return result

    def balance(self):
        for attempt in range(3):
            try:return super().balance()
            except APIError as error:
                retryable=error.code=='balance_unavailable' or error.code=='balance_http_429' or error.code.startswith('balance_http_5')
                if not retryable or attempt==2:raise
                time.sleep((1,3)[attempt])
