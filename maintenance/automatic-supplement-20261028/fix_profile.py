from pathlib import Path
p=Path('geo-monitor-deploy/creation/materials.py');s=p.read_text('utf8').replace("       private_dir(resources['lock'].parent)","       if supplement_origin(ROOT)==ROOT:private_dir(resources['lock'].parent)\n       elif not resources['lock'].parent.is_dir():raise ValueError('Original capture profile has not been initialized')")
p.write_text(s,encoding='utf8')
