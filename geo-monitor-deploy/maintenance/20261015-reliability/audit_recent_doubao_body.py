"""Read live native bodies against durable captures, receipts and normalized PG answers."""
import hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code','/opt/monitor']
from native_soak import read,atomic
from question_only_core import lookup_bound
from soak_monitor import fidelity
from doubao_question_aliases import canonical_question_name
base=Path('/opt/monitor/geo-capture');p=read(base/'soak12h_current.json');m=read(Path(p['root'])/'manifest.json')
report={'at':time.time(),'test_id':p['test_id'],'scope':'Recent five processed text captures per Doubao; live native original versus raw ingest and normalized database answer. Does not establish semantic truth of model recommendations.','models':{},'failures':[]}
for model in ('doubao1','doubao2'):
    root=Path('/home/user/redroid-doubao/batches')/m['jobs'][model]['batch'];samples=[]
    with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        rows=[dict(r) for r in db.execute("select * from tasks where state='completed' order by ordinal desc limit 8")]
    for task in rows:
        saved=json.loads(task['result_json']);rid=hashlib.sha256(('redroid-doubao:'+task['task_id']+':'+str(saved['request_id'])).encode()).hexdigest()
        if not (root/'receipts'/(rid+'.json')).exists():continue
        step='live_native_completion';checks={}
        try:
            binding=read(root/(task['task_id']+'-attempt-'+str(task.get('capture_retries',0))+'.binding.json'))
            live=lookup_bound(task,binding)
            assert live['status']=='complete' and live['first_user_turn'] and live['body_capture_complete'] and live['source_capture_complete']
            step='live_native_vs_saved'
            checks={key:live[key]==saved[key] for key in ('body_markdown','body_parts','sources','citations','search_queries','request_id','answer_id','conversation_id')}
            assert all(checks.values()),checks
            item=read(root/'outbox'/(rid+'.json'));receipt=read(root/'receipts'/(rid+'.json'))
            query="select json_build_object('record',e.record,'answer',r.answer,'question',r.question,'sequence_no',r.sequence_no) from monitor_ingest_events e join monitor_runs r on e.model_id=r.model_id and e.run_id=r.run_id where e.request_id='"+rid+"'"
            stored=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query],text=True,timeout=30))
            step='raw_ingest_fidelity'
            fidelity(item,stored['record'])
            step='database_body_and_prompt';checks.update(envelope_native_result=item['payload']['native_result']==saved,database_body=stored['answer']==live['body_markdown'],original_sent_question=stored['record']['native_result']['wire_question']==task['question']==task['wire_question'],canonical_question=stored['question']==canonical_question_name(task['question']))
            assert all(checks.values())
            step='receipt_sizes'
            assert receipt['analysis']['answer_length']==len(live['body_markdown'].strip()) and receipt['analysis']['source_count']==len(live['sources'])
            samples.append({'ordinal':task['ordinal'],'record_number':stored['sequence_no'],'question':task['question'],'panel_category':stored['question'],
                'body_characters':len(live['body_markdown']),'text_parts':len(live['body_parts']),'sources':len(live['sources']),
                'all_native_blocks_finished':all(b.get('is_finish') is True for b in live['raw_answer_blocks']),
                'native_capture_ingest_database_body_equal':True,'all_sources_citations_queries_equal':True,'first_user_turn':True,
                'processed':True,'body_sha256':hashlib.sha256(live['body_markdown'].encode()).hexdigest(),
                'body_start':live['body_markdown'][:130],'body_end':live['body_markdown'][-150:]})
        except Exception as exc:
            report['failures'].append({'model':model,'ordinal':task['ordinal'],'kind':type(exc).__name__,'step':step,'checks':checks,'sent_question':task['question'],'stored_question':stored.get('question') if 'stored' in locals() else None})
        if len(samples)==5:break
    report['models'][model]={'checked':len(samples),'samples':samples}
report['passed']=not report['failures'] and all(v['checked']==5 for v in report['models'].values())
out=base/'maintenance/20261015-reliability/recent-doubao-body-audit.json';atomic(out,report)
export=Path('/tmp/geo-reliability-export/recent-doubao-body-audit.json');export.write_bytes(out.read_bytes());export.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
