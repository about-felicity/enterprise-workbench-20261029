"""Install only the independent browser test and its loopback receiver."""
import json,os,signal,subprocess,zipfile
from pathlib import Path
root=Path('/opt/monitor/geo-deepseek-browser-test');root.mkdir(exist_ok=True);root.chmod(0o700)
# The earlier slow installer belongs exclusively to this test; stop its verified processes.
for pid in (52817,52743,52735):
    path=Path('/proc')/str(pid)/'cmdline'
    if path.exists():
        command=path.read_bytes()
        if b'playwright' in command and (b'install\0chromium' in command or b'oopBrowserDownload.js' in command):
            os.kill(pid,signal.SIGTERM)
for archive,dest in [('/tmp/geo-deepseek-browser-test-source.zip',root),('/tmp/geo-browser-test-chrome-linux64.zip',root/'chromium')]:
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path=(dest/item.filename).resolve()
            if not path.is_relative_to(dest.resolve()):raise ValueError('Invalid archive member')
            z.extract(item,dest)
            mode=item.external_attr>>16
            if mode&0o111 and path.is_file():path.chmod(0o755)
chrome=root/'chromium/chrome-linux64/chrome';chrome.chmod(0o755)
for name,command,memory in [
 ('geo-deepseek-browser-test-receiver',f'/usr/bin/python3 -u {root}/project/local_receiver.py',128),
 ('geo-deepseek-browser-test',f'/opt/monitor/geo-capture/venv/bin/python -u -B {root}/browser_test.py',1200)]:
    unit=f'''[Unit]
Description=Independent DeepSeek headless extension test
After=network-online.target
[Service]
Type=simple
WorkingDirectory={root}
ExecStart={command}
Environment=DEEPSEEK_MONITOR_DATA_DIR={root}/data
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=10
MemoryHigh={int(memory*.8)}M
MemoryMax={memory}M
TasksMax=512
UMask=0077
[Install]
WantedBy=multi-user.target
'''
    Path('/etc/systemd/system',name+'.service').write_text(unit)
subprocess.run(['systemctl','daemon-reload'],check=True)
# Test services are deliberately not enabled for boot and not registered as daily GEO lanes.
for name in ('geo-deepseek-browser-test-receiver','geo-deepseek-browser-test'):
    subprocess.run(['systemctl','start',name],check=True,timeout=25)
print(json.dumps({'root':str(root),'chrome':str(chrome),'test_only':True,'auto_question':False}))
