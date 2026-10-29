import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
import requests
from geo_source_cards.deepseek_api import APIError
from .client import CreationClient

class LogicClientTests(unittest.TestCase):
 def test_uncertain_independent_review_has_own_intent_and_is_never_replayed(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);key=root/'key';key.write_text('sk-'+'x'*24)
   (root/'draft.md').write_text('# 标题\n\n前提。\n\n结论。',encoding='utf-8')
   (root/'product.json').write_text(json.dumps({'name':'甲产品','facts':[]}),encoding='utf-8')
   (root/'knowledge.json').write_text('{}')
   session=Mock();session.post.side_effect=requests.ConnectionError('test disconnect')
   client=CreationClient(key,session=session)
   for _ in range(2):
    with self.assertRaises(APIError) as error:client.review_logic(root,root/'logic-call',{'date':'2026-10-21','category':'科普类','number':1})
    self.assertTrue(error.exception.uncertain)
   self.assertEqual(session.post.call_count,1)
   state=json.loads((root/'logic-call/api_state.json').read_text());self.assertEqual(state['state'],'REQUEST_UNKNOWN')

if __name__=='__main__':unittest.main()
