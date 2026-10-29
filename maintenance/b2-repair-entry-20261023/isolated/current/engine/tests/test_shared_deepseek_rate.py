import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards.cli import deepseek_rate_path

class SharedRateTests(unittest.TestCase):
 def test_shared_rate_carries_latest_geo_and_creation_send_without_regression(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);runtime=root/'private';runtime.mkdir();(runtime/'deepseek_last_prompt.json').write_text('{"last_prompt_epoch":100}')
   previous=root/'geo/batch/collector';previous.mkdir(parents=True);(previous/'deepseek_last_prompt.json').write_text('{"last_prompt_epoch":250}')
   with patch.dict(os.environ,{'GEO_DEEPSEEK_RATE_STATE':str(root/'shared.json'),'GEO_DEEPSEEK_SEED_ROOT':str(root/'geo')}):
    target=deepseek_rate_path(runtime);self.assertEqual(json.loads(target.read_text())['last_prompt_epoch'],250)
    target.write_text('{"last_prompt_epoch":500}')
    self.assertEqual(json.loads(deepseek_rate_path(runtime).read_text())['last_prompt_epoch'],500)
 def test_corrupt_state_fails_instead_of_bypassing_spacing(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'shared.json').write_text('corrupt')
   with patch.dict(os.environ,{'GEO_DEEPSEEK_RATE_STATE':str(root/'shared.json')}):
    with self.assertRaises(ValueError):deepseek_rate_path(root)
 def test_legacy_runtime_path_is_unchanged(self):
  with patch.dict(os.environ,{},clear=True):self.assertEqual(deepseek_rate_path(Path('/tmp/legacy')),Path('/tmp/legacy/deepseek_last_prompt.json'))

if __name__=='__main__':unittest.main()
