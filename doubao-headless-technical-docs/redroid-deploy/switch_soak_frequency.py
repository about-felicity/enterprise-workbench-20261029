import pathlib,subprocess,json,datetime,time,os
r=pathlib.Path('/home/user/redroid-doubao').resolve()
assert r==pathlib.Path('/home/user/redroid-doubao')
assert not (r/'soak1h/status.json').exists(), 'Short acceptance already exists'
units=['redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service']
def running():return subprocess.check_output(['systemctl','show',*units,'-p','Id','-p','MainPID','-p','ActiveState'],text=True)
before=running()
subprocess.run(['systemctl','stop','redroid-doubao-soak24h.service'],check=True)
old=r/'soak24h'
archive=pathlib.Path('/home/user/redroid-doubao-archive')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-frequency-switch')
archive.mkdir(mode=0o700)
if old.exists():
    assert old.resolve().parent==r and not old.is_symlink()
    path=old/'status.json'
    data=json.loads(path.read_text())
    data.update(status='cancelled',cancelled_utc_epoch=time.time(),reason='User replaced 10-minute long test with 1-hour/3-minute acceptance',replacement=str(r/'soak1h'))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    os.rename(old,archive/'soak24h-10min-cancelled')
previous=r/'hpe14-export/hpe14-soak24h-start.json'
if previous.exists():os.rename(previous,archive/previous.name)
subprocess.run(['install','-m','0644',str(r/'redroid-doubao-soak24h.service'),'/etc/systemd/system/redroid-doubao-soak24h.service'],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','redroid-doubao-soak24h.service'],check=True)
after=running()
assert before==after, 'Worker/logger state changed'
print(json.dumps({'archive':str(archive),'worker_and_logger_unchanged':True,'short_duration':3600,'interval':180,'planned_short':20,'planned_long':480}))
