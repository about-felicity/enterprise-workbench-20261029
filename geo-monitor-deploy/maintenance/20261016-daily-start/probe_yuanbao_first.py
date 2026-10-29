"""Read exact existing first answer twice; never navigate, click, send, or modify queues."""
import hashlib,json,sys,time,sqlite3
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code','/tmp']
from native_client import NativeClient
from native_core import parse_result,enum
import yuanbao_native_storage as ns

root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261015-181821-d56b0d20')
out=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start/yuanbao-first')
out.mkdir(parents=True,exist_ok=True,mode=0o700)
with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    task=dict(db.execute('select * from tasks where ordinal=322').fetchone())
    assert task['state']=='needs_attention' and not task['result_json']
    assert db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task['task_id'],)).fetchone()[0]==1
cid='0RGfLig07CS';answer=cid+'_2'
baseline=json.loads((root/(task['task_id']+'.pre-send.json')).read_text())
assert cid not in baseline['conversations']
client=NativeClient(root);client.connect()
try:
    source=Path('/home/user/redroid-yuanbao/native_models.js').read_text()
    assert source.count('const id=lastValue.id;')==1
    source=source.replace('const id=lastValue.id;','const id=messageId;')
    source=source.replace('T.i(conversationId,lastValue.pairId)','T.i(conversationId,serializeModel(message,0).pairId)')
    source=source.replace('T.d(0,conversationId,lastValue.pairId)','T.d(0,conversationId,serializeModel(message,0).pairId)')
    bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
    schema=Path('/home/user/redroid-yuanbao/tools/chat_model_schema.json').read_text()
    script=client.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+source)
    script.load()
    results=[]
    for sample in range(2):
        raw=script.exports_sync.read_known(cid,answer)
        (out/f'native-{sample}.json').write_text(json.dumps(raw,ensure_ascii=False))
        assert raw['question']['serverIndex']==1 and raw['message']['serverIndex']==2
        assert raw['question']['serverId']==cid+'_1' and raw['message']['serverId']==answer
        result=parse_result(task,{'conversation_id':cid,'server_answer_id':answer},raw)
        assert result['status']=='complete',result['status']
        results.append(result)
        if sample==0:time.sleep(3)
    assert results[0]==results[1]
    result=results[-1]
    histories=[]
    for path in ns.databases():
        with ns.open_readonly(path) as db:
            db.row_factory=sqlite3.Row
            histories.extend(dict(r) for r in db.execute('select * from ChatMessages where conversation_id=? order by message_index',(cid,)))
    assert [r['message_index'] for r in histories]==[1,2,3,4]
    texts=[];sources=[]
    for row in histories:
        body=json.loads(row['raw_data'])
        assert all(s.get('extra',{}).get('requestId')=='local_'+cid+'_1_1792077280_Q' for s in body['speechesV2'])
        if row['message_index']==2:
            texts=[c['msg'] for s in body['speechesV2'] for c in s['content'] if c['type']=='text']
            sources=[d for s in body['speechesV2'] for c in s['content'] if c['type']=='searchGuid' for d in c['docs']]
    assert '\n\n'.join(texts)==result['body_markdown']
    assert len(sources)==len(result['sources'])==19
    assert {d['url'] for d in sources}=={d['url'] for d in result['sources']}
    result.update(prompt_protocol='question-only-v1',first_user_turn=True)
    (out/'validated-result.json').write_text(json.dumps(result,ensure_ascii=False))
    report={'task_id':task['task_id'],'batch':root.name,'at':time.time(),'status':'validated_first_answer',
            'body_length':len(result['body_markdown']),'sources':len(result['sources']),
            'body_sha256':hashlib.sha256(result['body_markdown'].encode()).hexdigest(),
            'selected_answer':answer,'latest_answer':raw['last']['serverId'],'two_stable_reads':True,
            'sqlite_body_and_sources_match':True,'same_original_client_request_id':True,
            'model_send_actions':0,'production_parser_modified':False,'queue_modified':False}
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
finally:client.close()
