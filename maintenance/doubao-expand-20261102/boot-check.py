import subprocess
print(subprocess.run(['docker','ps','--filter','name=doubao-hpe14-account','--format','{{.Names}} {{.Status}}'],capture_output=True,text=True).stdout)
print(subprocess.run(['docker','logs','--tail','15','doubao-hpe14-account3'],capture_output=True,text=True).stdout[-2000:])
print(subprocess.run(['docker','exec','doubao-hpe14-account3','/system/bin/getprop','sys.boot_completed'],capture_output=True,text=True).stdout)
