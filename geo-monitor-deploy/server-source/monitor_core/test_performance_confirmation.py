import unittest,os,tempfile,json
from unittest.mock import patch
from datetime import datetime,timezone
from .performance_confirmation import confirmation_window,snapshot_fingerprint,BEIJING

class ConfirmationTests(unittest.TestCase):
    def test_window_boundaries(self):
        for hour,minute,state in [(0,0,'open'),(17,59,'open'),(18,0,'closed')]:
            self.assertEqual(confirmation_window('2026-11',datetime(2026,11,30,hour,minute,tzinfo=BEIJING))['state'],state)
        self.assertEqual(confirmation_window('2026-11',datetime(2026,11,29,23,59,tzinfo=BEIJING))['state'],'upcoming')
    def test_leap_year_and_timezone(self):
        self.assertEqual(confirmation_window('2028-02',datetime(2028,2,29,9,tzinfo=timezone.utc))['state'],'open')
        self.assertEqual(confirmation_window('2028-02',datetime(2028,2,29,10,tzinfo=timezone.utc))['state'],'closed')
    def test_invalid_month_and_naive_clock(self):
        for month in ['2026-13','bad','2026-1']:
            with self.assertRaises(ValueError):confirmation_window(month)
        with self.assertRaises(ValueError):confirmation_window('2026-11',datetime(2026,11,30))
    def test_exact_snapshot(self):
        a={'name':'佳佳','current':{'score':88,'date':'2026-11-30'}}
        self.assertEqual(snapshot_fingerprint(a,'2026-11'),snapshot_fingerprint(a,'2026-11'))
        b={**a,'current':{**a['current'],'score':89}}
        self.assertNotEqual(snapshot_fingerprint(a,'2026-11')[1],snapshot_fingerprint(b,'2026-11')[1])

class StoreTests(unittest.TestCase):
    def setUp(self):
        from . import performance_confirmation as c
        self.c=c;self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,MONITOR_PERFORMANCE_DB=self.tmp.name+'/test.sqlite');self.env.start()
        self.window=patch.object(c,'confirmation_window',return_value={'state':'open'});self.window.start()
        self.data={'people':[{'name':'佳佳','current':{'score':88,'coefficient':1,'date':'2026-11-30'}}]}
        self.call=lambda p,actor='geo_admin',session='s':c.act({'name':'佳佳','month':'2026-11',**p},actor,session,lambda m:self.data)
    def tearDown(self):self.window.stop();self.env.stop();self.tmp.cleanup()
    def setup_password(self):self.call({'action':'setup','password':'REDACTED_CONFIGURE_LOCALLY'})
    def test_setup_and_no_overwrite(self):
        self.setup_password()
        with self.assertRaises(ValueError):self.setup_password()
        with self.c.database() as db:
            r=db.execute('select * from confirmation_passwords').fetchone()
            self.assertNotIn('secret123',r['digest']);self.assertEqual(len(r['salt']),32)
    def test_confirm_snapshot_and_idempotence(self):
        self.setup_password();preview=self.call({'action':'preview'})
        result=self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY','token':preview['token']})
        again=self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY','token':preview['token']})
        self.assertEqual(result['confirmed_at'],again['confirmed_at'])
        self.data['people'][0]['current']['score']=99
        with self.c.database() as db:
            rows=db.execute('select * from performance_confirmations').fetchall()
            self.assertEqual(len(rows),1);self.assertEqual(json.loads(rows[0]['snapshot'])['current']['score'],88)
    def test_permissions(self):
        for actor in ['anonymous','superadmin','another']:
            with self.assertRaises(PermissionError):self.call({'action':'setup','password':'REDACTED_CONFIGURE_LOCALLY'},actor)
        with self.assertRaises(PermissionError):self.call({'action':'reset'})
    def test_password_attempts_persist(self):
        self.setup_password()
        for _ in range(5):
            with self.assertRaises(ValueError):self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY'})
        with self.assertRaisesRegex(ValueError,'15分钟'):self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY'})
    def test_session_and_reset(self):
        self.setup_password();p=self.call({'action':'preview'})
        with self.assertRaises(ValueError):self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY','token':p['token']},session='other')
        self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY','token':p['token']})
        self.call({'action':'reset'},actor='superadmin')
        with self.c.database() as db:
            self.assertEqual(db.execute('select count(*) from confirmation_passwords').fetchone()[0],0)
            self.assertEqual(db.execute('select count(*) from performance_confirmations').fetchone()[0],1)
    def test_change_invalidates_preview(self):
        self.setup_password();p=self.call({'action':'preview'})
        self.call({'action':'change','password':'REDACTED_CONFIGURE_LOCALLY','old_password':'secret123'})
        with self.assertRaises(ValueError):self.call({'action':'confirm','password':'REDACTED_CONFIGURE_LOCALLY','token':p['token']})
    def test_closed_window(self):
        self.setup_password();self.window.stop()
        with patch.object(self.c,'confirmation_window',return_value={'state':'closed'}):
            with self.assertRaises(ValueError):self.call({'action':'preview'})
        self.window.start()

if __name__=='__main__':unittest.main()
