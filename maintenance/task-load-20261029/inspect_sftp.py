import sys,re,json,stat
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'ssh-deps'))
import paramiko
config=(Path(__file__).resolve().parents[2]/'local_server.txt').read_text('utf-8-sig')
target=re.search(r'ssh\s+([\w.-]+)@([\w.-]+)',config)
password=re.search(r'password\s*:\s*(.+)',config).group(1).strip()
client=paramiko.SSHClient();client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(target.group(2),username=target.group(1),password=password,timeout=20,look_for_keys=False,allow_agent=False)
rows=[]
try:
 with client.open_sftp() as ftp:
  def inspect(folder,depth=0):
   entries=ftp.listdir_attr(folder);names={x.filename for x in entries}
   if 'api_state.json' in names:
    with ftp.open(folder+'/api_state.json') as f:state=json.load(f)
    rows.append({'path':folder,'state':state,'response_exists':'response.json' in names,'answer_exists':'answer.json' in names,'mtime':next(x.st_mtime for x in entries if x.filename=='api_state.json')})
   if depth<4:
    for x in entries:
     if stat.S_ISDIR(x.st_mode):inspect(folder+'/'+x.filename,depth+1)
  for job,run in [('creation-1793252901-ec370f70','b2df0b5b4303459f3f7e5da0'),('creation-1793252898-0afc24a2','bf69eab7ef2bef60bad0ca83'),('creation-1793252896-76293dac','1641469eb6fa9b3d5c903b88'),('creation-1793252890-7d974528','8eb1a2d6a91803a0def26bcc')]:
   inspect('/opt/monitor/geo-content/runtime/runs/'+job+'/api/runs/'+run)
 Path(__file__).with_name('four-calls.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(rows,ensure_ascii=False))
finally:client.close()
