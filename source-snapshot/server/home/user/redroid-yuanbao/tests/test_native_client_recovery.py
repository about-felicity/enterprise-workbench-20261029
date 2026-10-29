import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import frida
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_client import NativeClient

class NativeClientRecoveryTests(unittest.TestCase):
 def test_pretrace_task_missing_model_requires_durable_initial_identity(self):
  from test_initial_binding import InitialBindingTests
  fixture=InitialBindingTests();fixture.setUp()
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);binding={'task_id':'task','conversation_id':'new','server_answer_id':'local_a'}
   for suffix,value in [('binding',binding),('native',fixture.raw),('render',fixture.render),('pre-send',fixture.base)]:
    (root/('task.'+suffix+'.json')).write_text(json.dumps(value))
   r=object.__new__(NativeClient);r.root=root;r._lookup=Mock(side_effect=frida.RPCException('Error: Exact native message is missing'))
   self.assertEqual(r.lookup({'task_id':'task','wire_question':'问题'})['request_id'],'trace')
   (root/'task.render.json').unlink()
   with self.assertRaises(frida.RPCException):r.lookup({'task_id':'task','wire_question':'问题'})
 def test_missing_heap_model_with_original_trace_requests_history_without_resend(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'task.binding.json').write_text(json.dumps({'conversation_id':'cid','server_answer_id':'cid_2'}));(root/'task.native.json').write_text(json.dumps({'content':{'traceId':'trace'}}))
   r=object.__new__(NativeClient);r.root=root;r._lookup=Mock(side_effect=frida.RPCException('Error: Exact native message is missing'))
   self.assertEqual(r.lookup({'task_id':'task','request_id':'trace'})['reason'],'native_history_not_loaded')
   with self.assertRaises(frida.RPCException):r.lookup({'task_id':'task','request_id':'different'})
   r._lookup.side_effect=frida.RPCException('Different unexpected failure')
   with self.assertRaises(frida.RPCException):r.lookup({'task_id':'task','request_id':'trace'})
 def test_server_answer_readback_rejects_changed_original_trace(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);binding={'task_id':'task','conversation_id':'cid','server_answer_id':'cid_2'}
   raw={'last':{'id':'i'},'message':{'id':'i','serverId':'cid_2'},'content':{'traceId':'other','isEof':False}}
   (root/'task.binding.json').write_text(json.dumps(binding))
   r=object.__new__(NativeClient);r.root=root;r.connect=Mock();r.script=Mock()
   r.script.exports_sync.read_known.return_value=raw
   from native_core import NativeDataError
   with self.assertRaisesRegex(NativeDataError,'trace changed'):
    r.lookup({'task_id':'task','wire_question':'question','request_id':'original'})
   self.assertFalse((root/'task.native.json').exists())

 def test_render_only_server_candidate_stays_pending_until_native_model_arrives(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);binding={'task_id':'task','conversation_id':'cid','server_answer_id':'local_a'}
   raw={'last':{'id':'i'},'message':{'id':'i','serverId':'local_a'},'content':{'traceId':'trace','isEof':False}}
   (root/'task.binding.json').write_text(json.dumps(binding));(root/'task.native.json').write_text(json.dumps(raw))
   local={'kind':'markdown','value':{'v':'question','h':{'conversationId':'cid','msgId':'local_a','traceId':'trace'}}}
   real={'kind':'markdown','value':{'v':'question','h':{'conversationId':'cid','msgId':'cid_2','traceId':'trace'}}}
   r=object.__new__(NativeClient);r.root=root;r.connect=Mock();r.script=Mock()
   r.script.exports_sync.snapshot.return_value=[local,real]
   r.script.exports_sync.read_known.side_effect=[frida.RPCException('Error: Exact native message is missing'),raw]
   with patch('native_client.parse_result',return_value={'status':'pending','reason':'native_answer_fetch_failed'}):
    result=r.lookup({'task_id':'task','wire_question':'question'})
   self.assertEqual(result['reason'],'native_answer_fetch_failed')
   self.assertEqual(json.loads((root/'task.binding.json').read_text()),binding)
   self.assertFalse((root/'task.binding-promotion.json').exists())
