import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_readback_guard import AppReadbackGuard
from unattended_core import DataError
from question_only_adapters import assert_question_only_composer,wait_question_only_landing,optional_commerce_login,dismiss_optional_commerce_login

def atomic(path,value):path.write_text(json.dumps(value))
class Device:
    def __init__(self,code=1,output=''):self.calls=[];self.code=code;self.output=output
    def shell(self,command):
        self.calls.append(command)
        return SimpleNamespace(exit_code=self.code,output=self.output) if command[0]=='pidof' else SimpleNamespace(exit_code=0,output='ok')

class Tests(unittest.TestCase):
    task={'task_id':'original','state':'prepared'}
    def test_only_exact_optional_shop_connection_is_declined(self):
        from unittest.mock import Mock
        fields={'tv_app_name':'抖音商城','tv_title':'在豆包内使用抖音商城','tv_subtitle':'登录后豆包可帮你完成下单、订单查询、售后申请等操作','btn_negative':'不登录','btn_positive':'登录'}
        xml='<hierarchy>'+''.join('<node resource-id="com.larus.nova:id/'+k+'" text="'+v+'"/>' for k,v in fields.items())+'</hierarchy>'
        self.assertTrue(optional_commerce_login(xml))
        a=Mock();a.device.app_current.return_value={'package':'com.larus.nova'};a.device.dump_hierarchy.return_value=xml
        self.assertTrue(dismiss_optional_commerce_login(a));a.tap.assert_called_once();a.device.assert_called_once_with(resourceId='com.larus.nova:id/btn_negative',text='不登录')
        for altered in ('<hierarchy><node text="登录"/></hierarchy>',xml.replace('在豆包内使用抖音商城','登录豆包'),xml.replace('不登录','取消')):
            self.assertFalse(optional_commerce_login(altered));a.reset_mock();a.device.dump_hierarchy.return_value=altered
            self.assertFalse(dismiss_optional_commerce_login(a));a.tap.assert_not_called()
    def test_landing_wait_requires_two_strict_snapshots_without_ui_actions(self):
        prefix='com.larus.nova:id/'
        good='<hierarchy><node resource-id="'+prefix+'back_icon" content-desc="返回"/><node resource-id="'+prefix+'input_text"/><node text="为你推荐"/></hierarchy>'
        old=good.replace('</hierarchy>','<node resource-id="'+prefix+'msg_action_copy"/></hierarchy>')
        now=[0];frames=iter([old,good,old,good,good]);seen=[]
        def dump():
            value=next(frames);seen.append(value);return value
        def sleep(seconds):now[0]+=seconds
        wait_question_only_landing(SimpleNamespace(dump_hierarchy=dump),clock=lambda:now[0],sleep=sleep)
        self.assertEqual(len(seen),5)
        with self.assertRaises(DataError):
            wait_question_only_landing(SimpleNamespace(dump_hierarchy=lambda:old),timeout=1,clock=lambda:now[0],sleep=sleep)
    def test_missing_app_reopens_without_question_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Device();events=[];g=AppReadbackGuard(tmp,atomic,lambda:100)
            self.assertEqual(g.check(d,self.task,{'status':'waiting'},lambda *a:events.append(a))['phase'],'reopening_original_app')
            self.assertEqual(d.calls,[['pidof','com.larus.nova'],['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1']])
            self.assertEqual(len(events),1)
    def test_live_app_and_complete_answer_never_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Device(0,'123');g=AppReadbackGuard(tmp,atomic,lambda:100)
            self.assertIsNone(g.check(d,self.task,{'status':'waiting'},lambda *a:None));self.assertEqual(len(d.calls),1)
            self.assertIsNone(g.check(d,self.task,{'status':'complete'},lambda *a:None));self.assertEqual(len(d.calls),1)
    def test_missing_yuanbao_reopens_original_app_without_new_chat_or_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Device();events=[];g=AppReadbackGuard(tmp,atomic,lambda:100,model='yuanbao')
            self.assertEqual(g.check(d,self.task,{},lambda *a:events.append(a))['phase'],'reopening_original_app')
            self.assertEqual(d.calls,[['pidof','com.tencent.hunyuan.app.chat'],['am','start','-W','-n','com.tencent.hunyuan.app.chat/.biz.login.v2.HYLoginMainActivity']])
            self.assertEqual(len(events),1)
            g=AppReadbackGuard(tmp,atomic,lambda:131,model='yuanbao');d=Device()
            self.assertEqual(g.check(d,self.task,{},lambda *a:None,paused=True)['phase'],'app_stopped_original_pending')
            self.assertEqual(d.calls,[['pidof','com.tencent.hunyuan.app.chat']])
    def test_pause_stop_and_transport_failure_do_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kw in ({'paused':True},{'stopping':True}):
                g=AppReadbackGuard(tmp,atomic,lambda:1000);g.state={};d=Device()
                self.assertEqual(g.check(d,self.task,{'status':'waiting'},lambda *a:None,**kw)['phase'],'app_stopped_original_pending');self.assertEqual(len(d.calls),1)
            g.state={};d=Device(127,'unavailable')
            with self.assertRaises(RuntimeError):g.check(d,self.task,{'status':'waiting'},lambda *a:None)
            self.assertEqual(len(d.calls),1)
    def test_relaunch_budget_survives_worker_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Device()
            for now in (100,131,162):
                g=AppReadbackGuard(tmp,atomic,lambda:now);self.assertEqual(g.check(d,self.task,{'status':'waiting'},lambda *a:None)['phase'],'reopening_original_app')
            g=AppReadbackGuard(tmp,atomic,lambda:193)
            self.assertEqual(g.check(d,self.task,{'status':'waiting'},lambda *a:None)['phase'],'app_recovery_backoff')
            self.assertEqual(sum(c[0]=='am' for c in d.calls),3)
    def test_real_empty_landing_required_before_pure_question(self):
        prefix='com.larus.nova:id/'
        xml='<hierarchy><node resource-id="'+prefix+'back_icon" content-desc="返回"/><node resource-id="'+prefix+'input_text"/><node text="为你推荐"/></hierarchy>'
        assert_question_only_composer(xml,landing=True)
        for extra in ('side_bar_merged_main_title','msg_action_copy','md_video_group_cover'):
            with self.assertRaises(Exception):assert_question_only_composer(xml.replace('</hierarchy>','<node resource-id="'+prefix+extra+'"/></hierarchy>'),landing=True)
        with self.assertRaises(Exception):assert_question_only_composer(xml.replace('返回','对话列表'))

if __name__=='__main__':unittest.main()
