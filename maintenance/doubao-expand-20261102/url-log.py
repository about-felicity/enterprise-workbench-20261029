from pathlib import Path
for n in (3,4):
 p=Path(f'/tmp/doubao-panel-url-{n}.log');print(n,p.read_text()[-800:] if p.exists() else 'waiting')
