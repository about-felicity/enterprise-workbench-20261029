import unittest
from unittest.mock import Mock,patch
from web_collectors.collector import BrowserCollector,PreSubmissionPageError

class Tests(unittest.TestCase):
    def collector(self):
        c=BrowserCollector.__new__(BrowserCollector);c.site=Mock(name='DeepSeek');c.page=Mock();c.assert_session=Mock();c._input_state=Mock(return_value={'ok':True});c._save_failure_evidence=Mock();return c
    def test_rechecks_position_then_clicks_once(self):
        c=self.collector();q='纯问题'
        c._send_state=Mock(side_effect=[{'text':q,'button':{'x':1,'y':2}},
            {'text':q,'button':{'x':100,'y':200}},
            {'text':'','url':'https://chat.deepseek.com/a/chat/s/new','conversationText':q}])
        with patch('web_collectors.collector.time.sleep'):c._submit(q)
        c.page.click.assert_called_once_with(100,200)
        inserted=[call for call in c.page.call.call_args_list if call.args[0]=='Input.insertText']
        self.assertEqual(inserted[0].args[1],{'text':q})
    def test_changed_composer_never_sends(self):
        c=self.collector();c.submission_started=False
        c._send_state=Mock(side_effect=[{'text':'纯问题','button':{'x':1,'y':2}}, {'text':'changed','button':None}])
        with patch('web_collectors.collector.time.sleep'),self.assertRaises(PreSubmissionPageError):c._submit('纯问题')
        c.page.click.assert_not_called();self.assertFalse(c.submission_started)
if __name__=='__main__':unittest.main()
