"""Deterministic identity/completeness and private-store regression tests."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from reader import parse,DataError
from device import auth
from policy import interval_range
from deepseek_android_login import validate_input
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from android import Android
from device import LANDING_GREETINGS

class NativeTests(unittest.TestCase):
 def test_every_observed_random_landing_greeting_can_prepare_without_sending(self):
  for greeting in [*LANDING_GREETINGS,'欢迎回来，想从哪里开始？','未来新的欢迎文案']:
   with self.subTest(greeting=greeting):
    a=Android.__new__(Android);a.device=Mock()
    a.device.dump_hierarchy.return_value='<hierarchy><node package="com.deepseek.chat" content-desc="开启新对话" bounds="[652,74][697,119]"/><node package="com.deepseek.chat" class="android.widget.EditText" text="发消息"/><node package="com.deepseek.chat" class="android.widget.TextView" text="'+greeting+'"/><node package="com.deepseek.chat" class="android.widget.TextView" text="深度思考"/><node package="com.deepseek.chat" class="android.widget.TextView" text="智能搜索"/></hierarchy>'
    a.enforce_modes=Mock()
    with patch('android.auth',return_value={'status':'ready'}),patch('android.time.sleep'):
     a.ready()
    a.enforce_modes.assert_called_once();a.device.set_input_ime.assert_called_once();a.device.send_keys.assert_not_called()
 def test_existing_answer_is_not_fresh_landing(self):
  import xml.etree.ElementTree as ET
  a=Android.__new__(Android)
  root=ET.fromstring('<hierarchy><node package="com.deepseek.chat" class="android.widget.EditText" text="发消息"/><node package="com.deepseek.chat" class="android.widget.TextView" text="深度思考"/><node package="com.deepseek.chat" class="android.widget.TextView" text="智能搜索"/><node package="com.deepseek.chat" class="android.widget.TextView" text="旧问题"/><node package="com.deepseek.chat" class="android.widget.TextView" text="旧回答"/><node package="com.deepseek.chat" content-desc="开启新对话"/></hierarchy>')
  self.assertFalse(a.fresh_landing(root))
 def test_missing_native_titles_keep_all_sources_and_original_evidence(self):
  for title in ['',None,'  ']:
   with self.subTest(title=title):
    values=json.loads(self.session['messages'][1]['fragments'])
    values[0]['results']=[{'title':title,'url':'https://example.com/original'},{'title':'真实标题','url':'https://example.org/other'}]
    self.session['messages'][1]['fragments']=json.dumps(values)
    r=parse(self.task,self.session)
    self.assertEqual(len(r['sources']),2)
    self.assertEqual(r['sources'][0]['title'],'https://example.com/original')
    self.assertEqual(r['sources'][0]['native_title'],title)
    self.assertTrue(r['sources'][0]['native_title_missing'])
    self.assertEqual(r['raw_answer_blocks'][0]['results'][0]['title'],title)
    self.assertEqual(r['source_title_missing_count'],1)
    self.assertFalse(r['source_metadata_complete'])
    self.assertTrue(r['source_capture_complete'])
    self.assertEqual(r['status'],'complete')
 def test_invalid_source_urls_still_rejected(self):
  for url in ['', 'https://', 'javascript:alert(1)', None]:
   values=json.loads(self.session['messages'][1]['fragments'])
   values[0]['results']=[{'title':'','url':url}]
   self.session['messages'][1]['fragments']=json.dumps(values)
   with self.subTest(url=url),self.assertRaises(DataError):parse(self.task,self.session)
 def test_timing_contract(self):
  for value in (600,601,660,900,1140,1199,1200):
   self.assertEqual(interval_range(value),(1200,1800))
  self.assertEqual(interval_range(1500),(1500,1800))
  self.assertEqual(interval_range(1800),(1800,1800))
  for value in (599,1801,3600,True):
   with self.assertRaises(ValueError):interval_range(value)
 def setUp(self):
  self.task={'task_id':'task-1','question':'推荐一款护发精油'}
  self.session={'table':'chat_session_messages_abc','messages':[
   {'message_id':1,'parent_id':None,'role':'USER','status':'FINISHED','fragments':json.dumps([{'type':'REQUEST','id':'1','content':self.task['question']}])},
   {'message_id':2,'parent_id':1,'role':'ASSISTANT','status':'FINISHED','thinking_enabled':0,'fragments':json.dumps([
    {'type':'SEARCH','status':'FINISHED','results':[{'title':'原文','url':'https://example.com/article'}]},
    {'type':'RESPONSE','content':'完整回答','references':[]}])}]}
 def test_complete_identity(self):
  r=parse(self.task,self.session);self.assertEqual(r['request_id'],'abc:1');self.assertTrue(r['first_user_turn']);self.assertEqual(r['body_markdown'],'完整回答')
 def test_streaming_is_not_success(self):
  self.session['messages'][1]['status']='WIP';self.assertEqual(parse(self.task,self.session)['status'],'pending')
 def test_followup_rejected(self):
  self.session['messages'].append(copy.deepcopy(self.session['messages'][0]))
  with self.assertRaises(DataError):parse(self.task,self.session)
 def test_wrong_question_rejected(self):
  with self.assertRaises(DataError):parse({**self.task,'question':'别的问题'},self.session)
 def test_regeneration_rejected(self):
  self.session['messages'].append(copy.deepcopy(self.session['messages'][1]))
  with self.assertRaises(DataError):parse(self.task,self.session)
 def test_unknown_fragments_rejected(self):
  self.session['messages'][1]['fragments']='[{"type":"UNKNOWN"}]'
  with self.assertRaises(DataError):parse(self.task,self.session)
 def test_thinking_answers_rejected(self):
  self.session['messages'][1]['thinking_enabled']=1
  with self.assertRaises(DataError):parse(self.task,self.session)
 def test_missing_sources_does_not_complete(self):
  self.session['messages'][1]['fragments']='[{"type":"RESPONSE","content":"不能算成功"}]'
  self.assertEqual(parse(self.task,self.session)['status'],'pending')
 def test_android_input_bounds(self):
  self.assertEqual(validate_input({'type':'click','x':700,'y':1200}),('click',(700,1200)))
  for v in ({'type':'click','x':721,'y':0},{'type':'click','x':0,'y':1280},{'type':'text','text':'\x00'},{'type':'key','key':'Power'}):
   with self.assertRaises(ValueError):validate_input(v)
 def test_absence_of_login_is_not_ready(self):
  d=Mock();d.app_info.return_value={'versionCode':281};d.app_current.return_value={'package':'com.deepseek.chat'};d.dump_hierarchy.return_value='<hierarchy/>'
  self.assertEqual(auth(d)['status'],'unknown')

if __name__=='__main__':unittest.main()
