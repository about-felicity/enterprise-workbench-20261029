import tarfile,json,pathlib,hashlib
p=pathlib.Path('/home/user/redroid-doubao/backups/hpe14-20261006/redroid13-hpe14-image.tar')
with tarfile.open(p) as t:
 m=json.load(t.extractfile('manifest.json'));print(m)
 for e in m:
  c=t.extractfile(e['Config']).read();print('configsha',hashlib.sha256(c).hexdigest());j=json.loads(c);print({k:j.get(k) for k in ['created','architecture','os','rootfs']});print('history-last',j.get('history',[])[-1:])
