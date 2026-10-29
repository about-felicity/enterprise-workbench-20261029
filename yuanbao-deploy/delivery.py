"""Frozen, authenticated GEO envelopes and strict processed receipt checks."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import time

import requests

from native_core import NativeDataError
from runtime_reliability import DeliveryGate


def envelope(task, result, completed_at, questions_count):
    captured=datetime.fromtimestamp(completed_at,timezone(timedelta(hours=8))).isoformat()
    record={'collector_model':'yuanbao','question':task['question'],'prompt':task['question'],
        'web_body':result['body_markdown'],'sources':result['sources'],
        'expected_source_count':result['expected_source_count'],'source_capture_complete':True,
        'body_capture_complete':True,'source_list_present':True,'status':'success',
        'task_id':task['ordinal'],'capture_task_id':task['task_id'],'batch_id':task['batch'],
        'round':(task['ordinal']-1)//questions_count+1,'question_index':(task['ordinal']-1)%questions_count+1,
        'serial':'yuanbao-hpe14-android13','source_device':'yuanbao-hpe14-android13',
        'started_at':datetime.fromtimestamp(task['prepared_at'],timezone(timedelta(hours=8))).isoformat(),
        'finished_at':captured,'captured_at':captured,'capture_mode':result['capture_mode'],
        'capture_label':'元宝无头原生采集','url':'https://yuanbao.tencent.com/chat/'+result['conversation_id'],
        'native_conversation_id':result['conversation_id'],'native_request_id':result['request_id'],
        'native_answer_id':result['answer_id'],'citations':result['citations'],
        'search_queries':result['search_queries'],'search_queries_exposed':result['search_queries_exposed'],
        'source_entries':result['raw_source_entries'],'capture_result':result}
    raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    rid=hashlib.sha256(('yuanbao\nyuanbao-hpe14-android13\n'+raw).encode()).hexdigest()
    return {'version':1,'model':'yuanbao','source_device':'yuanbao-hpe14-android13',
            'request_id':rid,'sent_at':completed_at,'record':record}


def verify_receipt(receipt,item):
    record=item['record'];analysis=receipt.get('analysis',{})
    sources=[{'title':s['title'].strip(),'href':s['url'].strip()} for s in record['sources']]
    if (receipt.get('request_id')!=item['request_id'] or receipt.get('model')!='yuanbao'
        or receipt.get('source_device')!=item['source_device'] or not receipt.get('stored_run_id')
        or analysis.get('quarantined') or not analysis.get('answer_present')
        or analysis.get('answer_length')!=len(record['web_body'].strip())
        or analysis.get('source_count')!=len(sources) or analysis.get('sources')!=sources
        or analysis.get('body_capture_complete') is not True
        or analysis.get('source_capture_complete') is not True):
        raise NativeDataError('GEO processed receipt does not match complete native result')


def nontext_envelope(task,result,completed_at,questions_count):
    if result.get('native_answer_kind')!='video_only' or result.get('rich_media_capture_complete') is not True:
        raise NativeDataError('Unsupported audit-only observation')
    item=envelope(task,{**result,'expected_source_count':0},completed_at,questions_count)
    record=item['record']
    record.update(web_body='',body_capture_complete=False,source_capture_complete=False,
                  source_list_present=False,availability='nontext_answer',capture_warning='native_video_only_answer')
    record['capture_result']=result
    raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    item['request_id']=hashlib.sha256(('yuanbao\nyuanbao-hpe14-android13\n'+raw).encode()).hexdigest()
    return item


def verify_nontext_receipt(receipt,item):
    analysis=receipt.get('analysis',{})
    if (receipt.get('request_id')!=item['request_id'] or receipt.get('model')!='yuanbao'
        or receipt.get('source_device')!=item['source_device']
        or analysis.get('quarantined') is not True or receipt.get('stored_run_id')
        or analysis.get('answer_present') is not False or analysis.get('answer_length')!=0
        or analysis.get('body_capture_complete') is not False
        or analysis.get('source_capture_complete') is not False or analysis.get('source_count')!=0):
        raise NativeDataError('Non-text audit receipt leaked into successful text statistics')


class Delivery:
    def __init__(self,root,question_count):
        from unattended_worker import atomic_json
        self.atomic=atomic_json;self.root=root;self.question_count=question_count;self.posts={};self.done=set();self.nontext_done=set()
        for folder in ('outbox','receipts','nontext-outbox','nontext-receipts'):(root/folder).mkdir(exist_ok=True,mode=0o700)
        config=json.loads(Path('/opt/monitor/runtime/lan_result_receiver.json').read_text('utf-8-sig'))
        self.url='http://127.0.0.1:'+str(config['port'])
        self.session=requests.Session();self.session.trust_env=False
        self.session.headers['Authorization']='Bearer '+config['token']
        self.gate=DeliveryGate(root,self.atomic)

    def sync(self,queue):
        observation=self.sync_nontext(queue)
        processed=0;errors=observation.pop('delivery_errors')
        rows=queue.db.execute("select task_id from tasks where state='completed' order by ordinal").fetchall()
        for row in rows:
            if row['task_id'] in self.done:processed+=1;continue
            task=dict(queue.db.execute('select * from tasks where task_id=?',(row['task_id'],)).fetchone());result=json.loads(task['result_json'])
            completed=queue.db.execute("select max(time) from events where task_id=? and event='completed'",(task['task_id'],)).fetchone()[0]
            item=envelope(task,result,completed,self.question_count);rid=item['request_id']
            outbox=self.root/'outbox'/(rid+'.json');receipt_path=self.root/'receipts'/(rid+'.json')
            if outbox.exists():
                if json.loads(outbox.read_text())!=item:raise NativeDataError('Frozen GEO envelope changed')
            else:self.atomic(outbox,item)
            if receipt_path.exists():
                verify_receipt(json.loads(receipt_path.read_text()),item);self.done.add(task['task_id']);self.gate.complete(rid);processed+=1;continue
            original=Path('/opt/monitor/runtime/lan_result_receiver/yuanbao/done')/(rid+'.json')
            if original.exists():
                receipt=json.loads(original.read_text())
                verify_receipt(receipt,item)
                self.atomic(receipt_path,receipt);self.done.add(task['task_id']);self.gate.complete(rid);processed+=1
            elif self.gate.due(rid):
                try:
                    if not self.gate.may_post(rid):self.gate.waiting(rid);continue
                    reply=self.session.post(self.url+'/api/v1/models/yuanbao/results',json=item,timeout=12)
                    reply.raise_for_status();ack=reply.json()
                    if not ack.get('ok') or ack.get('request_id')!=rid:raise NativeDataError('Invalid GEO enqueue receipt')
                    self.gate.waiting(rid,posted=True)
                except requests.RequestException as error:
                    errors.append({'ordinal':task['ordinal'],'kind':type(error).__name__,**self.gate.failed(rid,error)})
            else:
                diagnostic=self.gate.diagnostic(rid)
                if diagnostic.get('code')!='awaiting_processed':errors.append({'ordinal':task['ordinal'],**diagnostic})
        return {'captured':len(rows),'geo_processed':processed,'delivery_errors':errors,**observation}

    def sync_nontext(self,queue):
        rows=queue.db.execute("select task_id from tasks where state='completed_nontext' order by ordinal").fetchall()
        processed=0;errors=[]
        for row in rows:
            if row['task_id'] in self.nontext_done:processed+=1;continue
            task=dict(queue.db.execute('select * from tasks where task_id=?',(row['task_id'],)).fetchone())
            result=json.loads(task['result_json'])
            completed=queue.db.execute("select max(time) from events where task_id=? and event='completed_nontext'",(task['task_id'],)).fetchone()[0]
            item=nontext_envelope(task,result,completed,self.question_count);rid=item['request_id']
            outbox=self.root/'nontext-outbox'/(rid+'.json');receipt_path=self.root/'nontext-receipts'/(rid+'.json')
            if outbox.exists():
                if json.loads(outbox.read_text())!=item:raise NativeDataError('Frozen non-text audit envelope changed')
            else:self.atomic(outbox,item)
            original=Path('/opt/monitor/runtime/lan_result_receiver/yuanbao/done')/(rid+'.json')
            source=receipt_path if receipt_path.exists() else original
            if source.exists():
                receipt=json.loads(source.read_text());verify_nontext_receipt(receipt,item)
                self.atomic(receipt_path,receipt);self.gate.complete(rid);self.nontext_done.add(task['task_id']);processed+=1
            elif self.gate.due(rid):
                try:
                    if not self.gate.may_post(rid):self.gate.waiting(rid);continue
                    reply=self.session.post(self.url+'/api/v1/models/yuanbao/results',json=item,timeout=12)
                    reply.raise_for_status();ack=reply.json()
                    if not ack.get('ok') or ack.get('request_id')!=rid:raise NativeDataError('Invalid non-text audit enqueue receipt')
                    self.gate.waiting(rid,posted=True)
                except requests.RequestException as error:
                    errors.append({'ordinal':task['ordinal'],**self.gate.failed(rid,error)})
            else:
                diagnostic=self.gate.diagnostic(rid)
                if diagnostic.get('code')!='awaiting_processed':errors.append({'ordinal':task['ordinal'],**diagnostic})
        return {'nontext_observations':len(rows),'nontext_processed':processed,'nontext_pending':len(rows)-processed,'delivery_errors':errors}
