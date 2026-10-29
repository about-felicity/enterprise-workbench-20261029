"""One bounded submit of an App draft after two complete absence observations.

A click intention is not an acknowledgement. This path never resubmits a local
or server request, types text, opens a new chat, or discards a native binding.
"""
import json,time,xml.etree.ElementTree as ET
from pathlib import Path
from unattended_core import DataError
from question_only_core import baseline
from question_only_adapters import assert_question_only_composer,stabilize_question_only_send
from unattended_worker import atomic_json

P='com.larus.nova:id/'


def absent_proof(before,after):
    previous={v['database']:v for v in before['databases']};current={v['database']:v for v in after['databases']}
    if not previous or previous.keys()!=current.keys():return None
    observations=[]
    for name,old in previous.items():
        new=current[name]
        if 'prior_requests' not in old or set(new['conversations'])!=set(old['conversations']):return None
        # Includes unacknowledged local messages, with no server-index filter.
        old_requests={json.dumps(v,sort_keys=True) for v in old['prior_requests']}
        new_requests={json.dumps(v,sort_keys=True) for v in new['prior_requests']}
        if old_requests!=new_requests:return None
        observations.append({'database':name,'question_fingerprints':sorted(old_requests),'conversations':sorted(old['conversations'])})
    return observations


def exact_draft(xml,question):
    try:assert_question_only_composer(xml)
    except DataError:return False
    nodes=list(ET.fromstring(xml).iter('node'))
    edits=[n for n in nodes if n.get('resource-id')==P+'input_text']
    sends=[n for n in nodes if n.get('resource-id')==P+'action_send']
    if len(edits)!=1 or edits[0].get('text')!=question or len(sends)!=1 or sends[0].get('enabled')=='false':return False
    if any(n.get('text') in {'登录','手机号登录','安全验证'} or n.get('resource-id','').startswith('com.android.permissioncontroller:') for n in nodes):return False
    return True


def recover(root,task,observed,android,paths,event,*,paused=False,stopping=False,clock=time.time,last_send_path=None,interval=0):
    if paused or stopping or task.get('state')!='prepared' or task.get('request_id') or observed.get('status')!='absent':return None
    now=clock()
    if now-(task.get('prepared_at') or now)<120:return None
    root=Path(root);stem=task['task_id']+'-attempt-'+str(task.get('capture_retries',0))
    if (root/(stem+'.binding.json')).exists():return None
    before_path=root/(stem+'.pre-send.json')
    if not before_path.is_file():return None
    marker=root/(stem+'.draft-submit-recovery.json');state=json.loads(marker.read_text()) if marker.exists() else {}
    if state.get('attempted') or now<state.get('next_probe',0):return None
    if last_send_path and Path(last_send_path).exists() and now<json.loads(Path(last_send_path).read_text())['time']+interval:return None
    # Persist the probe/backoff even when no proof can be established.
    atomic_json(marker,{**state,'next_probe':now+30})
    device=android.device
    if device.app_current().get('package')!='com.larus.nova':return None
    xml=device.dump_hierarchy()
    question=task['wire_question']
    exact=exact_draft(xml,question)
    trailing_newline=not exact and exact_draft(xml,question+'\n')
    if not exact and not trailing_newline:return None
    before=json.loads(before_path.read_text());after=baseline(paths,task['wire_question']);proof=absent_proof(before,after)
    if proof is None:return None
    if not state.get('first_observed') or state.get('proof')!=proof:
        atomic_json(marker,{'first_observed':now,'next_probe':now+10,'proof':proof,'attempted':False})
        return {'phase':'verifying_existing_draft','reason':'draft_present_request_not_observed','next_at':now+10}
    if now-state['first_observed']<10:return None
    # A user pause wins before changing the draft or tapping. Controller drain
    # markers allow only this original, independently proven unsent draft.
    def user_paused():
        pause=root/'maintenance_pause.json'
        if not pause.is_file():return False
        marker=json.loads(pause.read_text())
        return not (marker.get('source')=='daily_tasks' and marker.get('action')=='apply' and marker.get('allow_original_readback') is True)
    if user_paused():return None
    if absent_proof(before,baseline(paths,question))!=proof:return None
    if trailing_newline:
        if state.get('normalization_attempted'):return None
        if not exact_draft(device.dump_hierarchy(),question+'\n'):return None
        # Only the single observed trailing newline is removable; never strip
        # arbitrary differences or touch a draft with any native send evidence.
        state={**state,'normalization_attempted':True,'normalization_at':now,'original_draft':question+'\n'}
        atomic_json(marker,state)
        event(task['task_id'],'native_draft_trailing_newline_normalize_intent','Two unchanged database observations; preserve original draft; restore exact task text')
        device(resourceId=P+'input_text').set_text(question,timeout=5)
        if not exact_draft(device.dump_hierarchy(),question):return None
    if not exact_draft(device.dump_hierarchy(),question):return None
    stabilize_question_only_send(device,question)
    if user_paused() or absent_proof(before,baseline(paths,question))!=proof:return None
    record={**state,'attempted':True,'attempted_at':now,'request_observed':False,'question_unchanged':True}
    atomic_json(marker,record)
    if last_send_path:atomic_json(Path(last_send_path),{'time':now,'task_id':task['task_id'],'batch':task.get('batch')})
    event(task['task_id'],'native_existing_draft_submit_intent','Two stable original-baseline/SQLite/composer checks; no native request found; bounded one tap')
    android.tap(device(resourceId=P+'action_send'))
    event(task['task_id'],'native_existing_draft_submit_returned','Await original local/server acknowledgement; no further tap permitted')
    return {'phase':'awaiting_existing_draft_ack','reason':'existing_draft_submitted_once','next_at':now+3}
