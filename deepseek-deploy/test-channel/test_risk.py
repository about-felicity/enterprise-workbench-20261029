import importlib.util,sys,unittest
from pathlib import Path
path=Path(sys.argv.pop(1)) if len(sys.argv)>1 and sys.argv[1].endswith('.py') else Path(__file__).resolve().parents[1]/'auth_policy.py'
spec=importlib.util.spec_from_file_location('risk_policy',path);policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
from xml.sax.saxutils import escape
NOTICE='因违反用户使用规范，你的账号已被禁言至 2026 年 10 月 24 日 14:04。禁言结束后，重启 App 即可恢复使用。如有疑问，请点此联系我们'
def xml(text,composer=False,dialog=False):
 nodes='<node package="com.deepseek.chat" class="android.widget.TextView" text="'+escape(text,{'"':'&quot;'})+'"/>'
 if dialog:nodes='<node package="com.deepseek.chat" class="android.app.Dialog">'+nodes+'</node>'
 if composer:nodes+='<node package="com.deepseek.chat" class="android.widget.EditText"/><node package="com.deepseek.chat" text="智能搜索"/>'
 return '<hierarchy>'+nodes+'</hierarchy>'
class RiskTests(unittest.TestCase):
 def test_actual_account_notice(self):
  for account in [False,True]:
   result=policy.classify_ui(xml(NOTICE),account)
   self.assertEqual(result['status'],'risk_blocked');self.assertEqual(result['risk_reason'],'account_muted')
   self.assertEqual(result['restriction_until_display'],'2026-10-24 14:04')
   self.assertEqual(result['restriction_until_timezone'],'unspecified')
 def test_modal_cannot_pass_with_composer(self):
  self.assertEqual(policy.classify_ui(xml(NOTICE,True,True),True)['status'],'risk_blocked')
 def test_normal_answer_quotation_not_warning(self):
  for text in ['如果账号被禁言，需要等待恢复。',NOTICE,'账号封禁与禁言是不同的处理。']:
   self.assertEqual(policy.classify_ui(xml(text,True),True)['status'],'ready')
 def test_muted_variations(self):
  for text in ['该帐号已被禁言','您的账户已被禁言至2026-10-24 14:04','Your account has been muted','你的账号暂时禁聊']:
   self.assertEqual(policy.classify_ui(xml(text),True)['status'],'risk_blocked')
 def test_bad_date_does_not_hide_block(self):
  self.assertEqual(policy.classify_ui(xml('你的账号已被禁言至2026年99月24日14:04'),True)['status'],'risk_blocked')
 def test_elapsed_date_not_automatic_success(self):
  self.assertEqual(policy.classify_ui(xml('你的账号已被禁言至2020年1月1日00:00'),True)['status'],'risk_blocked')
 def test_login_token_without_composer_not_success(self):
  self.assertEqual(policy.classify_ui(xml('欢迎回来，想从哪里开始？'),True)['status'],'unknown')
if __name__=='__main__':unittest.main()
