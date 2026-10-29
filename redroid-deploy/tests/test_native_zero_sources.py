import copy,json,tempfile,unittest,sqlite3
from pathlib import Path
from question_only_core import Queue,source_absence_verified,PROTOCOL,DataError,lookup_bound
from geo_batch_bridge import envelope

class ZeroSources(unittest.TestCase):
    def test_permission_replay_keeps_parent_and_continuation_identity_and_rejects_unproven_extra_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'native.sqlite';db=sqlite3.connect(p)
            db.execute('create table im_message(local_message_id,conversation_id,user_type,local_index,server_index,message_id,content,status)')
            q=json.dumps([{'content':{'text_block':{'text':'问题'}}}]);body=json.dumps([{'is_finish':True,'content':{'text_block':{'text':'完整回答'}}}])
            permission=[{'block_type':10066,'is_finish':True,'content':{'permission_apply_block':{'permission_data':json.dumps({'doubaoAppletName':'抖音商城','refuseInteractReplay':True,'grantingList':[{'grantingName':'aweme_login','permissionStatus':'pending'}]})}}}]
            db.executemany('insert into im_message values(?,?,?,?,?,?,?,?)',[('original','cid',1,1000,1,'q1',q,11),('permission','cid',2,2000,2,'a1',json.dumps(permission),21),('continuation','cid',1,6000,6,'q2',q,11),('answer','cid',2,7000,7,'a2',body,21)]);db.commit()
            task={'task_id':'task','wire_question':'问题','question':'问题'};binding={'database':str(p),'conversation_id':'cid','request_id':'original'}
            with self.assertRaises(DataError):lookup_bound(task,binding)
            result=lookup_bound(task,{**binding,'optional_commerce_declined_at':100})
            self.assertEqual((result['request_id'],result['answer_id']),('original','answer'));self.assertFalse(result['first_user_turn'])
            self.assertEqual(result['permission_continuation']['continuation_request_id'],'continuation');self.assertTrue(source_absence_verified(result))
            permission[0]['is_finish']=False
            permission[0]['content']['pc_event_block']=''
            data=json.loads(permission[0]['content']['permission_apply_block']['permission_data'])
            data['grantingList'][0]['permissionStatus']='refused'
            permission[0]['content']['permission_apply_block']['permission_data']=json.dumps(data)
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(permission),'permission'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,binding)
            result=lookup_bound(task,{**binding,'optional_commerce_declined_at':100})
            self.assertEqual(result['answer_id'],'answer');self.assertTrue(source_absence_verified(result))
            permission[0]['content']['pc_event_block']='unexpected event'
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(permission),'permission'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,{**binding,'optional_commerce_declined_at':100})
            permission[0]['content']['pc_event_block']=''
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps(permission),'permission'));db.commit()
            db.execute('update im_message set content=? where local_message_id=?',(json.dumps([{'content':{'text_block':{'text':'不同问题'}}}]),'continuation'));db.commit()
            with self.assertRaises(DataError):lookup_bound(task,{**binding,'optional_commerce_declined_at':100})
            db.close()
    def test_native_tip_preserves_zero_source_proof_without_weakening_schema(self):
        r=self.result();tip={'block_type':10053,'is_finish':True,'content':{'tips_block':{'type':1,'text':'AI生成提示'}}}
        r['raw_answer_blocks'].append(tip);r['body_markdown']+='\n\nAI生成提示'
        self.assertTrue(source_absence_verified(r))
        tip['content']['tips_block']['type']=2
        self.assertFalse(source_absence_verified(r))
    def result(self):
        return {'status':'complete','finished':True,'native_request_confirmed':True,
                'first_user_turn':True,'prompt_protocol':PROTOCOL,'body_capture_complete':True,
                'source_capture_complete':True,'source_availability':'not_provided','native_answer_status':21,
                'body_markdown':'完整商品推荐','sources':[],'citations':[],'search_queries':[],
                'request_id':'r','answer_id':'a','conversation_id':'c',
                'raw_answer_blocks':[{'is_finish':True,'content':{'text_block':{'text':'完整商品推荐'}},
                  'meta_info':[{'info':json.dumps({'media':[{'type':4,'applet':{'render_data':'原始商品卡片'}}]})}]}]}

    def test_completed_native_without_web_sources_keeps_raw_cards_and_single_click(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/'tasks.sqlite');q.enqueue('batch',['问题'],True);task=q.next_task()
            q.prepare(task['task_id'],protocol='phase-v2');q.click_attempt(task['task_id'])
            result={**self.result(),'task_id':task['task_id'],'wire_question':'问题'}
            self.assertTrue(source_absence_verified(result));q.complete(task['task_id'],result)
            row=dict(q.db.execute('select * from tasks').fetchone());item=envelope(row,1)
            self.assertEqual(item['payload']['items'],[])
            self.assertEqual(item['payload']['native_result']['raw_answer_blocks'],result['raw_answer_blocks'])
            self.assertEqual(q.db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0],1)
            q.db.close()

    def test_missing_unfinished_or_promised_sources_are_never_accepted(self):
        for change in ('unfinished','status','missing_raw','search','citation','body_changed','not_confirmed'):
            r=copy.deepcopy(self.result())
            if change=='unfinished':r['raw_answer_blocks'][0]['is_finish']=False
            elif change=='status':r['native_answer_status']=0
            elif change=='missing_raw':r.pop('raw_answer_blocks')
            elif change=='search':r['raw_answer_blocks'][0]['content']['search_query_result_block']={'queries':['q'],'results':[]}
            elif change=='citation':r['raw_answer_blocks'][0]['meta_info']=[{'info':json.dumps({'url':'https://source.test'})}]
            elif change=='body_changed':r['body_markdown']='截断'
            elif change=='not_confirmed':r['native_request_confirmed']=False
            with self.subTest(change=change):self.assertFalse(source_absence_verified(r))
