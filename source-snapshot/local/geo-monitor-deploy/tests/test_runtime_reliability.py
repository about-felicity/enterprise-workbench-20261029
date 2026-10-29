import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import requests

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_reliability import DeliveryGate,CompletionFence,failure_kind


def atomic(path,value):
    path.write_text(json.dumps(value),encoding='utf-8')


class ReliabilityTests(unittest.TestCase):
    def test_status_classification_redacts_private_exception_text(self):
        for status,code,retry in [(401,'receiver_auth_required',False),(403,'receiver_auth_required',False),
            (400,'receiver_request_rejected',False),(404,'receiver_request_rejected',False),
            (413,'receiver_request_rejected',False),(429,'receiver_rate_limited',True),
            (500,'receiver_unavailable',True),(503,'receiver_unavailable',True)]:
            r=requests.Response();r.status_code=status
            info=failure_kind(requests.HTTPError('private-token',response=r))
            self.assertEqual((info['code'],info['retryable']),(code,retry))
            self.assertNotIn('private-token',json.dumps(info))

    def test_retry_after_seconds_date_and_ceiling(self):
        r=requests.Response();r.status_code=429
        for raw,expected in [('120',120),('Thu, 01 Jan 1970 00:02:00 GMT',120),('999999',3600),('invalid',0)]:
            r.headers['Retry-After']=raw
            self.assertEqual(failure_kind(requests.HTTPError(response=r),now=0)['retry_after'],expected)

    def test_backoff_survives_restart_and_resets_only_after_success(self):
        now=[100]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gate=DeliveryGate(root,atomic,lambda:now[0])
            gate.failed('frozen-request',requests.Timeout('private data'))
            self.assertFalse(gate.due('frozen-request'))
            restarted=DeliveryGate(root,atomic,lambda:now[0])
            self.assertFalse(restarted.due('frozen-request'))
            now[0]=105;self.assertTrue(restarted.due('frozen-request'))
            restarted.failed('frozen-request',requests.ConnectionError())
            self.assertEqual(restarted.states['frozen-request']['next_at'],115)
            now[0]=115;restarted.waiting('frozen-request',posted=True)
            self.assertFalse(restarted.may_post('frozen-request'))
            now[0]=120;self.assertTrue(restarted.due('frozen-request'));self.assertFalse(restarted.may_post('frozen-request'))
            restarted.complete('frozen-request');self.assertEqual(json.loads(restarted.path.read_text()),{})

    def test_short_complete_answer_is_accepted_but_pending_or_changing_never_is(self):
        now=[0];fence=CompletionFence(clock=lambda:now[0])
        result={'status':'complete','body_markdown':'是。','conversation_id':'new','sources':[{'title':'a','url':'https://a.test'}]}
        self.assertFalse(fence.ready('one',result));now[0]=3;self.assertTrue(fence.ready('one',result))
        changed=copy.deepcopy(result);changed['sources'].append({'title':'b','url':'https://b.test'})
        self.assertFalse(fence.ready('one',changed));now[0]=6;self.assertTrue(fence.ready('one',changed))
        self.assertFalse(fence.ready('one',{'status':'pending'}));self.assertFalse(fence.ready('one',changed))
        self.assertFalse(fence.ready('other',changed))

    def test_web_lost_post_response_keeps_identical_envelope_after_restart(self):
        import capture_bridge as bridge
        from test_capture_bridge import fixture,receipt
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);lane=root/'lane'
            bridge.atomic_json(root/'runtime/lan_result_receiver.json',{'port':8791,'token':'private'})
            config={'model':'baidu_ai','rounds':5,'device':'test'};row,value=fixture()
            item=bridge.envelope(row,value,config)
            delivery=bridge.Delivery(lane,config,root);delivery.session=Mock()
            delivery.session.get.return_value.json.return_value={'status':'queued'}
            delivery.session.post.side_effect=requests.Timeout('response lost')
            result=delivery.sync([row]);self.assertEqual(result['errors'][0]['code'],'receiver_network_error')
            first=next((lane/'outbox').glob('*.json')).read_bytes()
            restarted=bridge.Delivery(lane,config,root);restarted.session=Mock()
            restarted.sync([row]);restarted.session.post.assert_not_called()
            for state in restarted.gate.states.values():state['next_at']=0
            restarted.session.get.return_value.json.return_value={'status':'processed','receipt':receipt(item)}
            result=restarted.sync([row]);self.assertEqual(result['processed'],1)
            restarted.session.post.assert_not_called()
            self.assertEqual(next((lane/'outbox').glob('*.json')).read_bytes(),first)

    def test_finished_doubao_wire_and_hydrated_defaults_are_equivalent_without_mutation(self):
        now=[0];fence=CompletionFence(clock=lambda:now[0])
        card={'title':'信源','url':'https://example.com','doc_id':'doc','index':1}
        a={'status':'complete','prompt_protocol':'question-only-v1','native_answer_status':21,'body_markdown':'完整正文',
           'sources':[{**card,'native_source':copy.deepcopy(card)}],
           'raw_answer_blocks':[{'block_id':'block','is_finish':True,'patch_type':1,'content':{'text_block':{'text':'完整正文'},'search_query_result_block':{'results':[{'text_card':copy.deepcopy(card)}]}}}]}
        b=copy.deepcopy(a);block=b['raw_answer_blocks'][0];block.pop('patch_type');block['extra_info']={};block['content']['pc_event_block']=''
        block['content']['search_query_result_block']['vlm_rich_media_results']=[]
        block['content']['text_block'].update(summary='',icon_url='',icon_url_dark='')
        for c in (b['sources'][0]['native_source'],block['content']['search_query_result_block']['results'][0]['text_card']):c.update(has_image=False,summary='',original_doc_rank=0,source_type=0)
        original=copy.deepcopy(b)
        self.assertFalse(fence.ready('task',a));now[0]=3;self.assertTrue(fence.ready('task',b));self.assertEqual(b,original)
        for key,new in [('summary','有实际内容'),('url','https://changed.example'),('original_doc_rank',1)]:
            changed=copy.deepcopy(b);changed['sources'][0]['native_source'][key]=new
            self.assertFalse(fence.ready('task',changed));now[0]+=3;self.assertFalse(fence.ready('task',b));now[0]+=3;self.assertTrue(fence.ready('task',b))
        changed=copy.deepcopy(b);changed['raw_answer_blocks'][0]['content']['unknown_payload']={'value':1}
        self.assertFalse(fence.ready('task',changed))

    def test_receiver_auth_failure_blocks_next_web_model_question(self):
        import capture_bridge as bridge
        from test_capture_bridge import fixture
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bridge.atomic_json(root/'runtime/lan_result_receiver.json',{'port':8791,'token':'private'})
            config={'model':'wenxin_card','rounds':1,'device':'test'}
            delivery=bridge.Delivery(root/'lane',config,root);delivery.session=Mock()
            response=requests.Response();response.status_code=401
            delivery.session.get.side_effect=requests.HTTPError('private token',response=response)
            result=delivery.sync([fixture()[0]])
            self.assertEqual(result['processed'],0)
            self.assertFalse(result['errors'][0]['retryable'])
            self.assertEqual(result['captured'],1)
            delivery.session.post.assert_not_called()

if __name__=='__main__':unittest.main()
