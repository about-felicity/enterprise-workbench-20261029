import copy,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stored_replacements import validate_records,enrich,cards_for
from native_core import NativeDataError,parse_result
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_native_core as helpers

class StoredReplacementTests(unittest.TestCase):
 def setUp(self):
  h=helpers.NativeCaptureTests();h.setUp();card=h.video_fixture();self.task=h.task;self.binding={**h.binding,'task_id':h.task['task_id']};self.raw=h.raw
  self.task.update(request_id='trace');self.raw['question'].update(serverIndex=1);self.raw['message'].update(serverIndex=2)
  self.raw['render_snapshot']['h']['traceId']='trace';self.raw['render_snapshot']['i']['replacesJson']=[]
  self.raw['render_snapshot']['v']=self.task['wire_question']
  self.cards=[card]
  self.messages=[{'message_id':'server-q','conversation_id':'conv','speaker':'human','message_index':1,'create_time':1000,'raw_data':json.dumps({'displayPrompt':self.task['wire_question']})},
   {'message_id':'server-answer','conversation_id':'conv','speaker':'ai','message_index':2,'create_time':1003,'raw_data':json.dumps({'id':'server-answer','conversationId':'conv','speaker':'ai','status':0,'speechesV2':[{'traceID':'trace','extra':{'replaces':self.cards}}]})}]
  self.contents=[{'conversation_id':'conv','message_id':'server-answer','content_id':'content','trace_id':'trace','extra':json.dumps({'replaces':self.cards})}]
  self.entities=[{'conversation_id':'conv','message_id':'server-answer','content_id':'content','entity_index':0,'type':'text','object_json':json.dumps({'type':'text','msg':'[](@replace=bypass_card)'})}]
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=Path(self.tmp.name)/'chat.db'
  with sqlite3.connect(self.db) as db:
   for table,rows in [('ChatMessages',self.messages),('ChatMessagesContecnt',self.contents),('ChatMessageEntities',self.entities)]:
    cols=list(rows[0]);db.execute('create table '+table+'('+','.join(cols)+')')
    db.executemany('insert into '+table+' values('+','.join('?' for _ in cols)+')',[tuple(r[k] for k in cols) for r in rows])
 def proof(self):return validate_records(self.task,self.binding,self.raw,self.messages,self.contents,self.entities)
 def test_actual_gap_video_card_pending_becomes_nontext_not_fabricated_text(self):
  self.assertEqual(parse_result(self.task,self.binding,self.raw)['reason'],'native_video_card_pending')
  original=copy.deepcopy(self.raw);result=enrich(self.task,self.binding,self.raw,paths=[self.db]);parsed=parse_result(self.task,self.binding,result)
  self.assertEqual(self.raw,original);self.assertEqual(parsed['status'],'nontext_complete');self.assertEqual(parsed['rich_cards'],self.cards)
  self.assertFalse(parsed['text_body_present']);self.assertEqual(parsed['sources'],[]);self.assertEqual(parsed['native_snapshot']['render_snapshot']['i']['replacesJson'],[])
 def test_same_immutable_snapshot_is_stable_for_completion_fence(self):
  self.assertEqual(enrich(self.task,self.binding,self.raw,paths=[self.db]),enrich(self.task,self.binding,self.raw,paths=[self.db]))
 def test_wrong_trace_content_answer_conversation_rejected(self):
  for key in ('trace_id','content_id','message_id','conversation_id'):
   old=self.contents[0][key];self.contents[0][key]='different'
   with self.assertRaises(NativeDataError):self.proof()
   self.contents[0][key]=old
 def test_wrong_question_or_send_time_is_rejected(self):
  self.messages[0]['raw_data']=json.dumps({'displayPrompt':'其他问题'})
  with self.assertRaises(NativeDataError):self.proof()
  self.messages[0]['raw_data']=json.dumps({'displayPrompt':self.task['wire_question']});self.messages[0]['create_time']=1200
  with self.assertRaises(NativeDataError):self.proof()
 def test_extra_turn_and_duplicate_content_cannot_be_selected(self):
  self.messages.append(copy.deepcopy(self.messages[0]))
  with self.assertRaises(NativeDataError):self.proof()
  self.messages.pop();self.contents.append(copy.deepcopy(self.contents[0]))
  with self.assertRaises(NativeDataError):self.proof()
 def test_raw_message_and_content_replacements_must_agree(self):
  self.contents[0]['extra']=json.dumps({'replaces':[{'id':'other'}]})
  with self.assertRaises(NativeDataError):self.proof()
 def test_unfinished_native_answer_cannot_get_stored_completion(self):
  for field,change in [('isEof',False),('state','STREAMING')]:
   raw=copy.deepcopy(self.raw);raw['content'][field]=change
   with self.assertRaises(NativeDataError):enrich(self.task,self.binding,raw,paths=[self.db])
 def test_mixed_uncollected_text_cannot_be_hidden(self):
  self.raw['entities'][0]['textEntity']['text']+='未采全的正文';self.assertEqual(enrich(self.task,self.binding,self.raw,paths=[self.db]),self.raw)
  self.raw['entities'][0]['textEntity']['text']=self.raw['entities'][0]['textEntity']['text'].replace('未采全的正文','')
  self.entities[0]['object_json']=json.dumps({'type':'text','msg':'[](@replace=bypass_card)还存在文字'})
  with self.assertRaises(NativeDataError):self.proof()
 def test_marker_and_all_card_ids_must_match(self):
  self.entities[0]['object_json']=json.dumps({'type':'text','msg':'[](@replace=other)'})
  with self.assertRaises(NativeDataError):self.proof()
 def test_metadata_not_present_remains_pending_without_fabrication(self):
  with sqlite3.connect(self.db) as db:db.execute('update ChatMessagesContecnt set extra=?',(json.dumps({'replaces':[]}),))
  self.assertNotIn('persisted_replacement_snapshot',enrich(self.task,self.binding,self.raw,paths=[self.db]))
 def test_render_trace_or_snapshot_hash_changed_rejected(self):
  proof=self.proof();native={**self.raw,'persisted_replacement_snapshot':proof};self.assertEqual(cards_for(self.task,self.binding,native),self.cards)
  proof['cards'][0]['title']='changed'
  with self.assertRaises(NativeDataError):cards_for(self.task,self.binding,native)
  self.raw['render_snapshot']['h']['traceId']='other'
  with self.assertRaises(NativeDataError):self.proof()
 def test_existing_complete_renderer_metadata_never_touches_database(self):
  self.raw['render_snapshot']['i']['replacesJson']=[json.dumps(self.cards[0])]
  with patch('stored_replacements.databases',side_effect=AssertionError('must not scan')):
   self.assertIs(enrich(self.task,self.binding,self.raw),self.raw)
 def test_client_executes_store_enrichment_after_eof_before_parsing(self):
  from native_client import NativeClient
  root=Path(self.tmp.name);(root/(self.task['task_id']+'.binding.json')).write_text(json.dumps(self.binding))
  c=object.__new__(NativeClient);c.root=root;c.connect=Mock();c.script=Mock();raw=copy.deepcopy(self.raw);raw['last']={'id':raw['message']['id']}
  c.script.exports_sync.read_known.return_value=raw;c.script.exports_sync.snapshot.return_value=[{'kind':'markdown','value':self.raw['render_snapshot']}]
  with patch('stored_replacements.databases',return_value=[self.db]):value=c.lookup(self.task)
  self.assertEqual(value['status'],'nontext_complete');self.assertTrue((root/(self.task['task_id']+'.native.json')).exists())
  self.assertNotIn('send',str(c.script.mock_calls))
 def test_database_is_read_only_and_no_http_or_ui_operations(self):
  before=self.db.read_bytes();enrich(self.task,self.binding,self.raw,paths=[self.db]);self.assertEqual(before,self.db.read_bytes())
