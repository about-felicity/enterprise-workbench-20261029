from pathlib import Path
import sqlite3,subprocess
for n in [3,4]:
 r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-smoke')
 with sqlite3.connect(r/'tasks.sqlite') as d:
  print(n,d.execute('select * from events order by rowid desc limit 9').fetchall())
 print(list(p.name for p in r.glob('*binding*')))
code="""import sys,uiautomator2 as u,xml.etree.ElementTree as E
d=u.connect(sys.argv[1]);root=E.fromstring(d.dump_hierarchy());ls=root.findall(".//node[@resource-id='com.larus.nova:id/message_list']");print('rows',[(len(l),[(len(row),[(n.get('resource-id','').split('/')[-1],n.get('text','')[:36]) for n in row.iter() if n.get('text') or n.get('resource-id','').endswith('mask_container')]) for row in l]) for l in ls]);print([(n.get('resource-id','').split('/')[-1],n.get('content-desc'),n.get('text')) for n in root.iter('node') if n.get('resource-id','').endswith(('back_icon','input_text','action_send','create_new_cvs'))])"""
for n in [3,4]:
 print(n,subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code,f'127.0.0.1:556{n}'],capture_output=True,text=True).stdout)
