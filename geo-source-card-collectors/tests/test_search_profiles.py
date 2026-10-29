import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from geo_source_cards.search_profiles import profile_for_search
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards import cli
from wenxin_monitor.controller import WenxinWebCollector

class SearchProfileTests(unittest.TestCase):
 def test_creation_profiles_persist_per_plan_and_channel_without_old_answers(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'plan-test'
   def lane(day,model):
    d=root/'days'/day
    atomic_json(d/'config.json',{'studio_plan':{'plan_id':root.name},'channels':['baidu_ai','wenxin_card'],'questions':['q'],'rounds':1})
    p=d/model/'collector';p.mkdir(parents=True,exist_ok=True);return p
   old=lane('2026-10-23','baidu_ai');seed=old/'profiles/baidu/scrapling_profile';seed.mkdir(parents=True);(seed/'session').write_text('good')
   (old.parent/'results.jsonl').write_text(json.dumps({'model':'baidu_ai','question':'q','round':1})+'\n')
   (old/'tasks.sqlite').write_text('old journal')
   current=lane('2026-10-24','baidu_ai');target=profile_for_search(current,'baidu_ai')
   self.assertEqual((target/'session').read_text(),'good');self.assertFalse((target/'tasks.sqlite').exists())
   self.assertEqual(profile_for_search(lane('2026-10-25','baidu_ai'),'baidu_ai'),target)
   self.assertNotEqual(profile_for_search(lane('2026-10-24','wenxin_card'),'wenxin_card'),target)
   (target/'session').write_text('updated');self.assertEqual((seed/'session').read_text(),'good')
 def test_creation_profile_rejects_open_seed_and_wrong_plan(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'plan-a';day=root/'days/2026-10-24';lane=day/'baidu_ai/collector';seed=lane/'profiles/baidu/scrapling_profile';seed.mkdir(parents=True)
   atomic_json(day/'config.json',{'studio_plan':{'plan_id':'plan-b'},'channels':['baidu_ai']})
   self.assertEqual(profile_for_search(lane,'baidu_ai'),seed)
   atomic_json(day/'config.json',{'studio_plan':{'plan_id':root.name},'channels':['baidu_ai']})
   (seed/'SingletonLock').write_text('live')
   with self.assertRaises(RuntimeError):profile_for_search(lane,'baidu_ai')
 def batch(self,base,name,model='baidu_ai',created=1,complete=False):
  root=base/'batches'/name;profile=root/'collector/profiles/baidu/scrapling_profile';profile.mkdir(parents=True)
  (profile/'session-marker').write_text(name)
  atomic_json(root/'manifest.json',{'model':model,'batch':name,'questions':['q'],'rounds':1,'created_at':created})
  atomic_json(root/'bridge_health.json',{'model':model,'batch':name,'status':'complete' if complete else 'running','processed':int(complete),'tasks':{'completed':int(complete)},'worker_pid':None,'bridge_pid':None})
  return root/'collector'
 def test_successful_profile_is_carried_across_days_without_copying_old_answers(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);old=self.batch(base,'yesterday',complete=True);current=self.batch(base,'today',created=2)
   atomic_json(old/'tasks.sqlite',{'never_copy':'old task'})
   target=profile_for_search(current,'baidu_ai')
   self.assertEqual((target/'session-marker').read_text(),'yesterday')
   self.assertFalse((target/'tasks.sqlite').exists());self.assertEqual((current/'profiles/baidu/scrapling_profile/session-marker').read_text(),'today')
   (target/'session-marker').write_text('refreshed')
   tomorrow=self.batch(base,'tomorrow',created=3);self.assertEqual(profile_for_search(tomorrow,'baidu_ai'),target)
   self.assertEqual((target/'session-marker').read_text(),'refreshed')
   self.assertEqual((old/'profiles/baidu/scrapling_profile/session-marker').read_text(),'yesterday')
 def test_channel_isolation_skips_unfinished_and_future_profiles(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);self.batch(base,'old-good',complete=True)
   self.batch(base,'new-unknown',created=2);self.batch(base,'future',created=99,complete=True)
   self.batch(base,'wenxin',model='wenxin_card',created=2,complete=True)
   current=self.batch(base,'current',created=3)
   target=profile_for_search(current,'baidu_ai');self.assertEqual((target/'session-marker').read_text(),'old-good')
   other=self.batch(base,'next-wenxin',model='wenxin_card',created=3)
   self.assertNotEqual(profile_for_search(other,'wenxin_card'),target)
   self.assertEqual((profile_for_search(other,'wenxin_card')/'session-marker').read_text(),'wenxin')
 def test_incomplete_migration_or_live_source_does_not_reset_or_steal_profile(self):
  for mode in ('live','staged','target'):
   with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp);old=self.batch(base,'old',complete=True);current=self.batch(base,'current',created=2)
    folder=base/'profiles/search/baidu_ai';folder.mkdir(parents=True)
    if mode=='live':(old/'profiles/baidu/scrapling_profile/SingletonLock').write_text('active')
    elif mode=='staged':(folder/'scrapling_profile.migrating').mkdir()
    else:(folder/'scrapling_profile').mkdir()
    with self.assertRaises(RuntimeError):profile_for_search(current,'baidu_ai')
    self.assertEqual((old/'profiles/baidu/scrapling_profile/session-marker').read_text(),'old')
 def test_standalone_unknown_manifest_and_unsupported_channel_never_share(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'collector'
   self.assertEqual(profile_for_search(root,'baidu_ai'),root/'profiles/baidu/scrapling_profile')
   root=Path(tmp)/'batches/current/collector'
   self.assertEqual(profile_for_search(root,'wenxin_card'),root/'profiles/baidu/scrapling_profile')
   with self.assertRaises(ValueError):profile_for_search(root,'deepseek')
 def test_real_factory_uses_the_persistent_profile_for_each_search_model(self):
  for model in ('baidu_ai','wenxin_card'):
   with patch.object(WenxinWebCollector,'__init__',return_value=None) as ctor,patch('geo_source_cards.search_profiles.profile_for_search',return_value=Path('/channel/profile')) as select:
    cli.create_collector(model);ctor.assert_called_once_with(profile=Path('/channel/profile'));self.assertEqual(select.call_args.args[1],model)

if __name__=='__main__':unittest.main()
