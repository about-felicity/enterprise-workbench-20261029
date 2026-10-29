import importlib.util,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('creation.candidate_materials','/tmp/formats28-materials.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Preparation(unittest.TestCase):
 def run_prepare(self, count, workflow='rewrite-v2', off=False):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'product.json').write_text(json.dumps({'name':'造型喷雾','brand':''}))
   (root/'rewrite_policy.json').write_text(json.dumps({'workflow':workflow}))
   rows=[{'sources':[{'url':'https://www.sohu.com/a/'+str(i),'article':{'status':'fetched','title':'面部抗皱喷雾' if off else '造型喷雾','text':'body'}} for i in range(count)]}]
   (root/'private_observations.jsonl').write_text(json.dumps(rows[0]))
   out=root/'private_source_analysis';out.mkdir();(out/'articles.jsonl').write_text(json.dumps(rows[0]))
   with patch('geo_source_cards.editorial_pipeline.prepare'),patch('geo_source_cards.article_fetch.ScraplingArticleFetcher'),patch('geo_source_cards.pipeline_control.ensure_running'),patch('creation.owned_sources.exclude_owned',return_value=(rows,[])),patch('geo_source_cards.article_quality.normalize',side_effect=lambda a:a),patch('geo_source_cards.daily_editorial.prepare_day',return_value={'ok':True}):
    return m.prepare(root,{'date':'2026-10-27','question':'推荐造型喷雾','max_per_category':5})
 def test_single_v2_source_can_proceed(self):self.assertEqual(self.run_prepare(1)['preparation'],'ready')
 def test_zero_stays_blocked(self):
  with self.assertRaises(m.InsufficientMaterials):self.run_prepare(0)
 def test_legacy_requirement_preserved(self):
  with self.assertRaises(m.InsufficientMaterials):self.run_prepare(1,'legacy')
 def test_off_topic_stays_blocked(self):
  with self.assertRaises(m.InsufficientMaterials):self.run_prepare(3,off=True)
if __name__=='__main__':unittest.main()

