import subprocess,json,time,hashlib,socket
from pathlib import Path
w=Path('/home/user/redroid-doubao/expansion-20261102');w.mkdir(exist_ok=True)
def run(*a):return subprocess.check_output(a,text=True,timeout=90).strip()
old=json.loads(run('docker','inspect','doubao-hpe14-account2'))[0]
assert old['Image']=='sha256:18244ad4ab1c36047438bb9c524d8f8d6f848ee8d7537a98483a26c5dda7601f'
apk=run('docker','exec','doubao-hpe14-account2','pm','path','com.larus.nova').removeprefix('package:');assert '\n' not in apk
lib=str(Path(apk).parent/'lib/arm64/libkeva.so')
subprocess.run(['docker','cp','doubao-hpe14-account2:'+apk,str(w/'doubao.apk')],check=True)
subprocess.run(['docker','cp','doubao-hpe14-account2:'+lib,str(w/'libkeva.so')],check=True)
assert hashlib.sha256((w/'libkeva.so').read_bytes()).hexdigest()=='dab31cd9e76eefbdc72502108029d181fbccca5e1304816c472d6c8373f9117c'
for num,port in [(3,5563),(4,5564)]:
 name=f'doubao-hpe14-account{num}';volume=name+'-data'
 exists=name in run('docker','ps','-a','--format','{{.Names}}').splitlines()
 if exists:
  info=json.loads(run('docker','inspect',name))[0]
  assert info['Config']['Labels'].get('geo.expansion')=='20261102' and info['Image']==old['Image']
 else:
  with socket.socket() as probe:probe.bind(('127.0.0.1',port))
  available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
  assert available>3*1024*1024,'Not enough current headroom to boot another device'
  run('docker','volume','create',volume)
  print('CREATING',name,flush=True)
  run('docker','run','-d','--name',name,'--label','geo.expansion=20261102','--restart','unless-stopped','--privileged','--cpus','2','--memory','3g','--memory-swap','4g','-p',f'127.0.0.1:{port}:5555','-v',volume+':/data',old['Image'],*old['Config']['Cmd'])
 for _ in range(90):
  boot=subprocess.run(['docker','exec',name,'/system/bin/getprop','sys.boot_completed'],capture_output=True,text=True)
  if boot.returncode==0 and boot.stdout.strip()=='1':break
  time.sleep(2)
 else:raise RuntimeError('Boot timeout '+name)
 run('docker','cp',str(w/'doubao.apk'),name+':/data/local/tmp/doubao.apk')
 print('INSTALL',name,run('docker','exec',name,'pm','install','/data/local/tmp/doubao.apk'),flush=True)
 newapk=run('docker','exec',name,'pm','path','com.larus.nova').removeprefix('package:');newlib=str(Path(newapk).parent/'lib/arm64/libkeva.so')
 run('docker','cp',name+':'+newlib,str(w/f'account{num}-libkeva-original.so'))
 run('docker','cp',str(w/'libkeva.so'),name+':'+newlib)
 run('docker','exec',name,'chmod','755',newlib)
 assert run('docker','exec',name,'sha256sum',newlib).split()[0]=='dab31cd9e76eefbdc72502108029d181fbccca5e1304816c472d6c8373f9117c'
 assert run('docker','exec',name,'getprop','ro.build.version.sdk')=='33'
 assert run('docker','exec',name,'sha256sum','/system/lib64/libhoudini.so').split()[0]=='5ef64035ec89bca3d5e33b9f3b6556f98f6c11d11957387d403ae4a4d7cc40ec'
 run('docker','exec',name,'am','start','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1')
 print('READY_FOR_LOGIN',name,port,flush=True)
print(run('free','-m'),flush=True)
