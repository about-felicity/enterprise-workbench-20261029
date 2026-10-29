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
            body=[{'is_finish':True,'content':{'text_block':{'text':'正文第一段'}}},
                  {'is_finish':True,'content':{'text_block':{'text':'正文末段'},'search_query_result_block':{'queries':['检索词'],'results':[{'text_card':{'title':'标题','url':'https://example.com/source','doc_id':'doc','index':1,'extra':'完整元数据'}}]}}}]
            db.execute('insert into im_message values(?,?,?,?,?,?,?,?)',('answer','new-conversation',2,2,json.dumps(body,ensure_ascii=False),None,'answer',2));db.commit()
            result=lookup_bound({'task_id':'local-only','question':'问题','wire_question':'问题'},bound)
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
