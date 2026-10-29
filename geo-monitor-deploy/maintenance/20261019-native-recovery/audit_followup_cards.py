import hashlib,json,sqlite3,time,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import parse_blocks
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261019-native-recovery')
control=sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True);control.row_factory=sqlite3.Row
out={'checked_at':time.time(),'after_fix_epoch':1792372115,'lanes':[]}
def has_cards(blocks):
 s=json.dumps(blocks,ensure_ascii=False)
 return any(key in s for key in ('render_ecom_card_widget','ecom_card_type','product_list','EcomCard'))
for model in ('doubao1','doubao2'):
 job=control.execute('select j.* from jobs j join settings s on s.current_batch=j.batch where s.model=?',(model,)).fetchone();root=Path(job['health']).parent
 db=sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 lane={'model':model,'batch':job['batch'],'completed':0,'after_fix_completed':0,'after_fix_receipts_verified':0,'after_fix_web_sources':0,'after_fix_zero_sources':0,'after_fix_body_and_cards':0,'after_fix_cards_without_body':0,'zero_source_examples':[],'unresolved':[]}
 for row in db.execute("select * from tasks where state='completed'"):
  t=dict(row);r=json.loads(t['result_json']);lane['completed']+=1
  completed=db.execute("select max(time) from events where task_id=? and event='completed'",(t['task_id'],)).fetchone()[0]
  if completed<out['after_fix_epoch']:continue
  lane['after_fix_completed']+=1
  rid=hashlib.sha256(('redroid-doubao:'+t['task_id']+':'+str(r['request_id'])).encode()).hexdigest()
  rp=root/'receipts'/(rid+'.json')
  if rp.exists():
   receipt=json.loads(rp.read_text());a=receipt.get('analysis',{})
   if a.get('source_capture_complete') is True and a.get('answer_length')==len(r['body_markdown'].strip()) and a.get('source_count')==len(r.get('sources',[])):lane['after_fix_receipts_verified']+=1
  body=r.get('body_markdown','').strip();cards=has_cards(r.get('raw_answer_blocks',[]));sources=r.get('sources',[])
  lane['after_fix_web_sources' if sources else 'after_fix_zero_sources']+=1
  if cards:lane['after_fix_body_and_cards' if body else 'after_fix_cards_without_body']+=1
  if not sources:
   matching=list((root/'outbox').glob('*.json'));receipt=None
   for p in matching:
    item=json.loads(p.read_text());native=item.get('payload',{}).get('native_result',{})
    if native.get('task_id')==t['task_id']:
     rp=root/'receipts'/p.name
     if rp.exists():receipt=json.loads(rp.read_text())
     break
   lane['zero_source_examples'].append({'ordinal':t['ordinal'],'question':t['question'],'body_length':len(body),'commerce_cards':cards,'source_availability':r.get('source_availability'),'receipt_verified':bool(receipt and receipt.get('analysis',{}).get('source_count')==0)})
 for row in db.execute("select * from tasks where state in ('prepared','needs_attention')"):
  t=dict(row);bound=root/(t['task_id']+'-attempt-'+str(t.get('capture_retries',0))+'.binding.json')
  x={'ordinal':t['ordinal'],'state':t['state'],'bound':bound.exists()}
  if bound.exists():
   b=json.loads(bound.read_text())
   with sqlite3.connect(Path(b['database']).as_uri()+'?mode=ro',uri=True) as native:
    native.row_factory=sqlite3.Row
    answers=native.execute('select content from im_message where conversation_id=? and user_type=2',(b['conversation_id'],)).fetchall()
    x['answers']=[{'body_length':sum(len(k.get('content',{}).get('text_block',{}).get('text','').strip()) for k in parse_blocks(a['content'])),'commerce_cards':has_cards(parse_blocks(a['content'])),'all_blocks_finished':all(k.get('is_finish') is True for k in parse_blocks(a['content']))} for a in answers]
  lane['unresolved'].append(x)
 out['lanes'].append(lane)
(ROOT/'doubao-followup-cards.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
