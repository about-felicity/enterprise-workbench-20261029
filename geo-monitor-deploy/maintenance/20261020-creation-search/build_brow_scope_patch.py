import zipfile
from pathlib import Path
ws=Path(__file__).resolve().parents[3];out=Path(__file__).with_name('brow-scope-patch.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for name in ['daily_editorial.py','genre_pools.py','source_scope.py','reference_design.py']:
        z.write(ws/'geo-source-card-collectors/geo_source_cards'/name,'engine/geo_source_cards/'+name)
    for name in ['test_article_allocation.py','test_article_quality.py','test_genre_pools.py','test_reference_design.py','test_product_identity.py','test_genre_length.py','test_auto_repair.py','test_source_scope.py']:
        z.write(ws/'geo-source-card-collectors/tests'/name,'tests/'+name)
print(out)
