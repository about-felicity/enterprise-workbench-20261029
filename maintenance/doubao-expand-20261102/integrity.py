import sqlite3,subprocess,json,hashlib,re,collections,xml.etree.ElementTree as ET
from pathlib import Path
from contextlib import closing
def hashtext(v):return hashlib.md5(v.encode()).hexdigest()
native=Path('/home/user/redroid-doubao')
fleet=json.loads(Path('/opt/monitor/geo-capture/fleet.json').read_text())['collectors']
for n in [1,2,3,4]:
 r=Path(next(x['health'] for x in fleet if x['name']==f'豆包 {n}')).parent
 receipts={}; stats=collections.Counter();examples=[];ui_examples=[];detail=[]
 for p in (r/'receipts').glob('*.json'):
  rec=json.loads(p.read_text());rid=rec['save']['run_id'];assert re.fullmatch('doubao-[0-9a-f]+',rid);receipts[rid]=p
 if not receipts:print('EMPTY',n);continue
 sql="""select json_build_object('id',r.run_id,'body',md5(r.payload->>'answer'),'eventbody',md5(e.record->>'answerText'),'urls',(select json_agg(x->>'url') from jsonb_array_elements(e.record->'items') x),'saved', (select json_agg(s.url order by s.source_index) from monitor_sources s where s.model_id=r.model_id and s.run_id=r.run_id),'answer_id',e.record->>'native_answer_id') from monitor_runs r join monitor_ingest_events e using(model_id,run_id) where r.model_id='doubao' and r.run_id in ("""+','.join("'"+k+"'" for k in receipts)+')'
 pg={y['id']:y for y in map(json.loads,subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True).splitlines())}
 for rid,p in receipts.items():
  stats['receipts']+=1
  payload=json.loads((r/'outbox'/p.name).read_text())['payload'];result=payload['native_result'];tid=result['task_id']
  try:
   binding=json.loads(next(r.glob(tid+'-attempt-*.binding.json')).read_text());path=Path(binding['database'])
   with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=3)) as d:
    row=d.execute('select content,status from im_message where local_message_id=? and conversation_id=? and user_type=2',(result['answer_id'],result['conversation_id'])).fetchone()
   if not row:stats['not_in_device_now']+=1;blocks=result['raw_answer_blocks']
   else:stats['read_live']+=1;blocks=json.loads(row[0])
   body=[];urls=[];types=set()
   for blk in blocks:
    c=blk['content'];types.update(set(c)-{'text_block','tips_block','search_query_result_block','pc_event_block'})
    for k in ['tips_block','text_block']:
     if k in c:body.append(c[k]['text'])
    urls.extend(x['text_card'].get('url') for x in c.get('search_query_result_block',{}).get('results',[]))
   body='\n\n'.join(body);v=pg[rid];saved=v['saved'] or [];evt=v['urls'] or []
   matches=all(k.get('is_finish') is True for k in blocks) and not types and body==payload['answerText'] and hashtext(body)==v['eventbody']==v['body'] and str(v['answer_id'])==str(result['answer_id'])
   stats['body_ok']+=int(matches);stats['snapshot_equal']+=int(blocks==result['raw_answer_blocks']);stats['urls_exact_event']+=int(urls==evt);stats['urls_exact_saved']+=int(urls==saved)
   stats['raw_cards']+=len(urls);stats['saved_links']+=len(saved)
   if not matches or urls!=saved or urls!=evt:examples.append((rid,len(body),len(urls),len(set(urls)),len(saved),set(urls)==set(saved)))
   ui=None;xml=r/(tid+'.xml')
   if xml.exists():
    vs=[x.get('text','') for x in ET.parse(xml).iter('node') if x.get('resource-id','').endswith('/tv_reference_title')]
    nums=[int(a) for a in re.findall(r'参考\s*(\d+)\s*篇',' '.join(vs))]
    if nums:ui=nums[-1];stats['ui_has_count']+=1;stats['ui_matches']+=int(ui==len(urls))
    if nums and ui!=len(urls):ui_examples.append((rid,ui,len(urls)))
   if n>=3:detail.append((rid,len(body),len(urls),len(set(urls)),len(saved),ui,len(payload['citations'])))
  except Exception as e:stats['error']+=1;examples.append((rid,type(e).__name__,str(e)[:75]))
 print(n,r.name,dict(stats),'examples',examples[:5],'UI exceptions',ui_examples[:4],'new',detail,flush=True)

