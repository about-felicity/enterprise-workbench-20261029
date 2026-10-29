import json
from pathlib import Path
import sys
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import all_channel_soak as soak


class Fake:
    def __init__(self):self.calls=[]
    def action(self,*args):self.calls.append(args);return {'ok':True}


class Tests(unittest.TestCase):
    def test_video_audit_keeps_full_raw_card_out_of_text_statistics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rid='a'*64
            record={'web_body':'','availability':'nontext_answer','capture_task_id':'task','batch_id':'batch',
                    'body_capture_complete':False,'source_capture_complete':False,
                    'capture_result':{'rich_cards':[{'id':'one','items':[1,2,3,4,5,6,7]}]}}
            item={'request_id':rid,'source_device':'device','record':record}
            receipt={'request_id':rid,'model':'yuanbao','source_device':'device','stored_run_id':'',
                     'analysis':{'quarantined':True,'answer_present':False,'body_capture_complete':False,'source_capture_complete':False}}
            for folder,value in [('nontext-outbox',item),('nontext-receipts',receipt)]:
                (root/folder).mkdir();(root/folder/(rid+'.json')).write_text(json.dumps(value))
            stored={'id':rid,'record':json.loads(json.dumps(record)),'run_id':''}
            with patch.object(soak,'job_root',return_value=root),patch.object(soak,'command',side_effect=lambda *args:json.dumps([stored])):
                self.assertEqual(soak.audit_nontext('yuanbao',{'batch':'unused'})['processed'],1)
                stored['record']['capture_result']['rich_cards'][0]['items']=[1]
                with self.assertRaisesRegex(ValueError,'fidelity'):soak.audit_nontext('yuanbao',{'batch':'unused'})
    def test_native_and_generic_receipts_keep_their_existing_completion_contract(self):
        item={'request_id':'r','source_device':'device','payload':{'body_capture_complete':True,
              'complete':True,'native_result':{'finished':True}}}
        receipt={'request_id':'r','source_device':'device','save':{'run_id':'run'},
                 'analysis':{'source_capture_complete':True}}
        soak.verify_receipt_protocol(receipt,item)
        item['payload']['native_result']['finished']=False
        with self.assertRaises(ValueError):soak.verify_receipt_protocol(receipt,item)
        generic={'request_id':'r','source_device':'device','record':{}}
        receipt['stored_run_id']='run'
        with self.assertRaises(ValueError):soak.verify_receipt_protocol(receipt,generic)
        receipt['analysis']['body_capture_complete']=True
        soak.verify_receipt_protocol(receipt,generic)

    def test_scoped_identity_refuses_cross_model_and_traversal(self):
        batch='geo-panel-yuanbao-20261015-170000-1234abcd'
        self.assertEqual(soak.job_root('yuanbao',batch).parent,Path('/home/user/redroid-yuanbao/batches'))
        for model,value in [('doubao1',batch),('yuanbao','../'+batch),('unknown',batch)]:
            with self.assertRaises(ValueError):soak.job_root(model,value)

    def test_deadline_does_not_pause_later_operator_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Fake();api.panel=lambda:{'models':[{'id':'yuanbao','current':{'batch':'later'}}]}
            result=soak.pause(Path(tmp),api,{'test_id':'t','jobs':{'yuanbao':{'batch':'geo-panel-yuanbao-20261015-170000-1234abcd'}}})
            self.assertEqual(result['yuanbao'],'superseded_by_operator')
            self.assertFalse(api.calls)

    def test_offline_deadline_only_marks_registered_web_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Fake()
            def offline():raise soak.requests.ConnectionError()
            api.panel=offline;batch='geo-panel-deepseek-20261015-170000-1234abcd'
            target=Path(tmp)/'owned'
            with patch.object(soak,'job_root',return_value=target):
                soak.pause(Path(tmp),api,{'test_id':'t','jobs':{'deepseek':{'batch':batch}}})
            self.assertEqual(json.loads((target/'pause.json').read_text())['source'],'t')
            self.assertFalse(api.calls)

    def test_expired_window_never_creates_any_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Fake();soak.launch(Path(tmp),api,{'deadline':0,'jobs':{}})
            self.assertFalse(api.calls)

    def test_native_queue_without_optional_failure_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
                db.executescript("create table tasks(request_id text);create table events(time real,event text,task_id text);insert into events values(10,'send_click_intent_committed','a'),(55,'send_click_intent_committed','b');")
            with patch.object(soak,'job_root',return_value=root):value=soak.queue_metrics('yuanbao',{'batch':'unused'})
            self.assertEqual(value['min_send_interval'],45)
            self.assertEqual(value['failed_attempts'],0)
            self.assertFalse(value['failed_attempts_table_present'])

    def test_retest_interval_is_scoped_but_historical_failure_stays_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
                db.executescript("create table tasks(request_id text);create table events(time real,event text,task_id text);insert into events values(10,'send_click_intent_committed','a'),(68.8,'send_click_intent_committed','b'),(130,'send_click_intent_committed','c'),(191,'send_click_intent_committed','d');")
            with patch.object(soak,'job_root',return_value=root):value=soak.queue_metrics('yuanbao',{'batch':'unused'},since=100)
            self.assertEqual(value['min_send_interval'],61)
            self.assertAlmostEqual(value['batch_min_send_interval'],58.8)
            self.assertEqual(value['send_clicks'],4)
            self.assertEqual(value['window_send_clicks'],2)


if __name__=='__main__':unittest.main()
