
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[1]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import native_soak as s


class Fake:
    def __init__(self):self.calls=[]
    def action(self,*args):self.calls.append(args);return {'ok':True,'revision':3}


class Tests(unittest.TestCase):
    def test_operation_reuses_identity_after_lost_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=Fake()
            s.operation(root,api,'new','doubao1','new',{'revision':2})
            s.operation(root,api,'new','doubao1','new',{'revision':99})
            self.assertEqual(len(api.calls),1)
            intent=s.read(root/'operations/new.json');intent.pop('result');s.atomic(root/'operations/new.json',intent)
            s.operation(root,api,'new','doubao1','new',{})
            self.assertEqual(api.calls[0],api.calls[1])

    def test_pause_never_touches_replacement_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Fake();api.panel=lambda:{'models':[{'id':'doubao1','current':{'batch':'other','state':'running'}}]}
            result=s.pause(Path(tmp),api,{'test_id':'t','jobs':{'doubao1':{'batch':'geo-panel-doubao1-20261015-100000-1234abcd'}}})
            self.assertEqual(result['doubao1'],'superseded_by_operator');self.assertFalse(api.calls)

    def test_deadline_fallback_writes_marker_only_in_own_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=Fake()
            def offline():raise s.requests.ConnectionError()
            api.panel=offline;batch='geo-panel-doubao2-20261015-100000-1234abcd'
            with patch.object(s,'NATIVE',root/'batches'):
                s.pause(root,api,{'test_id':'t','jobs':{'doubao2':{'batch':batch}}})
            self.assertTrue((root/'batches'/batch/'maintenance_pause.json').exists())

    def test_restore_keeps_operator_saved_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);api=Fake()
            s.atomic(root/'operations/doubao1-settings.json',{'result':{'revision':3}})
            api.panel=lambda:{'models':[{'id':'doubao1','revision':4}]}
            self.assertFalse(s.restore(root,api,{'original':{'doubao1':{'settings':{}}}},'doubao1'))
            self.assertFalse(api.calls)

    def test_minimum_interval_and_duplicate_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'tasks.sqlite'
            with sqlite3.connect(path) as db:
                db.executescript("create table events(time real,event text);create table tasks(request_id text);create table failed_attempts(x);insert into events values(10,'send_click_intent_committed'),(55,'send_click_intent_committed'),(102,'send_click_intent_committed');insert into tasks values('same'),('same');")
            db.close()
            result=s.summarize_queue(path)
            self.assertEqual(result['min_send_interval'],45)
            self.assertEqual(result['duplicate_native_requests'],1)

    def test_expired_window_never_starts_new_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            api=Fake()
            s.launch(Path(tmp),api,{'deadline':0,'jobs':{}})
            self.assertFalse(api.calls)

    def test_recover_committed_job_after_deadline_without_reposting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'panel').mkdir()
            path=root/'panel/control.sqlite'
            with sqlite3.connect(path) as db:
                db.executescript('create table commands(id text,model text,action text,result text,created real);')
                db.execute('insert into commands values(?,?,?,?,?)',('a'*32,'doubao1','new',json.dumps({'ok':True,'batch':'committed'}),10))
            db.close()
            s.atomic(root/'operations/doubao1-new.json',{'key':'a'*32})
            manifest={'jobs':{}}
            with patch.object(s,'BASE',root):s.recover_jobs(root,manifest)
            self.assertEqual(manifest['jobs']['doubao1']['batch'],'committed')


if __name__=='__main__':unittest.main()
