import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from android_ui import PACKAGE,update_notice_close
from native_core import NativeDataError
def xml(extra='',title='元宝新版本'):
 return f'''<hierarchy><node package="{PACKAGE}" text="{title}"/><node package="{PACKAGE}" text="新版本 v2.90.10"/>
 <node package="{PACKAGE}" text="立即更新" clickable="true" bounds="[162,709][558,789]"/>
 <node package="{PACKAGE}" class="android.widget.ImageView" clickable="true" bounds="[324,861][396,933]"/>{extra}</hierarchy>'''
class UpdateNoticeTests(unittest.TestCase):
 def test_observed_optional_update_close(self):self.assertEqual(update_notice_close(xml()),[324,861,396,933])
 def test_other_dialog_is_untouched(self):self.assertIsNone(update_notice_close(xml(title='安全验证')))
 def test_duplicate_close_is_not_clicked(self):
  with self.assertRaises(NativeDataError):update_notice_close(xml(f'<node package="{PACKAGE}" class="android.widget.ImageView" clickable="true" bounds="[300,950][372,1022]"/>'))
 def test_system_navigation_is_not_a_close(self):
  self.assertEqual(update_notice_close(xml('<node package="com.android.systemui" class="android.widget.ImageView" clickable="true" bounds="[300,950][372,1022]"/>')),[324,861,396,933])
 def test_update_button_is_never_returned(self):self.assertNotEqual(update_notice_close(xml()),[162,709,558,789])
if __name__=='__main__':unittest.main()
