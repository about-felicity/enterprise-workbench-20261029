import hashlib
from pathlib import Path
import zipfile
root=Path('/home/user/redroid-doubao')
archive=root/'platform-tools-linux.zip'
expected='d230f13842f60f782a8645f9c813f8f845bf36089ea7289f28c48f17979313f1'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected, 'ADB archive digest mismatch'
target=root/'linux-tools'
target.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as file:
    for name in file.namelist():
        assert (target/name).resolve().is_relative_to(target.resolve()), 'Invalid archive path'
    file.extractall(target)
for name in ['adb','fastboot']:
    (target/'platform-tools'/name).chmod(0o755)
print('Official Linux ADB archive verified and extracted')
