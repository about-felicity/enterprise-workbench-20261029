import sys,time,runpy
sys.path.insert(0,'/home/user/redroid-yuanbao')
from android_ui import Android
a=Android();item=a.device(description='抽屉页入口');assert item.count==1;a.tap(item);time.sleep(1)
try:runpy.run_path('/tmp/yuanbao-read-history22.py',run_name='__main__')
finally:a.device.press('back')
