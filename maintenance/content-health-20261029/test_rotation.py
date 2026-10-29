import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from creation import supplement,studio,materials
from geo_source_cards.runtime import atomic_json

class RotationTests(unittest.TestCase):
 def test_all_blocked_questions_get_turns_and_recovered_question_is_skipped(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p={'plan_id':'plan-'+'a'*32,'enabled':True,'questions':['male','female','sensitive'],'channels':['wenxin_card']}
   t={'plan':p,'daily_task_id':'test','date':'2026-10-29','jobs':{},'skipped_questions':dict.fromkeys(p['questions'],'none')}
   atomic_json(root/'days'/t['date']/(p['plan_id']+'.json'),t)
   with patch.object(studio,'ROOT',root),patch.object(studio,'plan',return_value=p),patch.object(studio,'capture_root',return_value=root/'capture'),patch.object(supplement,'policy',return_value={'enabled':True,'start_date':'2026-10-29'}),patch.object(materials,'progress',return_value=[]),patch.object(supplement.subprocess,'run') as run:
    run.return_value.returncode=0
    supplement.save(t,{'question':'male','attempt':8,'status':'checking_materials','next_at':200})
    supplement.tick(100);self.assertEqual(supplement.state(t)['status'],'waiting');run.assert_not_called()
    supplement.tick(201);self.assertEqual(supplement.state(t)['question'],'female')
    s=supplement.state(t);supplement.save(t,{**s,'status':'waiting','next_at':0});supplement.tick(202)
    self.assertEqual(supplement.state(t)['question'],'sensitive')
    s=supplement.state(t);supplement.save(t,{**s,'status':'waiting','next_at':0});supplement.tick(203)
    self.assertEqual(supplement.state(t)['question'],'male')
    t['skipped_questions'].pop('female');atomic_json(root/'days'/t['date']/(p['plan_id']+'.json'),t)
    s=supplement.state(t);supplement.save(t,{**s,'status':'waiting','next_at':0});supplement.tick(204)
    self.assertEqual(supplement.state(t)['question'],'sensitive')

if __name__=='__main__':unittest.main()
