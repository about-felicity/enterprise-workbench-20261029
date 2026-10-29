import unittest
from datetime import datetime
from unittest.mock import patch
from creation.test_studio import StudioTests
from creation import studio,materials,runtime,search_capture

class VerificationTests(StudioTests):
 def test_verified_source_continues_without_clearing_platform_block(self):
  p=studio.plan(self.plan()['plan_id']);p['channels']=['baidu_ai','wenxin_card']
  runtime.atomic_json(studio.ROOT/'plans'/(p['plan_id']+'.json'),p)
  progress=[{'id':'baidu_ai','completed':2,'settled':2}, {'id':'wenxin_card','completed':0,'settled':0,'recovery':{'blocked':1}}]
  with patch.object(materials,'progress',return_value=progress),patch.object(materials,'records',return_value=[{'body':'existing source'}]),patch.object(runtime,'action',return_value={'job_id':'existing'}) as create:
   studio.advance(p,'2099-10-17',datetime(2099,10,17,3,tzinfo=studio.ZONE))
   self.assertEqual(create.call_count,1)
  self.assertEqual(progress[1]['recovery']['blocked'],1)

 def test_no_material_remains_waiting_without_permanent_skip(self):
  p=studio.plan(self.plan()['plan_id']);p['channels']=['baidu_ai','wenxin_card']
  runtime.atomic_json(studio.ROOT/'plans'/(p['plan_id']+'.json'),p)
  progress=[{'id':'baidu_ai','completed':2,'settled':2}, {'id':'wenxin_card','completed':0,'settled':0,'recovery':{'blocked':1}}]
  with patch.object(materials,'progress',return_value=progress),patch.object(materials,'records',return_value=[]),patch.object(runtime,'action') as create:
   studio.advance(p,'2099-10-17',datetime(2099,10,17,3,tzinfo=studio.ZONE));create.assert_not_called()
  self.assertFalse(runtime.read(studio.day_path(p['plan_id'],'2099-10-17')).get('skipped_questions'))

 def test_pending_channel_is_not_treated_as_blocked(self):
  self.assertFalse(studio.channel_verification_blocked({'id':'wenxin_card','completed':0}))
  self.assertFalse(studio.channel_verification_blocked({'id':'deepseek','recovery':{'blocked':1}}))

class ExitTests(unittest.TestCase):
 def test_verification_returns_attention_exit_without_retry(self):
  from types import SimpleNamespace
  from pathlib import Path
  from geo_source_cards import cli
  args=SimpleNamespace(model='wenxin_card',runtime_dir=Path('/opt/monitor/geo-content/test-only'))
  with patch.object(cli,'parse_args',return_value=args),patch.object(cli,'run',side_effect=RuntimeError('等待人工处理百度验证；不会因重启自动恢复')):
   self.assertEqual(search_capture.main(),77)

if __name__=='__main__':unittest.main()
