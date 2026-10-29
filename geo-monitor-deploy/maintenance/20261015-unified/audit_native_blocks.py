import json,sys,subprocess,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
from unattended_core import parse_blocks
out=Path('/opt/monitor/geo-capture/maintenance/20261015-unified')
q="""select coalesce(json_agg(json_build_object('sequence',r.sequence_no,'model',r.model_id,'run_id',r.run_id,'answer',r.answer,'serial',r.serial,'record',e.record)),'[]') from monitor_runs r join monitor_ingest_events e on e.model_id=r.model_id and e.run_id=r.run_id where r.model_id='doubao' and r.sequence_no in (42810,42941)"""
rows=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',q],text=True))
report=[]
for row in rows:
 record=row['record'];native=record.get('native_result',{});match=None
 for path in databases(row['serial']):
  db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
  answer=db.execute('select * from im_message where local_message_id=?',(native.get('answer_id'),)).fetchone()
  if not answer:db.close();continue
  request=db.execute('select * from im_message where local_message_id=?',(native.get('request_id'),)).fetchone()
  blocks=parse_blocks(answer['content']);request_blocks=parse_blocks(request['content'])
  texts=[b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content']]
  wire='\n\n'.join(b['content']['text_block']['text'] for b in request_blocks if 'text_block' in b['content'])
  raw={'sequence':row['sequence'],'answer_blocks':blocks,'request_blocks':request_blocks,'message_columns':list(answer.keys())}
  (out/('native-blocks-'+str(row['sequence'])+'.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2))
  match={'sequence':row['sequence'],'native_text_equals_database':'\n\n'.join(texts)==row['answer'],'native_length':len('\n\n'.join(texts)),'native_body_parts':len(texts),'total_blocks':len(blocks),'all_native_blocks_finished':all(b.get('is_finish') is True for b in blocks),'actual_sent_prompt':wire,'block_shapes':[{'content_keys':list(b['content']),'text_keys':list(b['content'].get('text_block',{})),'block_keys':list(b)} for b in blocks]}
  db.close();break
 report.append(match or {'sequence':row['sequence'],'native_available':False})
(out/'native-body-layer-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
