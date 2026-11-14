import sys,unittest,tempfile,sqlite3,time,json,os
from unittest.mock import patch,Mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wenxin_retry import due,failed,clear_verified,browser_lock,retry_state,reusable_probe
class RetryTests(unittest.TestCase):
 def test_first_probe_due(self):self.assertTrue(due({},100))
 def test_browser_lock_prevents_parallel_profile_use_and_releases(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'browser.lock'
   with browser_lock(path):
    with self.assertRaises(RuntimeError):
     with browser_lock(path):pass
   with browser_lock(path):pass
 def test_cooldown_is_durable(self):
  s=failed({},100,'verification_required');self.assertFalse(due(s,999));self.assertTrue(due(s,1000))
 def test_three_attempts_stop_even_after_long_wait(self):
  s={}
  for i in range(3):s=failed(s,100+i*2000,'verification_required')
  self.assertEqual(s['attempts'],3);self.assertEqual(s['status'],'needs_attention');self.assertFalse(due(s,99999999))
 def test_increasing_cooldown(self):
  s=failed({},100,'read_error');self.assertEqual(s['next_at'],1000)
  s=failed(s,1000,'read_error');self.assertEqual(s['next_at'],2800)
 def test_retry_budget_is_preserved_for_current_batch_and_renewed_for_next_batch(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'retry.json'
   path.write_text(json.dumps({'attempts':3,'at':120,'next_at':900}))
   current={'state':path,'batch':'today','created_at':100}
   self.assertFalse(due(retry_state(current),2000))
   path.write_text(json.dumps(failed(retry_state(current),2000,'verification_required')))
   self.assertEqual(retry_state(current)['batch'],'today')
   tomorrow={**current,'batch':'tomorrow','created_at':3000}
   self.assertEqual(retry_state(tomorrow),{'batch':'tomorrow'})
   self.assertTrue(due(retry_state(tomorrow),3000))
 def test_no_clear_for_challenge_or_stale_proof(self):
  for proof in ({'status':'verification_required','at':time.time()},{'status':'ready','at':0}):
   with self.assertRaises(AssertionError):clear_verified({},proof)
 def test_cached_success_must_be_newer_than_the_last_challenge(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   (root/'search_recovery.json').write_text(json.dumps({'kind':'verification','checked_epoch':120}))
   proof=root/'verification_probe_latest.json'
   for timestamp,expected in ((110,False),(120,False),(121,True),(160,False)):
    proof.write_text(json.dumps({'status':'ready','at':timestamp}))
    self.assertEqual(bool(reusable_probe([root],150)),expected)
 def test_pause_wins_over_successful_probe(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'pause').touch()
   self.assertFalse(clear_verified({'pause':root/'pause','settings':None},{'status':'ready','at':time.time()}))
 def test_success_only_clears_gate_not_captured_rows(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);db=sqlite3.connect(root/'tasks.sqlite')
   db.executescript('create table search_recovery_control(id,streak,cooldown_until,blocked);insert into search_recovery_control values(1,4,999,1);create table captures(state,result);insert into captures values("completed","original");');db.close()
   block=root/'block.json';block.write_text('{}')
   item={'pause':root/'pause','settings':None,'runtimes':[root],'blocks':[block]}
   with patch('wenxin_retry.os.chown'):
    self.assertTrue(clear_verified(item,{'status':'ready','at':time.time()}))
   db=sqlite3.connect(root/'tasks.sqlite')
   self.assertEqual(db.execute('select blocked from search_recovery_control').fetchone()[0],0)
   self.assertEqual(db.execute('select * from captures').fetchone(),('completed','original'));db.close();self.assertFalse(block.exists())
if __name__=='__main__':unittest.main()
