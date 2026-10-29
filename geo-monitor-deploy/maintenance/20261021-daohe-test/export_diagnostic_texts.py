"""Read-only views of received test text, including structure-rejected answers.

These are diagnostic material, never approved articles or production exports.
No response, queue, certificate or receipt is changed.
"""
import sys,json,time,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import recover_format_metadata,recover_structural_json
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');report=runtime.read(M/'test-report.json');rows=[]
def view(document):
 lines=['# '+document['title']]
 lines += [p['text'] for p in document.get('introduction',[])]
 for section in document['sections']:
  lines.append('## '+section['heading']);lines += [p['text'] for p in section['paragraphs']]
 lines += [p['text'] for p in document.get('conclusion',[])]
 return '\n\n'.join(lines)+'\n'
for a in report['articles']:
 root=runtime.job_root(a['job']);folder=root/'days/2026-10-21/jobs'/a['category']/str(a['number']).zfill(2)
 draft=folder/'writer/draft.md';proof={};text='';flavor='no_text'
 if draft.exists():text=draft.read_text('utf-8-sig');flavor='materialized_rejected_draft';proof={'draft_sha256':hashlib.sha256(draft.read_bytes()).hexdigest()}
 else:
  tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
  candidates=sorted([t for t in tickets if t['stage']=='writer' and t['meta'].get('category')==a['category'] and t['meta'].get('number')==a['number']],key=lambda t:t.get('created_at',''),reverse=True)
  for t in candidates:
   run=root/'api/runs'/t.get('execution',{}).get('run_id','none');state=runtime.read(run/'call/api_state.json')
   raw=runtime.read(run/'call/answer.json');answer=runtime.read(run/'call/response.json');reason='parsed_received_response'
   if not answer and raw.get('finish_reason')=='stop':
    try:answer=json.loads(raw['content'])
    except (ValueError,TypeError,KeyError):
     try:answer=recover_format_metadata(raw.get('content'));reason='known_redundant_metadata'
     except (ValueError,TypeError):
      try:answer,reason=recover_structural_json(raw.get('content'))
      except (ValueError,TypeError):continue
   if not isinstance(answer,dict) or 'document' not in answer:continue
   try:text=view(answer['document'])
   except (KeyError,TypeError):continue
   proof={'run':run.name,'ticket':t['id'],'api_state':state.get('state'),'parse_projection':reason,'raw_response_sha256':hashlib.sha256((run/'call/answer.json').read_bytes()).hexdigest(),'original_section_ids':[v.get('id') for v in answer['document']['sections']]}
   flavor='unvalidated_model_response_reading_view';break
 rows.append({**a,'flavor':flavor,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest() if text else None,'reading_view_proof':proof,'approved_for_delivery':False})
value={'at':time.time(),'purpose':'Diagnostic inspection only; every sample remains blocked from approved production downloads','samples':len(rows),'readable_texts':sum(bool(a['text']) for a in rows),'materialized_drafts':report['drafts'],'approved':report['ready'],'articles':rows}
runtime.atomic_json(M/'diagnostic-texts.json',value);print(json.dumps({k:v for k,v in value.items() if k!='articles'},ensure_ascii=False))
