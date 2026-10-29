import json,sys,shutil,tarfile
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from multi_run import STATE,root_for
from creation import runtime
from geo_source_cards.runtime import atomic_json
out=BASE/'article-delivery-20261024'
for item in STATE['products']:
    root=root_for(item);dest=out/item['key'];dest.mkdir(parents=True,exist_ok=True)
    for writer in (root/'days'/item['date']/'jobs').glob('*/01/writer'):
        for name in ('draft.md','article.docx','rewrite_context.json','rewrite_material.json','product.json'):
            if (writer/name).exists():shutil.copy2(writer/name,dest/name)
        if (writer.parent/'review/result.json').exists():shutil.copy2(writer.parent/'review/result.json',dest/'review.json')
    atomic_json(dest/'runtime-status.json',runtime.read(BASE/'multi-results'/item['key']/'runtime-status.json'))
with tarfile.open(BASE/'article-delivery-20261024.tar.gz','w:gz') as archive:archive.add(out,arcname='raw-system-output')
print(str(BASE/'article-delivery-20261024.tar.gz'))
