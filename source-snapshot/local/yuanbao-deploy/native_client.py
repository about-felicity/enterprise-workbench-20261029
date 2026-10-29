"""Pinned, read-only access to the Yuanbao App's own active chat engine."""
import json
from pathlib import Path
import subprocess
import sys

import frida

from native_core import NativeDataError, parse_result

BASE = Path('/home/user/redroid-yuanbao')
sys.path.insert(0,str(Path(__file__).parent/'tools'))
from wechat_qr_compat import validate, transport


class NativeClient:
    def __init__(self, root):
        validate()
        transport()
        self.root = root
        self.session = self.script = None
        self.pid = None

    def connect(self):
        pid = subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],text=True,timeout=15).strip()
        if len(pid.split()) != 1:raise NativeDataError('App process is changing; sending is forbidden')
        if self.session and not self.session.is_detached and self.pid == pid:return
        self.close()
        validate()
        self.session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(int(pid),realm='native')
        bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
        schema=(BASE/'tools/chat_model_schema.json').read_text()
        self.script=self.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+(Path(__file__).parent/'native_models.js').read_text())
        self.script.load()
        self.pid=pid

    def lookup(self, task):
        try:return self._lookup(task)
        except frida.RPCException as error:
            if 'Exact native message is missing' not in str(error):raise
            binding=self.root/(task['task_id']+'.binding.json');native=self.root/(task['task_id']+'.native.json')
            if not binding.exists() or not native.exists():raise
            trace=json.loads(native.read_text()).get('content',{}).get('traceId')
            if not trace or (task.get('request_id') and trace!=task['request_id']):raise
            if not task.get('request_id'):
                # Before the first successful poll the durable task may not yet
                # carry its trace; require the persisted binding, render and pair.
                from initial_binding import validate_candidate
                raw=json.loads(native.read_text());bound=json.loads(binding.read_text())
                before=self.root/(task['task_id']+'.pre-send.json');render=self.root/(task['task_id']+'.render.json')
                if bound.get('task_id')!=task['task_id'] or not before.exists() or not render.exists():raise
                validate_candidate(task,json.loads(before.read_text()),json.loads(render.read_text()),raw)
            return {'status':'pending','phase':'awaiting_original_history','reason':'native_history_not_loaded',
                    'request_id':trace,'native_request_confirmed':True}

    def _lookup(self, task):
        self.connect()
        path=self.root/(task['task_id']+'.binding.json')
        if path.exists():binding=json.loads(path.read_text())
        else:
            snapshots=self.script.exports_sync.snapshot(task['wire_question'])
            matches={}
            for row in snapshots:
                if row['kind'] != 'markdown' or row['value'].get('v') != task['wire_question']:continue
                context=row['value']['h']
                if context.get('conversationId') and context.get('msgId'):
                    matches[(context['conversationId'],context['msgId'])]=row['value']
            if not matches:return {'status':'absent'}
            if len(matches)!=1:raise NativeDataError('More than one native request matches the task')
            (cid,answer),render=next(iter(matches.items()))
            binding={'conversation_id':cid,'server_answer_id':answer,'task_id':task['task_id']}
            from unattended_worker import atomic_json
            atomic_json(path,binding)
            atomic_json(self.root/(task['task_id']+'.render.json'),render)
        native_path=self.root/(task['task_id']+'.native.json')
        previous=json.loads(native_path.read_text()) if native_path.exists() else {}
        # Keep the App's request trace and internal pair when its temporary
        # answer ID is replaced by the real server ID. No question is sent.
        snapshots=None
        if binding['server_answer_id'].startswith('local_'):
            snapshots=self.script.exports_sync.snapshot(task['wire_question'])
            candidates=[r['value'] for r in snapshots if r['kind']=='markdown'
                and r['value'].get('v')==task['wire_question']
                and r['value'].get('h',{}).get('conversationId')==binding['conversation_id']
                and r['value'].get('h',{}).get('traceId')==previous.get('content',{}).get('traceId')
                and r['value'].get('h',{}).get('msgId')
                and not r['value']['h']['msgId'].startswith('local_')]
            ids={r['h']['msgId'] for r in candidates}
            if len(ids)>1:raise NativeDataError('Multiple server answers match local placeholder')
            if len(ids)==1:
                try:raw=self.script.exports_sync.read_known(binding['conversation_id'],next(iter(ids)))
                except frida.RPCException as error:
                    if 'Exact native message is missing' not in str(error):raise
                    # Render history may already expose the real ID before its
                    # DTMP model hydrates. Keep reading the proven placeholder
                    # so bounded history reload can run; never guess an answer.
                    raw=self.script.exports_sync.read_known(binding['conversation_id'],binding['server_answer_id'])
                else:
                    from binding_recovery import promote
                    updated=promote(binding,task,previous,raw,candidates[-1])
                    from unattended_worker import atomic_json
                    audit=self.root/(task['task_id']+'.binding-promotion.json')
                    if not audit.exists():atomic_json(audit,{'previous_binding':binding,'previous_native':previous,'promoted_binding':updated,'same_request_no_resend':True})
                    atomic_json(path,updated);binding=updated
            else:raw=self.script.exports_sync.read_known(binding['conversation_id'],binding['server_answer_id'])
        else:raw=self.script.exports_sync.read_known(binding['conversation_id'],binding['server_answer_id'])
        if not raw.get('message',{}).get('id'):return {'status':'awaiting_native_history'}
        if (raw['message'].get('serverId') != binding['server_answer_id'] or
            raw['last'].get('id') != raw['message'].get('id')):
            raise NativeDataError('Current native answer differs from persisted request')
        trace=raw.get('content',{}).get('traceId')
        expected=task.get('request_id') or previous.get('content',{}).get('traceId')
        if expected and trace and trace!=expected:
            raise NativeDataError('Original native request trace changed')
        render_path=self.root/(task['task_id']+'.render.json')
        if render_path.exists():raw['render_snapshot']=json.loads(render_path.read_text())
        from unattended_worker import atomic_json
        # Persist even a failed/incomplete snapshot for later diagnosis.
        atomic_json(self.root/(task['task_id']+'.native.json'),raw)
        if raw.get('content',{}).get('isEof') and not raw.get('conversation',{}).get('isBusy'):
            # The first matching view model binds the request while it streams.
            # Freeze rich replacement/card metadata again at native EOF, rather
            # than treating that early rendering snapshot as the final answer.
            snapshots=self.script.exports_sync.snapshot(task['wire_question'])
            matching=[row['value'] for row in snapshots if row['kind']=='markdown'
                      and row['value'].get('v')==task['wire_question']
                      and row['value'].get('h',{}).get('conversationId')==binding['conversation_id']
                      and row['value'].get('h',{}).get('msgId')==binding['server_answer_id']]
            if not matching:return {'status':'pending','phase':'awaiting_complete_snapshot',
                                    'reason':'final_render_pending','request_id':raw.get('content',{}).get('traceId'),
                                    'native_request_confirmed':True}
            raw['render_snapshot']=matching[-1]
            raw['render_snapshot_final']=True
            from stored_replacements import enrich
            raw=enrich(task,binding,raw)
            from unattended_worker import atomic_json
            atomic_json(render_path,raw['render_snapshot'])
        from unattended_worker import atomic_json
        atomic_json(self.root/(task['task_id']+'.native.json'),raw)
        result=parse_result(task,binding,raw)
        return result

    def history_entries(self):
        self.connect()
        return self.script.exports_sync.history_entries()

    def close(self):
        if self.session:
            try:self.session.detach()
            except Exception:pass
        self.session=self.script=None
        self.pid=None
