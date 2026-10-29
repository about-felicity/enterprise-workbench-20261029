import sys,unittest,os
sys.path.insert(0,os.environ.get('GEO_TEST_CODE','/opt/monitor/geo-capture'))
from deepseek_android_login import validate_input
from scrcpy_stream import ScrcpyStream,touch_packet,key_packets
class InputTests(unittest.TestCase):
 def test_batch_order_and_protocol(self):
  kind,parts=validate_input({'type':'batch','events':[{'type':'click','x':4,'y':5},{'type':'text','text':'abc'},{'type':'key','key':'Backspace'}]})
  stream=ScrcpyStream('deepseek_test');sent=[];stream.send=sent.append;stream.input(kind,parts)
  self.assertEqual(sent[0],touch_packet(0,4,5)+touch_packet(1,4,5))
  self.assertTrue(sent[1].endswith(b'abc'));self.assertEqual(sent[2],key_packets(67))
 def test_invalid_batch_rejected_before_any_input(self):
  for events in [[],[{}]*17,[{'type':'batch','events':[]}],[None],[{'type':'click','x':720,'y':0}]]:
   with self.subTest(events=events):
    with self.assertRaises(ValueError):validate_input({'type':'batch','events':events})
if __name__=='__main__':unittest.main()
