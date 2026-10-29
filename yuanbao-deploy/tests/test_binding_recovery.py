import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from binding_recovery import promote
from native_core import NativeDataError

class BindingRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.t={'task_id':'task','wire_question':'测试问题'}
  self.b={'task_id':'task','conversation_id':'cid','server_answer_id':'local_answer'}
  self.old={'message':{'id':'internal-a','serverId':'local_answer'},'question':{'id':'internal-q'},'content':{'traceId':'trace'}}
  self.raw={'message':{'id':'internal-a','serverId':'cid_2','pairId':'internal-q','serverPairId':'cid_1','serverIndex':'2','contentCount':1},'question':{'id':'internal-q','serverId':'cid_1','serverIndex':'1'},'content':{'traceId':'trace'},'question_entities':[{'type':'TEXT','textEntity':{'text':'测试问题'}}]}
  self.r={'v':'测试问题','h':{'conversationId':'cid','msgId':'cid_2','questionServerMsgId':'cid_1','traceId':'trace'}}
 def test_same_internal_pair_and_request_promotes_only_server_identity(self):
  result=promote(self.b,self.t,self.old,self.raw,self.r)
  self.assertEqual(result['server_answer_id'],'cid_2');self.assertEqual(result['native_request_id'],'trace')
  self.assertEqual(self.b['server_answer_id'],'local_answer')
 def test_different_trace_conversation_task_or_question_cannot_promote(self):
  for which,key,value in [('r','traceId','other'),('r','conversationId','other'),('r','msgId','other'),('r','questionServerMsgId','other')]:
   render=copy.deepcopy(self.r);render['h'][key]=value
   with self.assertRaises(NativeDataError):promote(self.b,self.t,self.old,self.raw,render)
  with self.assertRaises(NativeDataError):promote(self.b,{**self.t,'task_id':'other'},self.old,self.raw,self.r)
  with self.assertRaises(NativeDataError):promote(self.b,{**self.t,'wire_question':'other'},self.old,self.raw,self.r)
 def test_pair_variants_followups_and_server_to_server_replacement_forbidden(self):
  for key,value in [('id','other'),('pairId','other'),('serverPairId','other'),('serverIndex','4'),('contentCount',2),('serverId','local_second')]:
   raw=copy.deepcopy(self.raw);raw['message'][key]=value
   with self.assertRaises(NativeDataError):promote(self.b,self.t,self.old,raw,self.r)
  old=copy.deepcopy(self.old);old['message']['serverId']='remote_old'
  with self.assertRaises(NativeDataError):promote({**self.b,'server_answer_id':'remote_old'},self.t,old,self.raw,self.r)
