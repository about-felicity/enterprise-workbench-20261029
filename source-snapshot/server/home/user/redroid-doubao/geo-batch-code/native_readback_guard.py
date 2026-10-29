"""Relaunch a missing native App for readback only; never create or send a question."""
import json,time
from pathlib import Path

class AppReadbackGuard:
    def __init__(self,root,atomic,clock=time.time,*,model='doubao1'):
        self.path=Path(root)/'native_readback_recovery.json';self.atomic=atomic;self.clock=clock
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {}
        self.package='com.tencent.hunyuan.app.chat' if model=='yuanbao' else 'com.larus.nova'
        self.activity=self.package+('/.biz.login.v2.HYLoginMainActivity' if model=='yuanbao' else '/com.larus.home.impl.alias.AliasActivity1')

    def check(self,device,task,observed,event,*,paused=False,stopping=False):
        if task.get('state')!='prepared' or observed.get('status') in ('complete','nontext_complete'):return None
        now=self.clock()
        if now<self.state.get('next_probe',0):return None
        result=device.shell(['pidof',self.package])
        output=result.output.strip()
        if result.exit_code==0 and output and all(v.isdigit() for v in output.split()):
            self.state['next_probe']=now+30;self.atomic(self.path,self.state);return None
        if result.exit_code!=1 or output:raise RuntimeError('Native App process probe failed')
        self.state['next_probe']=now+30
        attempts=[t for t in self.state.get('launches',[]) if now-t<600]
        if paused or stopping:
            self.atomic(self.path,self.state)
            return {'phase':'app_stopped_original_pending','reason':'native_app_not_running','next_at':now+30}
        if len(attempts)>=3:
            self.state['launches']=attempts;self.atomic(self.path,self.state)
            return {'phase':'app_recovery_backoff','reason':'native_app_repeated_exit','next_at':attempts[0]+600}
        attempts.append(now);self.state['launches']=attempts;self.atomic(self.path,self.state)
        event(task['task_id'],'native_app_relaunch_for_readback','process_absent; original request retained; no send')
        response=device.shell(['am','start','-W','-n',self.activity])
        if response.exit_code!=0:raise RuntimeError('Native App readback relaunch failed')
        return {'phase':'reopening_original_app','reason':'native_app_not_running','next_at':now+10}
