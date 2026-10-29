import zipfile
from pathlib import Path
base=Path(__file__).resolve().parents[3]/'geo-source-card-collectors'
out=Path(__file__).with_name('engine-product-patch.zip')
modules=['product_identity.py','reference_design.py','daily_editorial.py','genre_outline.py','genre_length.py','genre_prompts.py']
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for name in modules:z.write(base/'geo_source_cards'/name,'geo_source_cards/'+name)
 for name in ['test_product_identity.py','test_genre_pools.py','test_genre_length.py','test_reference_design.py']:
  z.write(base/'tests'/name,'tests/'+name)
print(str(out))
