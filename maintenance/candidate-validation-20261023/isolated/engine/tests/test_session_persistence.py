import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from web_collectors import session_store as store

class Page:
    def __init__(self):self.calls=[];self.cookies=[];self.storage={'local_storage':{'userToken':'test-secret'},'session_storage':{'session':'test-session'}}
    def call(self,method,params=None):
        self.calls.append((method,params))
        return {'cookies':self.cookies} if method=='Network.getAllCookies' else {}
    def evaluate(self,script):return self.storage if script.startswith('location.origin') else None

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'GEO_DEEPSEEK_PROFILE_DIR':str(self.root/'profile')});self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_restart_restores_session_cookie_and_storage(self):
        page=Page();page.cookies=[{'name':'ds_session_id','value':'secret','domain':'chat.deepseek.com','path':'/','expires':-1,'session':True}]
        self.assertTrue(store.checkpoint(page));other=Page();store.restore(other)
        restored=next(p for m,p in other.calls if m=='Network.setCookies')['cookies'][0]
        self.assertNotIn('expires',restored);self.assertEqual(restored['value'],'secret')
        script=next(p for m,p in other.calls if m=='Page.addScriptToEvaluateOnNewDocument')['source']
        self.assertIn('location.origin!=="https://chat.deepseek.com"',script)
        self.assertIn('sessionStorage',script)
    def test_never_overwrites_refreshed_cookie(self):
        page=Page();page.cookies=[{'name':'ds_session_id','value':'old','domain':'chat.deepseek.com','path':'/'}];store.checkpoint(page)
        other=Page();other.cookies=[{**page.cookies[0],'value':'new'}];store.restore(other)
        self.assertFalse(any(m=='Network.setCookies' for m,p in other.calls))
    def test_expired_and_foreign_cookies_excluded(self):
        store.write_state({'version':1,'cookies':[{'name':'old','domain':'chat.deepseek.com','expires':1},{'name':'foreign','domain':'evil.example','value':'x'}]})
        page=Page();store.restore(page);self.assertFalse(any(m=='Network.setCookies' for m,p in page.calls))
    def test_rejected_session_is_not_resurrected(self):
        store.checkpoint(Page());store.invalidate();self.assertFalse(store.restore(Page()))
        self.assertNotIn('test-secret',store.state_path().read_text())
    def test_file_is_private(self):
        store.checkpoint(Page())
        if os.name!='nt':self.assertEqual(store.state_path().stat().st_mode&0o777,0o600)
    def test_batch_rollover_and_login_share_profile(self):
        with patch.dict(os.environ,{},clear=True):
            with patch.object(store,'runtime_root',return_value=Path('/example/geo/batches/first/collector')):first=store.profile_path()
            with patch.object(store,'runtime_root',return_value=Path('/example/geo/batches/second/collector')):self.assertEqual(store.profile_path(),first)
            self.assertEqual(first,Path('/example/geo/profiles/deepseek'))
    def test_unrelated_runtime_keeps_own_account(self):
        with patch.dict(os.environ,{},clear=True),patch.object(store,'runtime_root',return_value=Path('/editorial/runtime')):
            self.assertEqual(store.profile_path(),Path('/editorial/runtime/web_profiles/deepseek'))

if __name__=='__main__':unittest.main()
