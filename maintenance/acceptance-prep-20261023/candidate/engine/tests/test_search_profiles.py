import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from geo_source_cards.search_profiles import profile_for_search
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards import cli
from wenxin_monitor.controller import WenxinWebCollector

class SearchProfileTests(unittest.TestCase):
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
