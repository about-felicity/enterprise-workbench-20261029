"""Read-only pending native task and current UI markers; no navigation or send."""
import json,os,sqlite3,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code']
from native_soak import read,atomic
base=Path('/opt/monitor/geo-capture');p=read(base/'soak12h_current.json');m=read(Path(p['root'])/'manifest.json')
home=Path('/home/user/redroid-yuanbao/batches')/m['jobs']['yuanbao']['batch']
report={'at':time.time(),'test_id':p['test_id'],'model_actions':0}
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    row=db.execute("select task_id,ordinal,question,state,prepared_at,error,request_id from tasks where state in ('prepared','needs_attention') order by ordinal limit 1").fetchone()
    if not row:report['pending']=False
    else:
        task=dict(row);report['task']=task
        report['events']=[dict(x) for x in db.execute('select event,time,detail from events where task_id=? order by time',(task['task_id'],))]
        report['files']=[{'name':f.name,'bytes':f.stat().st_size} for f in home.glob(task['task_id']+'*')]
        os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
        import uiautomator2 as u2
        d=u2.connect('127.0.0.1:5559');xml=d.dump_hierarchy()
        out=base/'maintenance/20261015-reliability/yuanbao-ack';out.mkdir(exist_ok=True,mode=0o700)
        (out/'current-ui.xml').write_text(xml)
        nodes=list(ET.fromstring(xml).iter('node'))
        report['ui']={'exact_question_visible':any(n.get('text')==task['question'] for n in nodes),
            'markers':[{'text':n.get('text'),'description':n.get('content-desc'),'resource_id':n.get('resource-id')} for n in nodes if any(w in (n.get('text','')+' '+n.get('content-desc','')) for w in ('网络','重试','停止','重新生成','加载失败','登录','验证'))]}
        report['ui']['text_nodes']=[{'class':n.get('class'),'text':n.get('text','')[:95],'description':n.get('content-desc','')[:95],'resource_id':n.get('resource-id'),'bounds':n.get('bounds')} for n in nodes if n.get('text') or n.get('content-desc')][:50]
        last=db.execute("select ordinal,result_json from tasks where state='completed' order by ordinal desc limit 1").fetchone()
        if last:
            result=json.loads(last['result_json']);report['last_completed']={'ordinal':last['ordinal'],'question':result['wire_question'],'cid':result['conversation_id']}
        sys.path.insert(0,'/home/user/redroid-yuanbao')
        from native_client import NativeClient
        from native_core import text_entities
        from unattended_worker import deadline
        client=NativeClient(home)
        try:
            with deadline(30):
                client.connect();rows=client.script.exports_sync.snapshot(task['question'])
                prior=read(home/(task['task_id']+'.pre-send.json'))
                report['baseline_created_at']=prior['created_at'];report['baseline_cids']=prior['conversations'];report['native_candidates']=[]
                for entry in rows:
                    value=entry.get('value',{});ctx=value.get('h',{})
                    if entry['kind']!='markdown' or value.get('v')!=task['question']:continue
                    cid=ctx.get('conversationId');answer=ctx.get('msgId')
                    if not cid or not answer:continue
                    raw=client.script.exports_sync.read_known(cid,answer)
                    atomic(out/('native-'+str(len(report['native_candidates']))+'.json'),raw)
                    atomic(out/('render-'+str(len(report['native_candidates']))+'.json'),value)
                    report['native_candidates'].append({'cid_in_baseline':cid in prior['conversations'],
                        'conversation_id':cid,'answer_id':answer,'question_server_index':raw.get('question',{}).get('serverIndex'),
                        'create_time':raw.get('question',{}).get('createTime'),
                        'native_question_equal':'\n\n'.join(text_entities(raw['question_entities']))==task['question'],
                        'question_identity':{k:raw['question'].get(k) for k in ('id','serverId','serverIndex','speaker','pairId')},
                        'message_identity':{k:raw['message'].get(k) for k in ('id','serverId','serverIndex','speaker','pairId')},
                        'message_state':raw.get('message',{}).get('state'),'content_state':raw.get('content',{}).get('state'),
                        'isEof':raw.get('content',{}).get('isEof'),'isBusy':raw.get('conversation',{}).get('isBusy')})
        finally:client.close()
atomic(base/'maintenance/20261015-reliability/yuanbao-ack-diagnostic.json',report)
print(json.dumps(report,ensure_ascii=False))
