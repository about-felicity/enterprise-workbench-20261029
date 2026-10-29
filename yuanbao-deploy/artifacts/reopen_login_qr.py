import os,json
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
current=d.app_current()
if current.get('package')!='com.tencent.hunyuan.app.chat':
 raise SystemExit('Yuanbao is not foreground; no navigation performed')
if current.get('activity')=='com.tencent.hunyuan.deps.webview.ui.WebActivity':
 d.press('back')
if d(text='微信扫码登录').wait(timeout=3):
 d.click(644,372)
if not d(text='手机登录').wait(timeout=4):
 if not d(text='登录').wait(timeout=5):raise SystemExit('Login entry unavailable; no logout or reset performed')
 d(text='登录').click()
if not d(text='手机登录').wait(timeout=7):raise SystemExit('Login sheet unavailable')
d.click(360,978)
if d(text='同意').wait(timeout=1):d(text='同意').click()
print(json.dumps({'fresh_login_qr_requested':bool(d(text='微信扫码登录').wait(timeout=10))}))
