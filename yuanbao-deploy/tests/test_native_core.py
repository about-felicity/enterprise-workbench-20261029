import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_core import NativeDataError,parse_result
from delivery import envelope,verify_receipt,nontext_envelope,verify_nontext_receipt


class NativeCaptureTests(unittest.TestCase):
    def setUp(self):
        self.task={'task_id':'11111111-1111-5111-8111-111111111111','wire_question':'测试问题\n采集任务编号：11111111-1111-5111-8111-111111111111',
                   'question':'测试问题','ordinal':1,'batch':'test-batch','prepared_at':1000}
        self.binding={'conversation_id':'conv','server_answer_id':'server-answer'}
        self.source={'index':1,'docId':'doc-1','title':'原始标题','url':'https://example.test/original?q=all','quote':'原始摘要'}
        self.raw={'message':{'id':'a','serverId':'server-answer','pairId':'q','serverPairId':'server-q','speaker':{'text':'AI'},'contentCount':1,'state':{'text':'COMPLETED'}},
          'question':{'id':'q','serverId':'server-q','speaker':{'text':'HUMAN'}},
          'content':{'isEof':True,'entityCount':2,'state':{'text':'COMPLETED'},'traceId':'trace','contentId':'content'},
          'conversation':{'isBusy':False},
          'question_entities':[{'type':{'text':'TEXT'},'textEntity':{'text':self.task['wire_question']}}],
          'entities':[{'type':{'text':'SEARCH_GUIDE'},'searchEntity':{'docsJson':json.dumps([self.source],ensure_ascii=False),'docs':[{}],'title':'引用 1 篇资料作为参考'}},
                      {'type':{'text':'TEXT'},'textEntity':{'text':'完整正文\n\n最后一段[citation:1]'}}]}

    def result(self):return parse_result(self.task,self.binding,self.raw)

    def test_missing_source_title_keeps_every_source_and_marks_display_label(self):
        self.source.update(title='',web_site_name='来源站点')
        self.raw['entities'][0]['searchEntity']['docsJson']=json.dumps([self.source])
        result=self.result();source=result['sources'][0]
        self.assertEqual(result['expected_source_count'],1)
        self.assertTrue(source['title_missing']);self.assertEqual(source['original_title'],'')
        self.assertEqual(source['title'],'未提供标题（来源站点）')
        self.assertEqual(source['url'],self.source['url']);self.assertEqual(source['native_source']['title'],'')
        self.assertEqual(result['raw_source_entries'][0]['title'],'')
        self.assertEqual(result['citations'][0]['doc_id'],'doc-1')

    def test_missing_url_or_source_identity_is_still_rejected(self):
        for key in ('url','docId'):
            with self.subTest(key=key):
                source={**self.source,key:''};self.raw['entities'][0]['searchEntity']['docsJson']=json.dumps([source])
                with self.assertRaises(NativeDataError):self.result()

    def test_interrupted_idle_answer_is_original_history_pending_never_complete(self):
        self.raw['message']['state']='INTERRUPTED';self.raw['content']['state']='INTERRUPTED'
        self.raw['content']['isEof']=False
        result=self.result()
        self.assertEqual(result['reason'],'native_answer_interrupted')
        self.assertEqual(result['phase'],'awaiting_original_history')
        self.assertEqual(result['request_id'],'trace');self.assertNotIn('finished',result)
        self.raw['conversation']['isBusy']=True
        self.assertNotIn('reason',self.result())

    def test_interrupted_does_not_bypass_question_identity_validation(self):
        self.raw['message']['state']='INTERRUPTED';self.raw['content']['state']='INTERRUPTED'
        self.raw['question_entities'][0]['textEntity']['text']='另一问题'
        with self.assertRaises(NativeDataError):self.result()

    def test_local_fetch_error_is_readback_pending_not_a_success_or_missing_sources(self):
        self.binding['server_answer_id']='local_answer'
        self.raw['message']['serverId']='local_answer'
        self.raw['content']['entityCount']=1
        self.raw['entities']=[{'type':'TEXT','textEntity':{'text':'回答拉取失败，正在重试'}}]
        result=self.result()
        self.assertEqual(result['status'],'pending');self.assertEqual(result['reason'],'native_answer_fetch_failed')
        self.assertNotIn('finished',result)

    def video_fixture(self):
        self.raw['content']['entityCount']=1
        self.raw['entities']=[{'type':{'text':'TEXT'},'textEntity':{'text':'![@replace_videoBoxV2&prefix_bypass_card](https://yuanbao)'}}]
        card={'id':'bypass_card','display':'videoBoxV2','title':'相关视频','multimedias':[
            {'type':'videoBoxV2','mediaId':'native-video','title':'真实视频标题','resourceUrl':'https://example.test/native-asset',
             'ext':{'source':{'name':'作者'},'videoRecallQuery':'眼霜'}}]}
        self.raw.update(render_snapshot_final=True,render_snapshot={'h':{'conversationId':'conv','msgId':'server-answer'},
            'i':{'replacesJson':[json.dumps(card,ensure_ascii=False)]}})
        return card

    def test_complete_video_is_not_invented_as_text_or_citations(self):
        card=self.video_fixture();r=self.result()
        self.assertEqual(r['status'],'nontext_complete');self.assertEqual(r['rich_cards'],[card])
        self.assertIs(r['body_capture_complete'],False);self.assertIs(r['rich_media_capture_complete'],True)
        self.assertEqual(r['sources'],[]);self.assertIn('@replace_videoBoxV2',r['body_markdown'])

    def test_same_placeholder_keeps_main_card_and_all_streamed_video_items(self):
        card=self.video_fixture();stream=copy.deepcopy(card);stream['display']='videoBoxStream'
        stream['multimedias']=[{**copy.deepcopy(card['multimedias'][0]),'type':'videoBoxStream','mediaId':str(i)} for i in range(6)]
        self.raw['render_snapshot']['i']['replacesJson'].append(json.dumps(stream))
        result=self.result()
        self.assertEqual(result['status'],'nontext_complete')
        self.assertEqual(len(result['rich_cards']),2)
        self.assertEqual(sum(len(c['multimedias']) for c in result['rich_cards']),7)

    def test_video_requires_final_same_request_card_and_eof(self):
        self.video_fixture();self.raw['render_snapshot_final']=False
        self.assertEqual(self.result()['reason'],'final_video_card_pending')
        self.raw['render_snapshot_final']=True;self.raw['render_snapshot']['h']['conversationId']='other'
        with self.assertRaises(NativeDataError):self.result()
        self.video_fixture();self.raw['content']['isEof']=False
        self.assertEqual(self.result()['status'],'pending')

    def test_missing_or_unmatched_card_stays_unresolved(self):
        self.video_fixture();self.raw['render_snapshot']['i']['replacesJson']=[]
        self.assertEqual(self.result()['reason'],'native_video_card_pending')
        self.video_fixture();self.raw['entities'][0]['textEntity']['text']+='\n还有未取全的文字'
        self.assertEqual(self.result()['reason'],'required_sources_pending')

    def test_audit_only_video_uses_frozen_quarantine_receipt(self):
        self.video_fixture();r=self.result();item=nontext_envelope(self.task,r,1010,21)
        self.assertEqual(item['record']['web_body'],'');self.assertEqual(item['record']['capture_result'],r)
        ack={'request_id':item['request_id'],'model':'yuanbao','source_device':item['source_device'],'stored_run_id':'',
             'analysis':{'quarantined':True,'answer_present':False,'answer_length':0,'body_capture_complete':False,'source_capture_complete':False,'source_count':0}}
        verify_nontext_receipt(ack,item)
        ack['analysis']['quarantined']=False
        with self.assertRaises(NativeDataError):verify_nontext_receipt(ack,item)

    def test_video_terminal_state_keeps_original_send_and_next_question(self):
        from question_only_core import Queue,PROTOCOL
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            q=Queue(Path(tmp)/'tasks.sqlite');q.enqueue('video-test',['测试问题','下一题'],True)
            task=q.next_task();q.prepare(task['task_id'],protocol='phase-v2');q.click_attempt(task['task_id'])
            self.task=task;self.raw['question_entities'][0]['textEntity']['text']=task['wire_question']
            self.video_fixture();r={**self.result(),'first_user_turn':True,'prompt_protocol':PROTOCOL}
            q.complete_nontext(task['task_id'],r)
            self.assertEqual(q.summary(),{'completed_nontext':1,'pending':1})
            self.assertEqual(q.next_task()['question'],'下一题')
            self.assertEqual(q.db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0],1)
            q.db.close()

    def test_complete_keeps_exact_body_all_source_fields_and_reference(self):
        r=self.result()
        self.assertEqual(r['body_markdown'],'完整正文\n\n最后一段[citation:1]')
        self.assertEqual(r['raw_source_entries'],[self.source])
        self.assertEqual(r['sources'][0]['native_source'],self.source)
        self.assertEqual(r['citations'][0]['doc_id'],'doc-1')
        self.assertFalse(r['search_queries_exposed'])

    def test_eof_and_busy_are_required_even_with_complete_text(self):
        self.raw['content']['isEof']=False
        self.assertEqual(self.result()['status'],'pending')
        self.raw['content']['isEof']=True;self.raw['conversation']['isBusy']=True
        self.assertEqual(self.result()['status'],'pending')

    def test_other_question_or_pair_cannot_complete(self):
        self.raw['question_entities'][0]['textEntity']['text']='同名问题但不同任务编号'
        with self.assertRaises(NativeDataError):self.result()
        self.setUp();self.raw['message']['pairId']='other'
        with self.assertRaises(NativeDataError):self.result()

    def test_partial_entities_or_sources_cannot_complete(self):
        self.raw['content']['entityCount']=3
        self.assertEqual(self.result()['reason'],'native_entity_count_pending')
        self.setUp();self.raw['entities'][0]['searchEntity']['docs'].append({})
        self.assertEqual(self.result()['reason'],'native_source_count_pending')

    def test_unresolved_citation_and_invalid_source_are_rejected(self):
        self.raw['entities'][1]['textEntity']['text']='正文[citation:2]'
        self.assertEqual(self.result()['reason'],'citation_source_pending')
        self.setUp();self.source['url']='javascript:invalid'
        self.raw['entities'][0]['searchEntity']['docsJson']=json.dumps([self.source])
        with self.assertRaises(NativeDataError):self.result()

    def test_unknown_entity_and_multi_answer_are_rejected(self):
        self.raw['entities'][1]['type']['text']='UNSUPPORTED_CARD'
        with self.assertRaises(NativeDataError):self.result()
        self.setUp();self.raw['message']['contentCount']=2
        with self.assertRaises(NativeDataError):self.result()

    def test_frozen_envelope_identity_and_receipt_are_exact(self):
        r=self.result();item=envelope(self.task,r,1010,21)
        self.assertEqual(item,envelope(self.task,copy.deepcopy(r),1010,21))
        changed=copy.deepcopy(r);changed['sources'][0]['title']='改变标题'
        self.assertNotEqual(item['request_id'],envelope(self.task,changed,1010,21)['request_id'])
        receipt={'request_id':item['request_id'],'model':'yuanbao','source_device':item['source_device'],'stored_run_id':'run',
          'analysis':{'answer_present':True,'answer_length':len(r['body_markdown']),'source_count':1,
           'sources':[{'title':self.source['title'],'href':self.source['url']}],'body_capture_complete':True,'source_capture_complete':True}}
        verify_receipt(receipt,item)
        receipt['analysis']['source_count']=0
        with self.assertRaises(NativeDataError):verify_receipt(receipt,item)


if __name__=='__main__':unittest.main()
