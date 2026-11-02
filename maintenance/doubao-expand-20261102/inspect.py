import subprocess,json
from pathlib import Path
print(subprocess.check_output(['free','-m'],text=True))
for name in ['doubao-hpe14-13-test','doubao-hpe14-account2']:
 r=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
 print('EXISTING',json.dumps({'name':name,'image':r['Image'],'cmd':r['Config']['Cmd'],'memory':r['HostConfig']['Memory'],'nano_cpus':r['HostConfig']['NanoCpus'],'ports':r['HostConfig']['PortBindings'],'mounts':r['Mounts']}))
 print('VERSION',subprocess.check_output(['docker','exec',name,'sh','-c','dumpsys package com.larus.nova | grep -E "versionName=|versionCode="; getprop dalvik.vm.heapgrowthlimit; getprop dalvik.vm.heapsize; ls /data/local/tmp'],text=True))
print('CONTAINERS',subprocess.check_output(['docker','ps','-a','--format','{{.Names}} {{.Status}} {{.Ports}}'],text=True))
print('LISTEN',subprocess.check_output(['ss','-ltn'],text=True))
