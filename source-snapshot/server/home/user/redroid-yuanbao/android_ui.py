"""Use the App's normal new-chat and send controls. Never replay a send."""
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from native_core import NativeDataError

PACKAGE='com.tencent.hunyuan.app.chat'
ADB='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
SERIAL='127.0.0.1:5559'


def update_notice_close(xml):
    """Recognize the optional update dialog and its unique, visible close icon."""
    nodes=[n for n in ET.fromstring(xml).iter('node') if n.get('package')==PACKAGE]
    texts={n.get('text','') for n in nodes}
    if not {'元宝新版本','立即更新'}<=texts:return None
    if not any(re.fullmatch(r'新版本 v\d+(?:\.\d+)+',text) for text in texts):
        raise NativeDataError('Unrecognized Yuanbao update notice; no click attempted')
    def bounds(node):
        values=[int(v) for v in re.findall(r'\d+',node.get('bounds',''))]
        return values if len(values)==4 else None
    updates=[bounds(n) for n in nodes if n.get('text')=='立即更新' and n.get('clickable')=='true']
    if len(updates)!=1 or updates[0] is None:raise NativeDataError('Update action is ambiguous; no click attempted')
    left,top,right,bottom=updates[0]
    closes=[]
    for n in nodes:
        box=bounds(n)
        if (n.get('class')=='android.widget.ImageView' and n.get('clickable')=='true'
            and n.get('enabled')!='false' and not n.get('text') and not n.get('content-desc')
            and box and box[1]>=bottom and left<=(box[0]+box[2])/2<=right
            and 20<=box[2]-box[0]<=120 and 20<=box[3]-box[1]<=120):closes.append(box)
    if len(closes)!=1:raise NativeDataError('Optional update close icon is ambiguous; no click attempted')
    return closes[0]


def assert_fresh(xml):
    for node in ET.fromstring(xml).iter('node'):
        if node.get('class')=='android.widget.EditText':continue
        if '采集任务编号：' in node.get('text',''):
            raise NativeDataError('Previous question remains visible; new chat not proven')


def draft_matches(xml, question):
    nodes=list(ET.fromstring(xml).iter('node'))
    edits=[n for n in nodes if n.get('class')=='android.widget.EditText' and n.get('package')==PACKAGE]
    return (len(edits)==1 and edits[0].get('text') in (question,question+'\n')
            and any(n.get('content-desc')=='临时对话模式开关-关' for n in nodes)
            and not any(n.get('text') in {'登录','安全验证','微信扫码登录'} for n in nodes))


def stable_send_button(d, wire):
    # Hide only a visible IME. A stale coordinate can otherwise hit its enter key.
    if d.info.get('currentPackageName')!=PACKAGE:
        raise NativeDataError('App changed before send')
    if d.shell(['dumpsys','input_method']).output.find('mInputShown=true')>=0:
        d.press('back')
        time.sleep(.5)
    button=d(className='android.widget.Button',clickable=True,packageName=PACKAGE)
    edit=d(className='android.widget.EditText',packageName=PACKAGE)
    previous=None;stable=0
    for _ in range(12):
        if button.count!=1 or edit.count!=1 or edit.get_text()!=wire:
            raise NativeDataError('Exact input or unique send control changed')
        info=button.info
        current=info['bounds']
        stable=stable+1 if current==previous and info.get('enabled') else 0
        if stable>=3:return button,current
        previous=current;time.sleep(.25)
    raise NativeDataError('Send layout did not stabilize')


class Android:
    def __init__(self):
        os.environ['ADBUTILS_ADB_PATH']=ADB
        subprocess.run([ADB,'connect',SERIAL],check=True,timeout=15,capture_output=True)
        import uiautomator2 as u2
        self.device=u2.connect(SERIAL)

    def tap(self, selector):
        bounds=selector.info['bounds']
        self.device.shell(['input','tap',str((bounds['left']+bounds['right'])//2),str((bounds['top']+bounds['bottom'])//2)])

    def ensure_open(self):
        if self.device.app_current().get('package')!=PACKAGE:
            self.device.shell(['am','start','-W','-n',PACKAGE+'/.biz.login.v2.HYLoginMainActivity'])
        if not self.device.app_wait(PACKAGE,timeout=20):
            raise NativeDataError('Yuanbao process did not start; no baseline or send attempted')

    def ready(self):
        d=self.device
        if d.app_info(PACKAGE).get('versionCode')!=66517035:
            raise NativeDataError('Yuanbao APK changed')
        self.ensure_open()
        close=update_notice_close(d.dump_hierarchy())
        if close:
            if d.app_current().get('package')!=PACKAGE or update_notice_close(d.dump_hierarchy())!=close:
                raise NativeDataError('Update notice changed before dismissal; no click attempted')
            d.shell(['input','tap',str((close[0]+close[2])//2),str((close[1]+close[3])//2)])
            time.sleep(.75)
            if d.app_current().get('package')!=PACKAGE or update_notice_close(d.dump_hierarchy()):
                raise NativeDataError('Optional update notice did not close; no question sent')
        if d(text='登录').exists or d(text='安全验证').exists or d(text='微信扫码登录').exists:
            raise NativeDataError('Yuanbao login or security verification required')
        new=d(description='新建对话')
        if new.exists:self.tap(new)
        landing=d(description='临时对话模式开关-关')
        if not landing.wait(timeout=20):
            raise NativeDataError('Empty new-chat landing page not confirmed')
        edit=d(className='android.widget.EditText')
        if not edit.exists:
            keyboard=d(description='切换键盘')
            if keyboard.exists:self.tap(keyboard)
        if not edit.wait(timeout=5) or edit.count!=1:
            raise NativeDataError('Text mode unavailable; no send attempted')
        if edit.get_text():edit.set_text('')
        for _ in range(2):
            assert_fresh(d.dump_hierarchy())
            time.sleep(.5)

    def send(self, wire, before_click):
        d=self.device
        edit=d(className='android.widget.EditText')
        edit.set_text(wire)
        if edit.get_text()!=wire:raise NativeDataError('Editor does not contain the exact task')
        button,bounds=stable_send_button(d,wire)
        assert_fresh(d.dump_hierarchy())
        before_click()
        if button.info['bounds']!=bounds or edit.get_text()!=wire:
            raise NativeDataError('Send layout changed after durable intent; no click')
        # The durable click intent is committed before this sole UI send.
        d.shell(['input','tap',str((bounds['left']+bounds['right'])//2),str((bounds['top']+bounds['bottom'])//2)])

    def evidence(self, root, task_id):
        try:
            self.device.screenshot().save(root/(task_id+'.png'))
            (root/(task_id+'.xml')).write_text(self.device.dump_hierarchy(),encoding='utf8')
        except Exception:pass
