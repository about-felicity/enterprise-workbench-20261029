import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import review_arbitration as r
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json
from tests.test_article_compiler import case

class ArbitrationBatchTests(unittest.TestCase):
 def data(self):
  k,p=case();return {'version':r.VERSION,'draft_sha256':'draft','evidence_sha256':r.digest({'knowledge':k,'product':p}),
   'paragraphs':[{'id':'P001','text':'可以按需求比较。'}],'knowledge':k,'product':p,'original_source_units':[],
   'proposals':[{'id':f'ISS{i}','origin':'fact','kind':'unsupported_fact','reason':'核对一般建议','paragraph_ids':['P001']} for i in range(7)]}
 def client(self,unknown=False):
  class Client:
   calls=[]
   def __init__(self):self.calls=[]
   def complete(self,message,folder,**kwargs):
    data=json.loads(message.split('资料：')[-1]);self.calls.append(data)
    if unknown and len(self.calls)==2:
     atomic_json(folder/'api_state.json',{'state':'REQUESTING'});raise APIError('request_unknown',uncertain=True)
    return {'decisions':[{'issue_id':i['id'],'classification':'general_advice','paragraph_ids':['P001'],'article_quote':'可以按需求比较。','source_ids':[],'source_quote':'','reason':'普通条件式建议，不是具体产品属性','repair':''} for i in data['proposals']]}
  return Client()
 def test_many_issues_keep_full_context_and_resume_accepted_batches_without_calls(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);data=self.data();c=self.client();out=r.batched(c,folder,data,{})
   self.assertEqual([len(v['proposals']) for v in c.calls],[3,3,1])
   self.assertTrue(all(v['paragraphs']==data['paragraphs'] and v['knowledge']==data['knowledge'] for v in c.calls))
   self.assertEqual(len(out['decisions']),7);before=len(c.calls)
   self.assertEqual(r.batched(c,folder,data,{}),out);self.assertEqual(len(c.calls),before)
   data['draft_sha256']='changed'
   with self.assertRaisesRegex(ValueError,'Stale'):r.batched(c,folder,data,{})
 def test_unknown_batch_never_replays_or_forges_final_certificate(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);data=self.data();c=self.client(unknown=True)
   with self.assertRaises(APIError):r.batched(c,folder,data,{})
   self.assertTrue((folder/'batch-000/certificate.json').exists());self.assertFalse((folder/'batch-001/certificate.json').exists())
   with self.assertRaises(APIError):r.batched(c,folder,data,{})
   self.assertEqual(len(c.calls),2)
   self.assertNotEqual(json.loads((folder/'batches.json').read_text()).get('status'),'complete')

if __name__=='__main__':unittest.main()
