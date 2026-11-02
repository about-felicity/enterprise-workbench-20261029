import subprocess
for n in (3,4):
 c=f'doubao-hpe14-account{n}'
 for a in (['wm','size'],['wm','density'],['getprop','persist.sys.locale']):
  print(n,a,subprocess.check_output(['docker','exec',c,*a],text=True).strip())
