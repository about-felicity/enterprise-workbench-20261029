import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_memory_guard import MemoryGuard,parse_sample

SAMPLE='''** MEMINFO in pid 2195 [com.larus.nova] **
 Native Heap 406144 405788 224 714 407012 533476 402349 65755
 Dalvik Heap 200359 194568 5552 146 201084 254076 JAVA 98304
 TOTAL PSS: 1152036 TOTAL RSS: 1257180
__PROPS__
256m
512m
 flags=[ HAS_CODE LARGE_HEAP ]
__CGROUP__
2085224448
4294967296
inactive_file 120807424
'''
class Runner:
    def __init__(self):self.calls=[];self.java=480000;self.pid='2195';self.failure=False
    def __call__(self,args,**kwargs):
        self.calls.append(args)
        if self.failure:raise TimeoutError('read only probe timeout')
        output=self.pid if args[-2:]==['pidof','com.larus.nova'] else SAMPLE.replace('JAVA',str(self.java))
        return SimpleNamespace(returncode=0,stdout=output)
def atomic(path,value):path.write_text(json.dumps(value))

class Tests(unittest.TestCase):
    def guard(self,tmp):
        root=Path(tmp)/'batches/run';root.mkdir(parents=True,exist_ok=True);runner=Runner();clock=[1000]
        g=MemoryGuard(root,'doubao-test','doubao2',atomic,runner=runner,clock=lambda:clock[0],policy_path=Path(tmp)/'policy.json')
        return g,runner,clock
    def high(self,g,clock):g.refresh();clock[0]+=61;g.refresh();self.assertTrue(g.metrics['pending'])
    def test_allocated_heap_and_real_heap_flag_not_pss(self):
        m=parse_sample(SAMPLE.replace('JAVA','155772'))
        self.assertEqual(m['java_alloc_kib'],155772);self.assertEqual(m['java_limit_kib'],512*1024)
        self.assertAlmostEqual(m['java_fraction'],155772/(512*1024))
        self.assertEqual(parse_sample(SAMPLE.replace('JAVA','155772').replace(' LARGE_HEAP',''))['java_limit_kib'],256*1024)
        self.assertEqual(m['container_working_bytes'],2085224448-120807424)
    def test_yuanbao_memory_probe_and_recycle_use_its_package_only_after_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);g.model='yuanbao';g.package='com.tencent.hunyuan.app.chat';g.activity=g.package+'/.biz.login.v2.HYLoginMainActivity'
            g.policy_path.write_text(json.dumps({'models':['yuanbao']}))
            def run(args,**kw):
                r.calls.append(args)
                return SimpleNamespace(returncode=0,stdout=r.pid if args[-2:]==['pidof',g.package] else SAMPLE.replace('com.larus.nova',g.package).replace('JAVA','480000'))
            g.run=run;self.high(g,c)
            self.assertIsNone(g.maintain({'state':'prepared','task_id':'original'},{'prepared':1},{'captured':1,'geo_processed':1},lambda *a:None))
            self.assertIsNone(g.maintain({'state':'pending','task_id':'next'},{},{'captured':2,'geo_processed':1},lambda *a:None))
            self.assertFalse(any('force-stop' in v for v in r.calls))
            self.assertEqual(g.maintain({'state':'pending','task_id':'next'},{},{'captured':2,'geo_processed':2},lambda *a:None)['phase'],'memory_maintenance')
            self.assertIn(['docker','exec','doubao-test','am','force-stop',g.package],r.calls)
            self.assertIn(['docker','exec','doubao-test','am','start','-W','-n',g.activity],r.calls)
    def test_one_spike_does_not_recycle_and_low_memory_clears_pressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);g.refresh();self.assertFalse(g.metrics['pending']);r.java=150000;c[0]+=61;g.refresh();self.assertFalse(g.metrics['pending'])
    def test_never_recycles_prepared_paused_or_unconfirmed_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);self.high(g,c);event=lambda *a:None
            for task,summary,delivery,kw in [({'state':'prepared','task_id':'x'},{},{'captured':1,'geo_processed':1},{}),({'state':'pending','task_id':'x'},{'prepared':1},{'captured':1,'geo_processed':1},{}),({'state':'pending','task_id':'x'},{},{'captured':2,'geo_processed':1},{}),({'state':'pending','task_id':'x'},{},{'captured':1,'geo_processed':1},{'paused':True}),({'state':'pending','task_id':'x'},{},{'captured':1,'geo_processed':1},{'stopping':True})]:
                self.assertIsNone(g.maintain(task,summary,delivery,event,**kw))
            self.assertFalse(any('force-stop' in v for v in r.calls))
    def test_confirmed_boundary_recycle_and_persistent_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);self.high(g,c);events=[]
            result=g.maintain({'state':'pending','task_id':'next'},{'completed':2},{'captured':2,'geo_processed':2},lambda *a:events.append(a))
            self.assertEqual(result['phase'],'memory_maintenance');self.assertEqual(sum('force-stop' in v for v in r.calls),1);self.assertEqual(len(events),1)
            saved=json.loads(g.path.read_text());self.assertEqual(saved['last_recycle'],c[0]);self.assertEqual(len(saved['recycles']),1)
            g=MemoryGuard(Path(tmp)/'batches/run','doubao-test','doubao2',atomic,runner=r,clock=lambda:c[0],policy_path=Path(tmp)/'policy.json')
            g.config();g.metrics={**g.metrics,'pending':'java_fraction'};c[0]+=60
            self.assertEqual(g.maintain({'state':'pending','task_id':'next'},{},{'captured':2,'geo_processed':2},lambda *a:None)['phase'],'memory_maintenance_backoff')
            self.assertEqual(sum('force-stop' in v for v in r.calls),1)
    def test_changed_process_and_probe_failure_are_not_recycled(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);self.high(g,c);r.pid='999'
            self.assertIsNone(g.maintain({'state':'pending','task_id':'next'},{},{'captured':2,'geo_processed':2},lambda *a:None));self.assertFalse(any('force-stop' in v for v in r.calls))
            r.failure=True;c[0]+=61;self.assertIn('probe_error',g.refresh())
    def test_policy_disable_prevents_old_pending_maintenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp);self.high(g,c);g.policy_path.write_text('{"models":[]}');self.assertEqual(g.refresh(),{})
            self.assertIsNone(g.maintain({'state':'pending','task_id':'next'},{},{'captured':2,'geo_processed':2},lambda *a:None));self.assertFalse(any('force-stop' in v for v in r.calls))
    def test_distinguishes_java_oom_from_lmk_using_original_process_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            g,r,c=self.guard(tmp)
            def command(args,**kw):
                if args[0]=='dumpsys':return 'ApplicationExitInfo #0: timestamp=2026-10-20 02:33:21.790 pid=2195 reason=4 (CRASH)'
                return '10-20 02:33:21.790 2195 2195 E AndroidRuntime: java.lang.OutOfMemoryError'
            g.command=command;self.assertEqual(g.exit_info(2195)['reason'],'java_heap_oom')
            g.command=lambda *a,**kw:'ApplicationExitInfo #0: timestamp=2026-10-20 02:33:21.790 pid=2195 reason=3 (LOW_MEMORY)'
            self.assertEqual(g.exit_info(2195)['reason'],'low_memory')

if __name__=='__main__':unittest.main()
