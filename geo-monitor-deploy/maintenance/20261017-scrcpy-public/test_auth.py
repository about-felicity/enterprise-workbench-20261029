import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'deepseek-deploy'),str(ROOT/'geo-monitor-deploy')]
from auth_policy import classify_ui
from deepseek_auth_monitor import record
from scrcpy_stream import touch_packet,key_packets,ScrcpyStream
from deepseek_android_login import validate_input

def xml(*texts,composer=False,dialog=False):
 from xml.sax.saxutils import escape
 nodes=''.join('<node package="com.deepseek.chat" class="android.widget.TextView" text="'+escape(t,{'"':'&quot;'})+'" />' for t in texts)
 if dialog:nodes='<node package="com.deepseek.chat" class="android.app.Dialog">'+nodes+'</node>'
 if composer:nodes='<node package="com.deepseek.chat" class="android.widget.EditText" text=""/><node package="com.deepseek.chat" text="智能搜索"/>'+nodes
 return '<hierarchy>'+nodes+'</hierarchy>'

class AuthTests(unittest.TestCase):
 def test_ready_requires_account_and_composer(self):
  self.assertEqual(classify_ui(xml('嗨！欢迎回来',composer=True),True)['status'],'ready')
  self.assertEqual(classify_ui(xml('正常页面',composer=True),False)['status'],'unknown')
  self.assertEqual(classify_ui(xml('正常页面'),True)['status'],'unknown')
 def test_login_page(self):
  self.assertEqual(classify_ui(xml('手机验证码登录','密码登录'),True)['status'],'login_required')
 def test_risk_page_and_modal_block_success(self):
  for text in ['你的账号已被封禁','当前账户已暂停使用','Your account is suspended','操作过于频繁，请稍后再试','该帐号已冻结','检测到异常请求，当前已触发风控']:
   for composer in [False,True]:
    with self.subTest(text=text,composer=composer):self.assertEqual(classify_ui(xml(text,composer=composer,dialog=True),True)['status'],'risk_blocked')
 def test_captcha_is_not_ready(self):
  self.assertEqual(classify_ui(xml('请完成人机验证',composer=True,dialog=True),True)['status'],'verification_required')
 def test_answer_discussing_bans_is_not_a_block(self):
  self.assertEqual(classify_ui(xml('账号被封禁以后，可以向平台申诉。',composer=True),True)['status'],'ready')
 def test_unrecognized_modal_is_not_silent_success(self):
  self.assertEqual(classify_ui(xml('需要先处理的提示',composer=True,dialog=True),True)['status'],'verification_required')
 def test_transport_unknown_does_not_turn_ready_into_logout(self):
  with tempfile.TemporaryDirectory() as root:
   first=record('deepseek',{'status':'ready'},root)
   second=record('deepseek',{'status':'unknown'},root)
   self.assertEqual(second['status'],'ready');self.assertEqual(second['probe_status'],'unknown')
 def test_both_accounts_and_incident_dedup_are_isolated(self):
  with tempfile.TemporaryDirectory() as root:
   first=record('deepseek',{'status':'login_required'},root)
   second=record('deepseek',{'status':'login_required'},root)
   record('deepseek2',{'status':'ready'},root)
   self.assertEqual(first['incident_id'],second['incident_id'])
   self.assertEqual(json.loads((Path(root)/'auth-monitor/deepseek.json').read_text())['status'],'login_required')
   self.assertEqual(record('deepseek',{'status':'ready'},root)['incident_id'],'')
 def test_risk_stays_blocked_on_unknown(self):
  with tempfile.TemporaryDirectory() as root:
   record('deepseek',{'status':'risk_blocked'},root)
   self.assertEqual(record('deepseek',{'status':'unknown'},root)['status'],'risk_blocked')
 def test_control_packets_match_official_layout(self):
  packet=touch_packet(0,123,456)
  self.assertEqual(len(packet),32)
  self.assertEqual(struct.unpack('>BBqiiHHHII',packet),(2,0,-2,123,456,720,1280,65535,0,0))
  self.assertEqual(len(key_packets(67)),28)
 def test_unicode_uses_scrcpy_clipboard_control(self):
  s=ScrcpyStream('deepseek');sent=[];s.send=sent.append;s.input('text','你好123')
  self.assertEqual(sent[0][:10],struct.pack('>BQB',9,0,1));self.assertTrue(sent[0].endswith('你好123'.encode()))
 def test_input_validation_bounds(self):
  self.assertEqual(validate_input({'type':'touch','action':2,'x':10,'y':20}),('touch',(2,10,20)))
  for v in [{'type':'touch','action':9,'x':1,'y':1},{'type':'click','x':720,'y':1},{'type':'text','text':''}]:
   with self.assertRaises(ValueError):validate_input(v)
 def test_timer_is_five_minutes(self):
  self.assertIn('OnUnitActiveSec=5min',(ROOT/'geo-monitor-deploy/systemd/geo-deepseek-auth-check.timer').read_text())

if __name__=='__main__':unittest.main()
