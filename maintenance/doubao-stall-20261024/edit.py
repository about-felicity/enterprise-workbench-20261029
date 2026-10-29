from pathlib import Path
R=Path(__file__).resolve().parents[2]/'redroid-deploy'
p=R/'question_only_adapters.py';s=p.read_text('utf8')
mark='class QuestionOnlyAndroid(DoubaoAndroid):'
helper='''def stabilize_question_only_send(device,question,timeout=6,clock=time.monotonic,sleep=time.sleep):
    """Verify the exact draft and a stable send target after dismissing the IME."""
    end=clock()+timeout;last=None;consecutive=0;dismissed=False
    while True:
        xml=device.dump_hierarchy();assert_question_only_composer(xml)
        nodes=list(ET.fromstring(xml).iter('node'));prefix='com.larus.nova:id/'
        edits=[n for n in nodes if n.get('resource-id')==prefix+'input_text']
        sends=[n for n in nodes if n.get('resource-id')==prefix+'action_send']
        if len(edits)!=1 or edits[0].get('text')!=question or len(sends)!=1 or sends[0].get('enabled')=='false':
            raise DataError('Exact draft/send target changed before submit; no click dispatched')
        keyboard=any(n.get('package','').startswith('com.android.inputmethod.') or n.get('resource-id','').startswith('com.android.inputmethod.') for n in nodes)
        bounds=sends[0].get('bounds','')
        if keyboard:
            consecutive=0;last=None
            if not dismissed:device.press('back');dismissed=True
        elif re.fullmatch(r'\\[\\d+,\\d+\\]\\[\\d+,\\d+\\]',bounds):
            consecutive=consecutive+1 if bounds==last else 1;last=bounds
            if consecutive>=3:return
        if clock()>=end:raise DataError('Keyboard/send layout did not settle; no click dispatched')
        sleep(min(.4,max(0,end-clock())))


'''
assert mark in s;s=s.replace(mark,helper+mark)
s=s.replace("            assert_question_only_composer(self.device.dump_hierarchy())\n            if before_click:","            stabilize_question_only_send(self.device,question)\n            if before_click:")
p.write_text(s,encoding='utf8',newline='')
p=R/'draft_submission_recovery.py';s=p.read_text('utf8')
s=s.replace('from question_only_adapters import assert_question_only_composer','from question_only_adapters import assert_question_only_composer,stabilize_question_only_send')
s=s.replace("    if not exact_draft(xml,task['wire_question']):return None", """    question=task['wire_question']
    exact=exact_draft(xml,question)
    trailing_newline=not exact and exact_draft(xml,question+'\\n')
    if not exact and not trailing_newline:return None""")
s=s.replace("    if not state.get('first_observed') or state.get('proof')!=proof:", "    if not state.get('first_observed') or state.get('proof')!=proof:")
start=s.index('    # Hide the observed software keyboard');end=s.index('    record={**state',start)
s=s[:start]+'''    # A user pause wins before changing the draft or tapping. Controller drain
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
        if not exact_draft(device.dump_hierarchy(),question+'\\n'):return None
        # Only the single observed trailing newline is removable; never strip
        # arbitrary differences or touch a draft with any native send evidence.
        state={**state,'normalization_attempted':True,'normalization_at':now,'original_draft':question+'\\n'}
        atomic_json(marker,state)
        event(task['task_id'],'native_draft_trailing_newline_normalize_intent','Two unchanged database observations; preserve original draft; restore exact task text')
        device(resourceId=P+'input_text').set_text(question,timeout=5)
        if not exact_draft(device.dump_hierarchy(),question):return None
    if not exact_draft(device.dump_hierarchy(),question):return None
    stabilize_question_only_send(device,question)
    if user_paused() or absent_proof(before,baseline(paths,question))!=proof:return None
''' +s[end:]
p.write_text(s,encoding='utf8',newline='')
