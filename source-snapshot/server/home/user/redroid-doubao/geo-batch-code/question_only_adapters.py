"""Bind exact questions to newly created native conversations without prompt markers."""
from contextlib import closing
import json
import re
from pathlib import Path
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET

from unattended_core import DataError
from unattended_worker import Android as DoubaoAndroid, atomic_json, databases, is_blank_landing
from question_only_core import baseline, correlate, lookup_bound, canonical_binding, PROTOCOL


def native_timestamp(value):
    # Current APK wraps its unsigned epoch scalar as XP.q. It is not a float.
    if isinstance(value,dict):
        if value.get('_type')!='XP.q':raise DataError('Unsupported native timestamp model')
        value=value.get('text')
    if not re.fullmatch(r'\d+(?:\.\d+)?',str(value)):raise DataError('Invalid native timestamp')
    number=float(value)
    return number/1000 if number>1e12 else number


class ConversationLedger:
    def __init__(self,path,container):
        self.path=Path(path);self.container=container
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('create table if not exists bindings(container text,cid text,task text,created real,primary key(container,cid),unique(container,task))');db.commit()

    def bind(self,cid,task):
        key=task['task_id']+':'+str(task.get('capture_retries',0))
        with closing(sqlite3.connect(self.path)) as db:
            old=db.execute('select task from bindings where container=? and cid=?',(self.container,str(cid))).fetchone()
            if old and old[0]!=key:raise DataError('A native conversation was reused for another task')
            previous=db.execute('select cid from bindings where container=? and task=?',(self.container,key)).fetchone()
            if previous and previous[0]!=str(cid):raise DataError('Task already bound to another native conversation')
            try:
                db.execute('insert or ignore into bindings values(?,?,?,?)',(self.container,str(cid),key,time.time()));db.commit()
            except sqlite3.IntegrityError:raise DataError('Task already bound to another native conversation') from None

    def promote(self,old,new,task):
        key=task['task_id']+':'+str(task.get('capture_retries',0))
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('create table if not exists promotions(container text,old_cid text,new_cid text,task text,created real)')
            existing=db.execute('select task from bindings where container=? and cid=?',(self.container,str(new))).fetchone()
            if existing and existing[0]!=key:raise DataError('Promoted native conversation already belongs to another task')
            db.execute('update bindings set cid=? where container=? and cid=? and task=?',(str(new),self.container,str(old),key))
            db.execute('insert into promotions values(?,?,?,?,?)',(self.container,str(old),str(new),key,time.time()));db.commit()


class DoubaoReader:
    def __init__(self,root,container):
        self.root=Path(root);self.container=container
        self.ledger=ConversationLedger(self.root.parent.parent/'question-only-conversations.sqlite',container)

    def paths(self,task):
        name=task['task_id']+'-attempt-'+str(task.get('capture_retries',0))
        return self.root/(name+'.pre-send.json'),self.root/(name+'.binding.json')

    def database_paths(self):return databases(self.container)

    def before_new_chat(self,task):
        before,bound=self.paths(task)
        if bound.exists():raise DataError('Native request already bound; new send forbidden')
        if task['state']=='prepared' and before.exists():return
        atomic_json(before,baseline(databases(self.container),task['question']))

    def lookup(self,task):
        before,bound=self.paths(task)
        if bound.exists():
            binding=json.loads(bound.read_text())
            current=canonical_binding(task,binding,json.loads(before.read_text()))
            if current!=binding:
                self.ledger.promote(binding['conversation_id'],current['conversation_id'],task)
                archive=bound.with_name(bound.stem+'.local-before-ack.json')
                if not archive.exists():atomic_json(archive,binding)
                atomic_json(bound,current)
            with closing(sqlite3.connect((self.root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
                declined=db.execute("select max(time) from events where task_id=? and event in ('native_optional_commerce_login_dismissed','native_optional_commerce_login_decline_intent')",(task['task_id'],)).fetchone()[0]
            return lookup_bound(task,{**current,**({'optional_commerce_declined_at':declined} if declined else {})})
        if task['state']=='pending':return {'status':'absent'}
        if not before.exists():raise DataError('Missing durable native pre-send baseline')
        binding=correlate(json.loads(before.read_text()),task['question'])
        if not binding:return {'status':'absent'}
        self.ledger.bind(binding['conversation_id'],task);atomic_json(bound,binding)
        return lookup_bound(task,binding)

    def close(self):pass


def yuanbao_reader(root):
    sys.path.insert(0,'/home/user/redroid-yuanbao')
    from native_client import NativeClient
    from native_core import NativeDataError

    class Reader(NativeClient):
        def __init__(self,root):
            super().__init__(root)
            self.ledger=ConversationLedger(root.parent.parent/'question-only-conversations.sqlite','yuanbao-hpe14-android13')

        def before_new_chat(self,task):
            path=self.root/(task['task_id']+'.pre-send.json')
            if (self.root/(task['task_id']+'.binding.json')).exists():raise NativeDataError('Native request already bound')
            if task['state']=='prepared' and path.exists():return
            self.connect();cids=set(self.script.exports_sync.conversation_ids())
            from unbound_history import history_index
            cids.update(r['id'] for group in history_index() for r in group)
            atomic_json(path,{'protocol':PROTOCOL,'created_at':time.time(),'conversations':sorted(cids),'baseline_mode':'ids_only_with_persisted_history'})

        def lookup(self,task):
            path=self.root/(task['task_id']+'.binding.json')
            if not path.exists():
                if task['state']=='pending':return {'status':'absent'}
                before=self.root/(task['task_id']+'.pre-send.json')
                if not before.exists():raise NativeDataError('Missing durable pre-send baseline')
                base=json.loads(before.read_text());self.connect()
                recovery=self.root/(task['task_id']+'.unbound-history.json')
                recovery=json.loads(recovery.read_text()) if recovery.exists() else {}
                rows=self.script.exports_sync.snapshot(task['question']);matches={}
                for row in rows:
                    value=row['value'];context=value.get('h',{})
                    cid,answer=context.get('conversationId'),context.get('msgId')
                    if row['kind']!='markdown' or value.get('v')!=task['question'] or not cid or not answer or cid in base['conversations']:continue
                    if recovery.get('candidate_conversation_id') and cid!=recovery['candidate_conversation_id']:continue
                    try:raw=self.script.exports_sync.read_known(cid,answer)
                    except Exception as error:
                        from initial_binding import missing_exact_model
                        if not missing_exact_model(error):raise
                        # A server render can precede hydration of its exact model.
                        # Continue checking other views of this same request.
                        continue
                    question=raw.get('question',{})
                    created=native_timestamp(question.get('createTime') or 0)
                    if int(question.get('serverIndex') or 0)!=1 or created<base['created_at']-10:continue
                    if recovery.get('sent_at') and created>recovery['sent_at']+120:raise NativeDataError('Recovered native request is outside the original send window')
                    from initial_binding import validate_candidate
                    if not validate_candidate(task,base,value,raw):continue
                    matches[(cid,answer)]=value
                if not matches:return {'status':'absent'}
                from initial_binding import select_candidate
                matches=select_candidate(matches)
                (cid,answer),render=next(iter(matches.items()))
                self.ledger.bind(cid,task)
                atomic_json(path,{'conversation_id':cid,'server_answer_id':answer,'task_id':task['task_id'],
                                  'prompt_protocol':PROTOCOL,'first_user_turn':True})
                atomic_json(self.root/(task['task_id']+'.render.json'),render)
            result=super().lookup(task)
            if result.get('status') in {'complete','nontext_complete'}:
                result.update(prompt_protocol=PROTOCOL,first_user_turn=True)
                if int(result['native_snapshot']['question']['serverIndex'])!=1:
                    raise NativeDataError('Native request is not the first user turn')
            return result

    return Reader(Path(root))


def assert_question_only_composer(hierarchy,*,landing=False):
    nodes=list(ET.fromstring(hierarchy).iter('node'))
    prefix='com.larus.nova:id/'
    if not any(n.get('resource-id')==prefix+'back_icon' and n.get('content-desc')=='返回' for n in nodes):
        raise DataError('Fresh question-only composer identity not verified')
    for n in nodes:
        rid=n.get('resource-id','')
        if rid in (prefix+'side_bar_merged_main_title',prefix+'larus_chat_top_left_create_new_cvs') or rid.startswith((prefix+'msg_action_',prefix+'md_')):
            raise DataError('Existing conversation or drawer remains visible; send forbidden')
    if landing and not is_blank_landing(hierarchy):raise DataError('Empty question-only landing not verified')


def optional_commerce_login(xml):
    nodes=list(ET.fromstring(xml).iter('node'));prefix='com.larus.nova:id/'
    expected={'tv_app_name':'抖音商城','tv_title':'在豆包内使用抖音商城',
              'tv_subtitle':'登录后豆包可帮你完成下单、订单查询、售后申请等操作','btn_negative':'不登录','btn_positive':'登录'}
    return all(len([n for n in nodes if n.get('resource-id')==prefix+key and n.get('text')==text])==1 for key,text in expected.items())


def dismiss_optional_commerce_login(android,before_decline=None):
    device=android.device
    if device.app_current().get('package')!='com.larus.nova' or not optional_commerce_login(device.dump_hierarchy()):return False
    if before_decline:before_decline()
    android.tap(device(resourceId='com.larus.nova:id/btn_negative',text='不登录'))
    return True


def wait_question_only_landing(device,timeout=6,*,clock=time.monotonic,sleep=time.sleep):
    """Wait through rendering only; never tap, type, relax identity, or resend."""
    end=clock()+timeout
    consecutive=0
    while True:
        try:
            assert_question_only_composer(device.dump_hierarchy(),landing=True)
        except DataError:
            consecutive=0
        else:
            consecutive+=1
            if consecutive>=2:return
        if clock()>=end:raise DataError('Empty question-only landing not stable before deadline')
        sleep(min(.5,max(0,end-clock())))


def stabilize_question_only_send(device,question,timeout=6,clock=time.monotonic,sleep=time.sleep):
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
        elif re.fullmatch(r'\[\d+,\d+\]\[\d+,\d+\]',bounds):
            consecutive=consecutive+1 if bounds==last else 1;last=bounds
            if consecutive>=3:return
        if clock()>=end:raise DataError('Keyboard/send layout did not settle; no click dispatched')
        sleep(min(.4,max(0,end-clock())))


class QuestionOnlyAndroid(DoubaoAndroid):
    def ready(self):
        self._fresh_verified=False
        self.device.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
        if self.device(resourceId='com.larus.nova:id/side_bar_merged_main_title').exists:
            self.device.press('back')
        super().ready()
        wait_question_only_landing(self.device)
        self._fresh_verified=True

    def send(self,question,before_click=None):
        if not getattr(self,'_fresh_verified',False):raise DataError('Question-only new-chat preparation missing')
        def guarded_click():
            stabilize_question_only_send(self.device,question)
            if before_click:before_click()
        try:return super().send(question,guarded_click)
        finally:self._fresh_verified=False


def android(model,serial,adb):
    if model!='yuanbao':return QuestionOnlyAndroid(serial,adb)
    sys.path.insert(0,'/home/user/redroid-yuanbao')
    from android_ui import Android
    return Android()
