from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from question_only_core import Queue,DataError,baseline,correlate,lookup_bound,canonical_binding
from question_only_adapters import native_timestamp


def blocks(text,finished=True):
    return json.dumps([{'is_finish':finished,'content':{'text_block':{'text':text}}}],ensure_ascii=False)


class Tests(unittest.TestCase):
    def test_authorized_single_retry_cannot_trigger_unbounded_transient_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=Queue(Path(tmp)/'tasks.sqlite');q.enqueue('one-retry',['问题'])
            task=q.db.execute('select task_id from tasks').fetchone()[0]
            with q.db:
                q.db.execute('create table operator_retry_limits(task_id text primary key,max_capture_retries int)')
                q.db.execute('insert into operator_retry_limits values(?,1)',(task,))
                q.db.execute("update tasks set state='prepared',capture_retries=1")
            with self.assertRaisesRegex(DataError,'Authorized extra attempt exhausted'):
                q.schedule_transient_retry(task,{},limit=None)
            self.assertEqual(q.db.execute('select capture_retries,state from tasks').fetchone()[0],1)
            q.db.close()

    def test_optional_auth_widget_keeps_body_sources_and_raw_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path],'问题')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('q','new-cid',1,1,blocks('问题'),None,'q-server',1));db.commit()
            bound=correlate(before,'问题');task={'task_id':'task','question':'问题','wire_question':'问题'}
            data={'applet_id':'db_app_4PM0PUQ','widget_id':'aweme-auth-widget','version_tag':'v1','widget_data':'account-link UI'}
            card={'block_type':10017,'is_finish':True,'content':{'applet_block':{'render_data':json.dumps(data)}}}
            content=[{'is_finish':True,'content':{'text_block':{'text':'完整正文'},'search_query_result_block':{'queries':['查询'],'results':[{'text_card':{'index':1,'title':'参考资料','url':'https://example.com','doc_id':'doc'}}]}}},card]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('a','new-cid',2,2,json.dumps(content),None,'a-server',2));db.commit()
            result=lookup_bound(task,bound)
            self.assertEqual(result['body_markdown'],'完整正文');self.assertEqual(len(result['sources']),1)
            self.assertEqual(result['native_auxiliary_widgets'],[card]);self.assertEqual(result['raw_answer_blocks'],content)
            card['content']['pc_event_block']=''
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(content),'a'));db.commit()
            self.assertEqual(lookup_bound(task,bound)['body_markdown'],'完整正文')
            data['widget_id']='unknown-widget';card['content']['applet_block']['render_data']=json.dumps(data)
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(content),'a'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,bound)
            db.close()

    def test_native_code_block_keeps_original_content_and_rejects_unknown_output(self):
        from question_only_core import native_code_text,source_absence_verified
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);db.execute('alter table im_message add column status int');db.commit()
            before=baseline([path],'问题')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('q','new-cid',1,1,blocks('问题'),None,'q-server',1,11));db.commit()
            bound=correlate(before,'问题')
            code={'block_type':10008,'is_finish':True,'content':{'code_block':{'code':'```python\n# 本轮无需运行代码\n```','extend_fields':{},'std_out_list':[],'summary':'已完成代码运行','text':'','type':1}}}
            content=[code,{'is_finish':True,'content':{'text_block':{'text':'完整正文'}}}]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('a','new-cid',2,2,json.dumps(content),None,'a-server',2,21));db.commit()
            result=lookup_bound({'task_id':'task','question':'问题','wire_question':'问题'},bound)
            self.assertEqual(result['body_markdown'],native_code_text(code)+'\n\n完整正文')
            self.assertEqual(result['raw_answer_blocks'],content)
            self.assertTrue(source_absence_verified(result))
            code['content']['code_block']['std_out_list']=[{'unknown':'output'}]
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(content),'a'));db.commit()
            with self.assertRaises(DataError):lookup_bound({'task_id':'task','question':'问题','wire_question':'问题'},bound)
            db.close()

    def test_finished_applet_only_answer_is_recorded_without_becoming_text_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite'
            db=sqlite3.connect(path)
            db.executescript('create table im_message(local_message_id text,conversation_id text,local_index int,user_type int,content text,fts_content text,message_id text,server_index int,status int)')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('old','old-conversation',1,1,blocks('旧问题'),'旧问题','old-server',1,21));db.commit()
            before=baseline([path],'推荐一款护发精油')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('q','new-cid',1,1,blocks('推荐一款护发精油'),None,'q-server',1,21))
            card=[{'block_type':10017,'is_finish':True,'content':{'pc_event_block':'','applet_block':{'app_id':'commerce'}}}]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('a','new-cid',2,2,json.dumps(card),None,'a-server',2,21));db.commit()
            bound=correlate(before,'推荐一款护发精油')
            result=lookup_bound({'task_id':'task','question':'推荐一款护发精油','wire_question':'推荐一款护发精油'},bound)
            self.assertEqual(result['status'],'nontext_complete')
            self.assertEqual(result['native_answer_kind'],'applet_only')
            self.assertFalse(result['text_body_present'])
            self.assertEqual(result['sources'],[])
            self.assertEqual(result['answer_id'],'a')
            db.close()

    def test_only_acknowledged_terminal_empty_reply_is_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path)
            db.execute('alter table im_message add column status int');db.commit()
            before=baseline([path],'问题')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('q','new-cid',1,1,blocks('问题'),None,'q-server',1,11));db.commit()
            bound=correlate(before,'问题')
            queue=Queue(Path(tmp)/'tasks.sqlite');queue.enqueue('empty',['问题'])
            queue.db.row_factory=sqlite3.Row
            task=dict(queue.db.execute('select * from tasks').fetchone())
            queue.prepare(task['task_id'])
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?,?)',('a','new-cid',2,2,'[]',None,'a-server',2,11));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,bound)
            db.execute("update im_message set status=21,content='{}' where local_message_id='a'");db.commit()
            with self.assertRaises(DataError):lookup_bound(task,bound)
            db.execute("update im_message set content='[]' where local_message_id='a'");db.commit()
            result=lookup_bound(task,bound)
            self.assertEqual(result['native_answer_kind'],'empty_reply')
            self.assertFalse(result['body_capture_complete'])
            self.assertFalse(result['source_capture_complete'])
            queue.complete_nontext(task['task_id'],result)
            self.assertEqual(queue.db.execute('select state from tasks').fetchone()[0],'completed_nontext')
            queue.db.close();db.close()

    def test_finished_native_safety_tip_is_preserved_and_unknown_schema_still_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path],'问题')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('q','new-cid',1,1,blocks('问题'),None,'q-server',1));db.commit()
            bound=correlate(before,'问题');task={'task_id':'task','question':'问题','wire_question':'问题'}
            tip={'block_type':10053,'is_finish':True,'content':{'pc_event_block':'','tips_block':{'type':1,'text':'\n\n本回答由AI生成，仅供参考。'}}}
            body=[{'is_finish':True,'content':{'text_block':{'text':'完整回答'},'search_query_result_block':{'queries':['查询'],'results':[{'text_card':{'index':1,'title':'信源','url':'https://example.com','doc_id':'doc'}}]}}},tip]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('a','new-cid',2,2,json.dumps(body),None,'a-server',2));db.commit()
            result=lookup_bound(task,bound)
            self.assertEqual(result['body_markdown'],'完整回答\n\n'+tip['content']['tips_block']['text'])
            self.assertEqual(result['native_tips'],[tip['content']['tips_block']]);self.assertEqual(result['raw_answer_blocks'],body);self.assertEqual(len(result['sources']),1)
            tip['is_finish']=False;db.execute('update im_message set content=? where local_message_id=?',(json.dumps(body),'a'));db.commit()
            self.assertNotEqual(lookup_bound(task,bound)['status'],'complete')
            tip['is_finish']=True;tip['content']['tips_block']['type']=2
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(body),'a'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,bound)
            tip['content']['tips_block']['type']=1;tip['content']['unsupported_rich_block']={}
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(body),'a'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,bound)
            db.close()
    def test_installed_apk_unsigned_epoch_wrapper_and_milliseconds(self):
        self.assertEqual(native_timestamp({'_type':'XP.q','text':'1792058317'}),1792058317)
        self.assertEqual(native_timestamp('1792058317000'),1792058317)
        with self.assertRaises(DataError):native_timestamp({'_type':'unknown','text':'1792058317'})
    def test_repeated_questions_have_distinct_local_ids_and_identical_plain_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue=Queue(Path(tmp)/'tasks.sqlite')
            queue.enqueue('batch',['推荐一款睫毛增长液']*3,True)
            rows=queue.db.execute('select task_id,question,wire_question from tasks').fetchall()
            self.assertEqual(len({r['task_id'] for r in rows}),3)
            self.assertTrue(all(r['question']==r['wire_question']=='推荐一款睫毛增长液' for r in rows))
            queue.enqueue('batch',['推荐一款睫毛增长液']*3,True)
            self.assertEqual(queue.summary(),{'pending':3});queue.db.close()

    def test_legacy_queue_is_never_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite'
            with closing(sqlite3.connect(path)) as db:db.execute('create table tasks(x text)')
            with self.assertRaises(DataError):Queue(path)
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute('pragma table_info(tasks)').fetchone()[1],'x')

    def fixture(self,path):
        db=sqlite3.connect(path)
        db.executescript('create table im_message(local_message_id text,conversation_id text,local_index int,user_type int,content text,fts_content text,message_id text,server_index int)')
        db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('old','old-conversation',1,1,blocks('问题'),'问题','old-server',1));db.commit()
        return db

    def test_unindexed_exact_question_is_bound_to_only_the_new_conversation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path])
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('new','new-conversation',1,1,blocks('问题'),None,'request',1));db.commit()
            bound=correlate(before,'问题')
            self.assertEqual(bound['request_id'],'new');self.assertEqual(bound['conversation_id'],'new-conversation')
            task={'task_id':'local-only','question':'问题','wire_question':'问题'}
            self.assertEqual(lookup_bound(task,bound)['reason'],'native_reply_not_seen')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('stream','new-conversation',2,2,blocks('部分回答',False),None,'stream',2));db.commit()
            self.assertNotIn('reason',lookup_bound(task,bound))
            db.execute("delete from im_message where local_message_id='stream'");db.commit()
            body=[{'is_finish':True,'content':{'text_block':{'text':'正文第一段'}}},
                  {'is_finish':True,'content':{'text_block':{'text':'正文末段'},'search_query_result_block':{'queries':['检索词'],'results':[{'text_card':{'title':'标题','url':'https://example.com/source','doc_id':'doc','index':1,'extra':'完整元数据'}}]}}}]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('answer','new-conversation',2,2,json.dumps(body,ensure_ascii=False),None,'answer',2));db.commit()
            result=lookup_bound(task,bound)
            self.assertEqual(result['body_markdown'],'正文第一段\n\n正文末段')
            self.assertEqual(result['sources'][0]['native_source']['extra'],'完整元数据')
            self.assertEqual(result['raw_answer_blocks'],body);self.assertTrue(result['first_user_turn'])
            db.close()

    def test_reused_or_ambiguous_conversations_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path])
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('next','old-conversation',3,1,blocks('问题'),None,'next',3));db.commit()
            with self.assertRaises(DataError):correlate(before,'问题')
            db.execute("delete from im_message where local_message_id='next'")
            for n in ('one','two'):db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',(n,n,1,1,blocks('问题'),None,n,1))
            db.commit()
            with self.assertRaises(DataError):correlate(before,'问题')
            db.close()

    def test_historical_row_reinsert_does_not_hide_the_fresh_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path],'问题')
            old=db.execute('select * from im_message').fetchone()
            db.execute('delete from im_message')
            db.execute('insert into im_message(rowid,local_message_id,conversation_id,local_index,user_type,content,fts_content,message_id,server_index) values(?,?,?,?,?,?,?,?,?)',(100,*old))
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('new','fresh',1,1,blocks('问题'),None,'server',1));db.commit()
            self.assertEqual(correlate(before,'问题')['request_id'],'new')
            db.close()

    def test_historical_identity_does_not_allow_a_new_turn_in_old_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path],'问题')
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('second','old-conversation',3,1,blocks('问题'),None,'second-server',3));db.commit()
            with self.assertRaisesRegex(DataError,'existing conversation'):correlate(before,'问题')
            db.close()

    def test_reinsert_with_changed_message_identity_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path],'问题')
            old=list(db.execute('select * from im_message').fetchone());old[-2]='different-server'
            db.execute('delete from im_message')
            db.execute('insert into im_message(rowid,local_message_id,conversation_id,local_index,user_type,content,fts_content,message_id,server_index) values(?,?,?,?,?,?,?,?,?)',(100,*old));db.commit()
            with self.assertRaises(DataError):correlate(before,'问题')
            db.close()

    def test_server_ack_promotes_the_same_request_without_a_second_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'native.sqlite';db=self.fixture(path);before=baseline([path])
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('request','main-uuid-local',1,1,blocks('问题'),None,'',0));db.commit()
            self.assertIsNone(correlate(before,'问题'))
            binding={'database':str(path.resolve()),'conversation_id':'main-uuid-local','request_id':'request'}
            db.execute("update im_message set conversation_id='12345',message_id='server',server_index=1 where local_message_id='request'");db.commit()
            result=canonical_binding({'question':'问题'},binding,before)
            self.assertEqual(result['conversation_id'],'12345');self.assertEqual(result['request_id'],'request')
            self.assertEqual(db.execute("select count(*) from im_message where user_type=1 and conversation_id='12345'").fetchone()[0],1)
            db.close()


if __name__=='__main__':unittest.main()
