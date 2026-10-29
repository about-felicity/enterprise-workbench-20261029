import sys,traceback,subprocess,time
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import Android,deadline
try:
 a=Android('127.0.0.1:5558','/home/user/redroid-doubao/linux-tools/platform-tools/adb')
 with deadline(75):a.ready()
 print('ready_ok',flush=True)
except Exception:
 traceback.print_exc()
finally:
 subprocess.run(['systemctl','start','geo-native@geo-panel-doubao2-20261019-090003-88e4f45b.service'],check=True)
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
