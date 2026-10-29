"""Preserve the established Doubao receiver protocol and frozen delivery identities."""
import json
from pathlib import Path
import time

import requests
from unattended_core import DataError
from unattended_worker import atomic_json
from runtime_reliability import DeliveryGate


class DoubaoDelivery:
    def __init__(self,root,question_count,container):
        self.root=Path(root);self.question_count=question_count;self.posts={};self.done=set()
        import geo_batch_bridge
        geo_batch_bridge.CONTAINER=container
        self.envelope=geo_batch_bridge.envelope
        config=json.loads(geo_batch_bridge.RECEIVER.read_text('utf-8-sig'))
        self.url='http://127.0.0.1:'+str(config['port'])
        self.session=requests.Session();self.session.trust_env=False
        self.session.headers['Authorization']='Bearer '+config['token']
        for name in ('outbox','receipts'):(self.root/name).mkdir(exist_ok=True,mode=0o700)
        self.gate=DeliveryGate(self.root,atomic_json)

    def verify(self,receipt,item):
        analysis=receipt.get('analysis',{});payload=item['payload']
        if (receipt.get('request_id')!=item['request_id'] or receipt.get('source_device')!=item['source_device']
            or not receipt.get('save',{}).get('run_id') or analysis.get('quarantined')
            or analysis.get('answer_present') is not True or analysis.get('source_capture_complete') is not True
            or analysis.get('answer_length')!=len(payload['answerText'].strip())
            or analysis.get('source_count')!=len(payload['items'])):
            raise DataError('Processed receipt identity/body/source completeness mismatch')

    def sync(self,queue):
        processed=0;errors=[]
        rows=queue.db.execute("select task_id from tasks where state='completed' order by ordinal").fetchall()
        for row in rows:
            if row['task_id'] in self.done:processed+=1;continue
            task=dict(queue.db.execute('select * from tasks where task_id=?',(row['task_id'],)).fetchone())
            completed=queue.db.execute("select max(time) from events where event='completed' and task_id=?",(task['task_id'],)).fetchone()[0]
            item=self.envelope(task,completed,self.question_count);rid=item['request_id']
            outbox=self.root/'outbox'/(rid+'.json');receipt_path=self.root/'receipts'/(rid+'.json')
            if outbox.exists():
                if json.loads(outbox.read_text())!=item:raise DataError('Frozen delivery envelope changed')
            else:atomic_json(outbox,item)
            if receipt_path.exists():
                self.verify(json.loads(receipt_path.read_text()),item);self.done.add(task['task_id']);self.gate.complete(rid);processed+=1;continue
            if not self.gate.due(rid):
                diagnostic=self.gate.diagnostic(rid)
                if diagnostic.get('code')!='awaiting_processed':errors.append({'ordinal':task['ordinal'],**diagnostic})
                continue
            try:
                # Look for an acknowledgement before retrying the frozen item.
                # A lost POST response never creates a new capture identity.
                reply=self.session.get(self.url+'/api/v1/status/'+rid,timeout=10)
                if reply.status_code==404:state={'status':'not_found'}
                else:reply.raise_for_status();state=reply.json()
                if state.get('status')=='processed':
                    receipt=state['receipt'];self.verify(receipt,item);atomic_json(receipt_path,receipt);self.done.add(task['task_id']);self.gate.complete(rid);processed+=1
                elif state.get('error'):
                    self.gate.waiting(rid)
                    errors.append({'ordinal':task['ordinal'],'code':'receiver_processing_error','retryable':True})
                elif self.gate.may_post(rid) and state.get('status') not in ('queued','processing'):
                    response=self.session.post(self.url+'/api/v1/captures',json=item,timeout=15)
                    response.raise_for_status();self.gate.waiting(rid,posted=True)
                else:self.gate.waiting(rid)
            except requests.RequestException as error:
                errors.append({'ordinal':task['ordinal'],'kind':type(error).__name__,**self.gate.failed(rid,error)})
        return {'captured':len(rows),'geo_processed':processed,'delivery_errors':errors}
