import copy,json,sys,unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'geo-monitor-deploy/server-source'))
from monitor_core.employee_assessment import build_assessment,coefficient,load_config,_mention_summary

class AssessmentTests(unittest.TestCase):
 def build(self,rows=(),day='2026-10-31'):
  return build_assessment(rows,month='2026-10',as_of=day,today=date(2026,10,31))
 def test_five_people_and_yellow_products_excluded_from_all_parts(self):
  data=self.build()
  self.assertEqual([p['name'] for p in data['people']],['佳佳','杨涛','小美','鑫悦','谭露'])
  self.assertEqual(data['product_count'],15);self.assertEqual(len(data['excluded_products']),9)
  owned=[p['product'] for person in data['people'] for p in person['current']['products']]
  self.assertTrue(set(owned).isdisjoint(data['excluded_products']))
  self.assertEqual([p['current']['traffic']['daily_target'] for p in data['people']],[98,243,38,28,27])
  self.assertEqual([p['current']['budget']['monthly'] for p in data['people']],[15200,27000,15500,10000,12500])
 def test_budget_is_prorated_at_actual_checkpoint_and_capped(self):
  data=self.build();j=data['people'][0]['current'];b=j['budget']
  self.assertEqual(b['latest_date'],'2026-10-27');self.assertEqual(b['actual'],9133)
  expected=(15200*27/31)/9133*100
  self.assertAlmostEqual(j['scores']['budget'],expected,places=4)
  self.assertIsNone(b['daily_expense']);self.assertTrue(j['provisional'])
  self.assertEqual(data['people'][1]['current']['scores']['budget'],150)
 def test_blank_31st_is_not_zero_and_historical_day_uses_no_future_data(self):
  latest=self.build()['people'][0]['current']
  self.assertIsNone(latest['traffic']['today_actual']);self.assertEqual(latest['traffic']['latest_date'],'2026-10-30')
  old=self.build(day='2026-10-07')['people'][0]['current']
  self.assertEqual(old['traffic']['observed_days'],7);self.assertEqual(old['budget']['latest_date'],'2026-10-07')
  self.assertEqual(old['budget']['actual'],2401)
  self.assertIsNone(self.build(day='2026-10-06')['people'][0]['current']['budget']['actual'])
 def test_values_full_score_and_missing_geo_is_not_zero_score(self):
  p=self.build()['people'][0]['current']
  self.assertEqual(p['scores']['values'],100);self.assertEqual(p['contributions']['values'],10)
  self.assertIsNone(p['scores']['mention']);self.assertIsNone(p['score'])
 def test_mention_daily_mean_caps_and_model_weights(self):
  rows=[]
  config=load_config('2026-10')
  from monitor_core.performance import OCTOBER_RULES
  for product in config['products']:
   question=next(p['question'] for p in OCTOBER_RULES if p['product']==product['product'])
   for day in ['2026-10-01','2026-10-02']:
    models={k:{'eligible_runs':1000,'recommendation_runs':int(v*30),'recommendation_rate':v*3} for k,v in product['mention_targets'].items()}
    rows.append({'date':day,'product':product['product'],'question':question,'models':models})
  data=self.build(rows,day='2026-10-02')
  for p in data['people']:
   self.assertEqual(p['current']['scores']['mention'],200)
   self.assertEqual([m['weight'] for m in p['current']['mention']['models']],[10,40,40,10] if p['name'] in {'小美','谭露'} else [30,30,30,10])
 def test_employee_specific_weights_change_actual_result_for_all_daily_snapshots(self):
  from monitor_core.performance import OCTOBER_RULES
  config=load_config('2026-10');rows=[]
  attainments={'deepseek':100,'doubao':50,'wenxin':25,'yuanbao':0}
  for product in config['products']:
   question=next(p['question'] for p in OCTOBER_RULES if p['product']==product['product'])
   models={key:{'eligible_runs':10000,'recommendation_runs':int(target*attainments[key])} for key,target in product['mention_targets'].items()}
   for day in ['2026-10-01','2026-10-02']:rows.append({'date':day,'product':product['product'],'question':question,'models':models})
  for p in self.build(rows,day='2026-10-02')['people']:
   expected=40 if p['name'] in {'小美','谭露'} else 52.5
   for snapshot in p['daily']:self.assertEqual(snapshot['scores']['mention'],expected)
 def test_valid_zero_and_missing_sample_differ(self):
  rows=[{'date':'2026-10-01','product':'道和小红瓶','question':'防脱精华液推荐','models':{'deepseek':{'eligible_runs':2,'recommendation_rate':0},'doubao':{'eligible_runs':0,'recommendation_rate':0}}}]
  p=self.build(rows,day='2026-10-01')['people'][0]['current']['mention']
  self.assertEqual(p['models'][0]['score'],0);self.assertIsNone(p['models'][1]['score'])
 def test_coefficients_exact_boundaries(self):
  for score,value in [(69.99,.5),(70,.8),(80,1),(90,1.5),(95,2),(100,2.5),(105,3),(110,3.5),(115,4),(120,5)]:
   self.assertEqual(coefficient(score),value)
 def test_invalid_month_and_future_cutoff_rejected(self):
  with self.assertRaises(ValueError):build_assessment([],month='2026-09')
  with self.assertRaises(ValueError):build_assessment([],as_of='2026-11-01',today=date(2026,10,31))

if __name__=='__main__':unittest.main()
