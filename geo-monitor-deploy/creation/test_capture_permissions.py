import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from . import materials
class CapturePermissionsTests(unittest.TestCase):
 def test_snapshot_readable_by_collector_group_and_immutable(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);owner=SimpleNamespace(pw_gid=os.getgid())
   materials.capture_snapshot(root,{'questions':['original']},owner)
   path=root/'config.json';self.assertEqual(path.stat().st_mode&0o777,0o640)
   path.chmod(0o600)
   materials.capture_snapshot(root,{'questions':['changed']},owner)
   self.assertEqual(path.stat().st_mode&0o777,0o640)
   self.assertEqual(materials.read(path),{'questions':['original']})
