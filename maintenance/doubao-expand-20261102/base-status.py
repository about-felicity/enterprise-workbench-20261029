from pathlib import Path
import json,zipfile,hashlib,sqlite3,subprocess
with zipfile.ZipFile('/tmp/doubao-strict-lanes-20261102.zip') as z:
 for n,v in json.loads(z.read('manifest.json')).items():
  p=Path(v['target']);print(n,p.exists(),p.exists() and hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==v['base'])
b=Path('/opt/monitor/geo-capture')
with sqlite3.connect(b/'panel/control.sqlite') as d:
 for model,raw in d.execute("select model,value from settings where model like 'doubao%'"):
  v=json.loads(raw);print(model,len(v['questions']),v['rounds'],v['interval'])
print(subprocess.check_output(['systemctl','list-unit-files','geo-*','--no-legend'],text=True)[:4500])
