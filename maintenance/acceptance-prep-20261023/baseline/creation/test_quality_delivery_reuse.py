import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from . import quality_repair as q

class DeliveryReuseTests(unittest.TestCase):
 def test_complete_append_repaired_delivery_is_reused_without_replaying_writer(self):
  with tempfile.TemporaryDirectory() as tmp:
   entry=Path(tmp);previous=entry/'attempt-3/days/2026-10-20/articles/排行类/01/writer'
   side=entry/'attempt-5';base=side/'days/2026-10-20/articles/排行类/01';writer=base/'writer'
   for p in (previous,writer):
    p.mkdir(parents=True)
    for n in ('knowledge.json','product.json'):(p/n).write_text('{}')
   (previous/'draft.md').write_text('已送达并补齐篇幅的稿件')
   (previous/'writer_done.json').write_text('{}')
   with patch.object(q,'check',return_value={'failures':[]}) as checked,patch.object(q.CreationClient,'complete') as paid:
    reused=q.reuse_verified_delivery(entry,side,base)
   self.assertEqual(reused,str(previous/'writer_done.json'))
   self.assertEqual((writer/'draft.md').read_text(),'已送达并补齐篇幅的稿件');self.assertEqual(checked.call_count,2);paid.assert_not_called()
 def test_different_frozen_product_or_failing_delivery_cannot_be_reused(self):
  with tempfile.TemporaryDirectory() as tmp:
   entry=Path(tmp);previous=entry/'attempt-1/days/d/articles/c/01/writer';side=entry/'attempt-2';base=side/'days/d/articles/c/01';writer=base/'writer'
   for p in (previous,writer):
    p.mkdir(parents=True)
    for n in ('knowledge.json','product.json'):(p/n).write_text('{}')
   with patch.object(q,'check',return_value={'failures':['unsupported claim']}):self.assertIsNone(q.reuse_verified_delivery(entry,side,base))
   (previous/'product.json').write_text('{"name":"另一个产品"}')
   with patch.object(q,'check') as checked:self.assertIsNone(q.reuse_verified_delivery(entry,side,base));checked.assert_not_called()

if __name__=='__main__':unittest.main()
