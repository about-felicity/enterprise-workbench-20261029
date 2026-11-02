import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'geo-monitor-deploy/server-source'))
from monitor_core.employee_assessment import _mention_summary
from monitor_core.analytics import owned_product_recommendation_summary
from monitor_core.performance import _person_result
class MentionTests(unittest.TestCase):
 def rows(self):
  return [{'date':'2026-10-01','question':'q','product':'p','brand':'b','models':{'deepseek':{'eligible_runs':3,'recommendation_runs':1,'recommendation_rate':33.3}}},
          {'date':'2026-10-02','question':'q','product':'p','brand':'b','models':{'deepseek':{'eligible_runs':7,'recommendation_runs':2,'recommendation_rate':28.6}}}]
 def test_exact_same_summary_as_geo_board(self):
  self.assertEqual(_mention_summary(self.rows()),owned_product_recommendation_summary(self.rows(),['deepseek','doubao','wenxin','yuanbao']))
  self.assertEqual(_mention_summary(self.rows())[0]['models']['deepseek']['average_daily_mention_rate'],30.95)
 def test_no_intermediate_rounding_in_new_assessment(self):
  row=_mention_summary(self.rows())[0];rule={'product':'p','question':'q','targets':{'deepseek':30}}
  new=_person_result('n','role',{'deepseek':30},[rule],{('q','p'):row},['deepseek'],round_scores=False)
  self.assertAlmostEqual(new['score'],30.95/30*100,places=9)
  self.assertEqual(new['models'][0]['items'][0]['actual_rate'],30.95)
 def test_day_mean_not_pooled_rate_and_missing_days_not_zero(self):
  rows=self.rows();rows.append({'date':'2026-10-03','question':'q','product':'p','brand':'b','models':{'deepseek':{'eligible_runs':0,'recommendation_runs':0,'recommendation_rate':0}}})
  status=_mention_summary(rows)[0]['models']['deepseek'];self.assertEqual(status['observed_days'],2);self.assertEqual(status['average_daily_mention_rate'],30.95);self.assertEqual(status['pooled_mention_rate'],30)
if __name__=='__main__':unittest.main()
