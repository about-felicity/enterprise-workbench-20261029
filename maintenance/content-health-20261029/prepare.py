import tarfile
from pathlib import Path
w=Path(__file__).resolve().parents[2];d=Path(__file__).parent
with tarfile.open(d/'candidate.tar.gz','w:gz') as t:
 for p,n in [(w/'geo-monitor-deploy/creation/supplement.py','supplement.py'),(d/'test_rotation.py','test_rotation.py'),(w/'maintenance/automatic-supplement-20261028/test_supplement.py','test_original.py')]:t.add(p,arcname=n)
