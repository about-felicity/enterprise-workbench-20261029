import subprocess
from pathlib import Path
s=Path('/tmp/doubao-screenshot-refs.py').read_text(encoding='utf-8-sig').replace("d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])","d(resourceId=p+'tv_title',text='推荐眼霜').click();time.sleep(1.5)").replace("shot('answer');","assert '搜索 2 个关键词' in title;shot('answer');").replace("assert get(ns(),'tv_reference_index');shot","assert any('维生素A棕榈酸酯' in x.get('text','') for x in get(ns(),'tv_reference_content'));shot")
p=Path('/tmp/doubao-eye-fourth.py');p.write_text(s);subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python',str(p),'4'],check=True)
