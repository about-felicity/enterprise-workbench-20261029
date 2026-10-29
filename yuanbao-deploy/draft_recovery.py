"""Bounded recovery of an unchanged home-screen draft; never replay bound requests."""
import json,time,sqlite3
from contextlib import closing
from pathlib import Path
from android_ui import PACKAGE,draft_matches,stable_send_button
from unbound_history import history_index
from unattended_worker import atomic_json

def recover(root,task,observed,android,reader,event,*,paused=False,stopping=False):
    root=Path(root);now=time.time();tid=task['task_id']
    if paused or stopping or task['state']!='prepared' or task.get('request_id') or observed.get('status')!='absent':return
    if now-(task.get('prepared_at') or now)<120 or task.get('capture_retries'):return
    if any((root/(tid+suffix)).exists() for suffix in ('.binding.json','.native.json')):return
    before=root/(tid+'.pre-send.json')
    if not before.exists():return
    base=json.loads(before.read_text())
    if base.get('baseline_mode')!='ids_only_with_persisted_history':return
    marker=root/(tid+'.draft-recovery.json')
    state=json.loads(marker.read_text()) if marker.exists() else {}
    if state.get('attempted') or now<state.get('next_probe',0):return
    atomic_json(marker,{**state,'next_probe':now+15})
    d=android.device;question=task['wire_question']
    current=d.app_current()
    if current.get('package')!=PACKAGE or not draft_matches(d.dump_hierarchy(),question):return
    with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
        events=[r[0] for r in db.execute('select event from events where task_id=?',(tid,))]
    if events.count('send_click_intent_committed')!=1 or any('relaunch' in e or e=='native_existing_draft_submit_intent' for e in events):return
    def absent():
        reader.connect()
        cids=set(reader.script.exports_sync.conversation_ids())
        cids.update(r['id'] for group in history_index() for r in group)
        return not (cids-set(base['conversations'])) and not reader.script.exports_sync.snapshot(question)
    if not absent():return
    if not state.get('first_observed') or state.get('pid')!=current['pid']:
        atomic_json(marker,{'first_observed':now,'pid':current['pid'],'next_probe':now+15})
        return {'phase':'verifying_existing_draft','reason':'draft_without_native_request'}
    if now-state['first_observed']<15:return
    def paused_now():return (root/'maintenance_pause.json').exists()
    if paused_now() or not draft_matches(d.dump_hierarchy(),question) or not absent():return
    # No new conversation, model, binding, or app relaunch across two probes.
    # Only the exact original text (plus one observed newline) is accepted.
    edit=d(className='android.widget.EditText',packageName=PACKAGE)
    if edit.get_text()==question+'\n':edit.set_text(question)
    button,bounds=stable_send_button(d,question)
    if paused_now() or d.app_current().get('pid')!=state['pid'] or not absent():return
    if button.info['bounds']!=bounds or edit.get_text()!=question:return
    atomic_json(marker,{**state,'attempted':True,'attempted_at':now})
    event(tid,'native_existing_draft_submit_intent','Two stable draft/native/history checks; one bounded submission, original baseline retained')
    android.tap(button)
    event(tid,'native_existing_draft_submit_returned','Await native acknowledgement; never repeat recovery tap')
    return {'phase':'awaiting_existing_draft_ack','reason':'existing_draft_submitted_once'}
