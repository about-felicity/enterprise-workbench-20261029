"""Observe memory and recycle only between confirmed tasks; no question transmission."""
import json,re,sqlite3,subprocess,time
from datetime import datetime
from pathlib import Path

DEFAULT={'models':['doubao2'],'sample_seconds':60,'java_fraction':.85,'app_pss_fraction':.65,'container_fraction':.85,'consecutive_samples':2,'cooldown_seconds':900,'restart_window_seconds':21600,'max_restarts':3,'history_days':14}
POLICY=Path('/opt/monitor/geo-capture/native_memory_policy.json')

def size_kib(value):
    m=re.fullmatch(r'(\d+)([kKmMgG]?)',value.strip())
    if not m:raise ValueError('Unsupported heap limit')
    return int(m[1])*{'':1/1024,'k':1,'m':1024,'g':1024*1024}[m[2].lower()]

def parse_sample(text,package='com.larus.nova'):
    pid=re.search(r'MEMINFO in pid (\d+) \['+re.escape(package)+r'\]',text)
    if not pid:return {'app_alive':False}
    def heap(name):
        row=re.search(r'^\s*'+name+r'\s+([\d\s]+)$',text,re.M)
        numbers=[int(v) for v in row[1].split()] if row else []
        if len(numbers)!=8:raise ValueError('Unsupported Android heap table')
        return numbers[-3],numbers[-2]
    java_size,java_alloc=heap('Dalvik Heap');_,native_alloc=heap('Native Heap')
    pss=re.search(r'TOTAL PSS:\s*(\d+)',text)
    if not pss:raise ValueError('Android PSS summary missing')
    props=text.split('__PROPS__\n',1)[1].split('__CGROUP__\n',1)
    values=props[0].splitlines();growth,maximum=size_kib(values[0]),size_kib(values[1])
    flags=next((v for v in values[2:] if re.match(r'\s*flags=\[',v)),None)
    if flags is None:raise ValueError('App heap policy could not be verified')
    limit=maximum if 'LARGE_HEAP' in flags.split() else growth
    cgroup=props[1].splitlines();current=int(cgroup[0]);maximum_bytes=int(cgroup[1])
    inactive=next(int(v.split()[1]) for v in cgroup[2:] if v.startswith('inactive_file '))
    return {'app_alive':True,'pid':int(pid[1]),'java_alloc_kib':java_alloc,'java_size_kib':java_size,'java_limit_kib':limit,'java_fraction':java_alloc/limit,'native_alloc_kib':native_alloc,'app_pss_kib':int(pss[1]),'container_bytes':current,'container_working_bytes':max(0,current-inactive),'container_limit_bytes':maximum_bytes,'container_fraction':max(0,current-inactive)/maximum_bytes,'app_pss_fraction':int(pss[1])*1024/maximum_bytes}

class MemoryGuard:
    def __init__(self,root,container,model,atomic,*,clock=time.time,runner=subprocess.run,policy_path=POLICY):
        self.container=container;self.model=model;self.atomic=atomic;self.clock=clock;self.run=runner;self.policy_path=Path(policy_path)
        self.package='com.tencent.hunyuan.app.chat' if model=='yuanbao' else 'com.larus.nova'
        self.activity=self.package+('/.biz.login.v2.HYLoginMainActivity' if model=='yuanbao' else '/com.larus.home.impl.alias.AliasActivity1')
        self.root=Path(root).parent.parent/'memory'/container;self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'state.json';self.state_error=False
        try:self.state=json.loads(self.path.read_text()) if self.path.exists() else {}
        except (OSError,ValueError):self.state={};self.state_error=True
        self.policy=dict(DEFAULT);self.metrics=self.state.get('metrics',{});self.enabled=False
    def config(self):
        p={**DEFAULT,**(json.loads(self.policy_path.read_text()) if self.policy_path.exists() else {})}
        if not isinstance(p['models'],list) or any(v not in ('doubao1','doubao2','yuanbao') for v in p['models']):raise ValueError('Invalid memory policy models')
        for k in ('java_fraction','container_fraction','app_pss_fraction'):
            if not .5<=p[k]<=.98:raise ValueError('Invalid memory policy ratio')
        if not 30<=p['sample_seconds']<=600 or not 2<=p['consecutive_samples']<=5 or not 300<=p['cooldown_seconds']<=7200 or not 1<=p['max_restarts']<=6 or not 1<=p['history_days']<=90 or not p['cooldown_seconds']<=p['restart_window_seconds']<=86400:raise ValueError('Invalid memory sampling/restart policy')
        self.policy=p;self.enabled=self.model in p['models'];return self.enabled
    def command(self,args,timeout=12):
        r=self.run(['docker','exec',self.container,*args],capture_output=True,text=True,timeout=timeout)
        if r.returncode:raise RuntimeError('Memory inspection command failed')
        return r.stdout
    def exit_info(self,pid):
        try:
            text=self.command(['dumpsys','activity','exit-info',self.package])
            block=next(v for v in text.split('ApplicationExitInfo #') if re.search(r'\bpid='+str(pid)+r'\b',v))
            reason=re.search(r'reason=\d+ \(([^)]+)\)',block)[1]
            result={'pid':pid,'reason':{'LOW_MEMORY':'low_memory','CRASH':'other_crash','USER REQUESTED':'user_requested'}.get(reason,'other_exit')}
            if reason=='CRASH':
                stamp=re.search(r'timestamp=(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)',block)[1]
                ended=datetime.fromisoformat(stamp)
                crash=self.command(['logcat','-d','-b','crash','--pid='+str(pid),'-t','200'])
                for line in crash.splitlines():
                    if 'java.lang.OutOfMemoryError' not in line:continue
                    timestamp=datetime.strptime(str(ended.year)+'-'+line[:18],'%Y-%m-%d %H:%M:%S.%f')
                    if abs((timestamp-ended).total_seconds())<=5:result['reason']='java_heap_oom';break
            return result
        except Exception:return {'pid':pid,'reason':'unclassified_exit'}
    def refresh(self,force=False):
        now=self.clock()
        try:
            if self.state_error:return {'probe_error':'MemoryStateUnavailable'}
            if not self.config():return {}
            if not force and now<self.state.get('next_sample',0):return self.metrics
            text=self.command(['sh','-c','dumpsys meminfo '+self.package+'; echo __PROPS__; getprop dalvik.vm.heapgrowthlimit; getprop dalvik.vm.heapsize; dumpsys package '+self.package+' | grep "^ *flags="; echo __CGROUP__; cat /sys/fs/cgroup/memory.current; cat /sys/fs/cgroup/memory.max; grep "^inactive_file " /sys/fs/cgroup/memory.stat'])
            m={**parse_sample(text,self.package),'sampled_at':now}
            same_pid=m.get('pid')==self.metrics.get('pid')
            if not same_pid and self.metrics.get('pid'):self.state['last_exit']=self.exit_info(self.metrics['pid'])
            if self.state.get('last_exit'):m['last_exit']=self.state['last_exit']
            reasons=[k for k in ('java_fraction','container_fraction','app_pss_fraction') if m.get(k,0)>=self.policy[k]]
            streak=(self.state.get('high_samples',0)+1 if same_pid else 1) if reasons else 0
            pending=','.join(reasons) if streak>=self.policy['consecutive_samples'] else ''
            m.update(pending=pending,high_samples=streak)
            self.metrics=m;self.state.update(metrics=m,high_samples=streak,next_sample=now+self.policy['sample_seconds'])
            self.atomic(self.path,self.state)
            db=sqlite3.connect(self.root/'samples.sqlite')
            try:
                with db:
                    db.execute('create table if not exists samples(at real primary key,metrics text not null)')
                    db.execute('insert or replace into samples values(?,?)',(now,json.dumps(m)))
                    db.execute('delete from samples where at<?',(now-self.policy['history_days']*86400,))
            finally:db.close()
            return m
        except Exception as e:
            self.metrics={**self.metrics,'probe_error':type(e).__name__};self.state['next_sample']=now+60
            return self.metrics
    def maintain(self,task,summary,delivery,event,*,paused=False,stopping=False):
        if not self.enabled or paused or stopping or not task or task['state']!='pending':return None
        if any(summary.get(k,0) for k in ('prepared','capturing','needs_attention','failed_deferred')):return None
        if delivery.get('captured')!=delivery.get('geo_processed') or delivery.get('nontext_pending') or delivery.get('delivery_errors'):return None
        m=self.metrics
        if not m.get('pending') or m.get('probe_error'):return None
        probe=self.run(['docker','exec',self.container,'pidof',self.package],capture_output=True,text=True,timeout=10)
        if probe.returncode not in (0,1):raise RuntimeError('Memory maintenance process identity check failed')
        if probe.stdout.strip().split()!=[str(m['pid'])]:
            self.metrics={**m,'pending':''};self.state.update(metrics=self.metrics,next_sample=0,high_samples=0);self.atomic(self.path,self.state);return None
        now=self.clock();launches=[v for v in self.state.get('recycles',[]) if now-v<self.policy['restart_window_seconds']]
        due=max(self.state.get('last_recycle',0)+self.policy['cooldown_seconds'],launches[0]+self.policy['restart_window_seconds'] if len(launches)>=self.policy['max_restarts'] else 0)
        if now<due:return {'phase':'memory_maintenance_backoff','next_at':due,'reason':'memory_restart_budget'}
        # Persist the attempt before affecting the process. No task state or native data is changed.
        self.state.update(last_recycle=now,recycles=launches+[now],high_samples=0,next_sample=now+30)
        self.metrics={**m,'pending':'','maintenance_at':now};self.state['metrics']=self.metrics;self.atomic(self.path,self.state)
        event(task['task_id'],'native_memory_boundary_recycle',json.dumps({'reason':m['pending'],'pid':m['pid'],'previous_results_confirmed':True}))
        self.command(['am','force-stop',self.package])
        self.command(['am','start','-W','-n',self.activity],timeout=35)
        return {'phase':'memory_maintenance','next_at':now+5,'reason':'high_memory_at_safe_boundary'}
