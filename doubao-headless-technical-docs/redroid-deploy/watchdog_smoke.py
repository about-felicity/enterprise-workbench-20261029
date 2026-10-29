from unattended_worker import notify
import time
notify('READY=1\nWATCHDOG=1')
time.sleep(20)
