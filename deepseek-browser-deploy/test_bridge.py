import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,'/opt/monitor/geo-capture')
spec=importlib.util.spec_from_file_location('bridge','/opt/monitor/geo-deepseek-browser-test/browser_task_bridge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class BridgeTests(unittest.TestCase):
    def test_only_real_processed_receipt_completes_the_task(self):
        self.fixture('complete',True)
    def test_incomplete_sources_never_post_or_count_success(self):
        self.fixture('incomplete',False)
    def fixture(self,mode,success):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);batch=root/'batch';batch.mkdir();runtime=root/'runtime';runtime.mkdir()
            (runtime/'receiver.json').write_text(json.dumps({'token':'fixture-not-a-real-token','port':1}))
            (root/'data').mkdir()
            result={'run_id':'r','round':1,'prompt':'问题','web_body':'完整正文','status':'success',
                    'source_capture_complete':success,'sources':[{'title':'来源','url':'https://example.test'}],
                    'expected_source_count':1 if success else 2,'finished_at':'2026-10-19T11:00:00+08:00'}
            (root/'data/deepseek_results.jsonl').write_text(json.dumps(result)+'\n')
            (root/'state.json').write_text(json.dumps({'assignment':{'batch':'fixture'},'plugin_job':{'id':'r','state':'completed','cursor':1}}))
            session=Mock();session.headers={}
            def get(url,**_):
                rid=url.rsplit('/',1)[-1];reply=Mock();reply.json.return_value={'status':'processed','receipt':{
                    'request_id':rid,'source_device':'deepseek-browser-extension','stored_run_id':'actual-receipt-fixture',
                    'analysis':{'answer_length':4,'source_count':1,'source_capture_complete':True}}};return reply
            session.get.side_effect=get
            def remap(value):
                text=str(value)
                if text=='/home/user/redroid-deepseek-account2/batches':return root
                if text=='/opt/monitor/runtime/lan_result_receiver.json':return runtime/'receiver.json'
                return Path(value)
            (root/'fixture').mkdir()
            with patch.object(m,'ROOT',root),patch.object(m,'Path',side_effect=remap),patch.object(m,'command',side_effect=[{'ok':True,'job':{'id':'r'}},{'job':{'id':'r','state':'running'}}]),patch.object(m,'probe',return_value={'status':'ready'}),patch.object(m.requests,'Session',return_value=session):
                code=m.run({'batch':'fixture','questions':['问题'],'rounds':1})
            health=json.loads((root/'fixture/bridge_health.json').read_text())
            self.assertEqual(code,0 if success else 2)
            self.assertEqual(health['geo_processed'],1 if success else 0)
            session.post.assert_not_called()

unittest.main()
