import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import frida
from initial_binding import missing_exact_model,validate_candidate,select_candidate
from native_core import NativeDataError

class InitialBindingTests(unittest.TestCase):
 def setUp(self):
  self.t={'wire_question':'问题'};self.base={'conversations':['old']}
  self.render={'v':'问题','h':{'conversationId':'new','msgId':'local_a','questionServerMsgId':'local_q','traceId':'trace'}}
  self.raw={'question':{'id':'q','serverId':'local_q','pairId':'a','speaker':'HUMAN','serverIndex':1},'message':{'id':'a','serverId':'local_a','pairId':'q','serverPairId':'local_q','speaker':'AI','contentCount':1},'content':{'traceId':'trace'},'question_entities':[{'type':'TEXT','textEntity':{'text':'问题'}}]}
 def test_only_exact_missing_rpc_is_skippable(self):
  self.assertTrue(missing_exact_model(frida.RPCException('Error: Exact native message is missing\n at test')))
  self.assertFalse(missing_exact_model(RuntimeError('Exact native message is missing')))
  self.assertFalse(missing_exact_model(frida.RPCException('Error: Exact native message is ambiguous')))
 def test_local_placeholder_requires_exact_first_pair_and_trace(self):
  self.assertTrue(validate_candidate(self.t,self.base,self.render,self.raw))
  for field,value in [('pairId','other'),('serverPairId','other'),('contentCount',2)]:
   bad=copy.deepcopy(self.raw);bad['message'][field]=value
   with self.assertRaises(NativeDataError):validate_candidate(self.t,self.base,self.render,bad)
  with self.assertRaises(NativeDataError):validate_candidate({'wire_question':'wrong'},self.base,self.render,self.raw)
 def test_same_request_two_views_prefers_unique_server_answer(self):
  server=copy.deepcopy(self.render);server['h']['msgId']='server_a'
  chosen=select_candidate({('new','local_a'):self.render,('new','server_a'):server})
  self.assertEqual(list(chosen),[('new','server_a')])
 def test_different_cid_or_trace_never_collapses(self):
  bad=copy.deepcopy(self.render);bad['h']['traceId']='other'
  for matches in [{('new','local_a'):self.render,('new','server_a'):bad},{('new','local_a'):self.render,('other','server_a'):self.render}]:
   with self.assertRaises(NativeDataError):select_candidate(matches)

if __name__=='__main__':unittest.main()
