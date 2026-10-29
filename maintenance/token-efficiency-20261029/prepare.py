import tarfile
from pathlib import Path
w=Path(__file__).resolve().parents[2];d=Path(__file__).parent
with tarfile.open(d/'candidate.tar.gz','w:gz') as t:
 for p,n in [(w/'geo-source-card-collectors/geo_source_cards/rewrite_v2/full_writer.py','full_writer.py'),(d/'test_prompt_efficiency.py','test_prompt_efficiency.py'),(w/'geo-source-card-collectors/tests/test_rewrite_v2.py','test_rewrite_v2.py')]:t.add(p,arcname=n)
