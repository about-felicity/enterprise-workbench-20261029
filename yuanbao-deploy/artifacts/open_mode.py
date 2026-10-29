import os
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
if not d(text='快速').exists:raise SystemExit('Observed mode control unavailable')
d(text='快速').click()
