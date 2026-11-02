from pathlib import Path
for p in list(Path('/tmp/geo-source-length-20261030').glob('sample-*.txt'))[:4]:print(p.read_text()[:600])
