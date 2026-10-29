import os,json
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
if not d(text='微信扫码登录').exists:
    raise SystemExit('Expected WeChat QR page; no action taken')
d.click(644,372)
if not d(text='手机登录').wait(timeout=7):
    raise SystemExit('Expected normal login sheet; no further action')
d.click(360,978)
print(json.dumps({'qr_page':bool(d(text='微信扫码登录').wait(timeout=10))}))
