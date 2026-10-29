"""Fetch official Linux ADB and pip bootstrap for the isolated server worker."""
import hashlib
from pathlib import Path
import requests
root=Path(__file__).resolve().parent/'artifacts/worker-tools'
root.mkdir(parents=True,exist_ok=True)
for name,url in [
    ('platform-tools-linux.zip','https://dl.google.com/android/repository/platform-tools-latest-linux.zip'),
    ('get-pip.py','https://bootstrap.pypa.io/get-pip.py')]:
    result=requests.get(url,timeout=120)
    result.raise_for_status()
    (root/name).write_bytes(result.content)
    print(name,len(result.content),hashlib.sha256(result.content).hexdigest())
