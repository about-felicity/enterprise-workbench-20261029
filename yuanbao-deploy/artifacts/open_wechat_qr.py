import os,json
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
if d(text='登录').wait(timeout=10):d(text='登录').click()
if not d(text='手机登录').wait(timeout=10):
 print(json.dumps({'qr_opened':False,'reason':'login_sheet_unavailable'}));raise SystemExit()
d.click(360,978)
if d(text='同意').wait(timeout=2):d(text='同意').click()
print(json.dumps({'qr_opened':bool(d(text='微信扫码登录').wait(timeout=10))}))
