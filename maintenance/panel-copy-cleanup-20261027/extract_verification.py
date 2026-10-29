from pathlib import Path
import tarfile
D=Path(__file__).resolve().parent
with tarfile.open(D/'verification.tar') as archive:
 for item in archive:
  if not item.isfile():continue
  name=Path(item.name).name
  mapped={'模型总览.png':'overview.png','内容创作中心.png':'creation.png','品牌与产品.png':'brands.png','信源洞察.png':'sources.png','report.json':'browser-report.json'}
  if name in mapped:(D/'verification'/mapped[name]).write_bytes(archive.extractfile(item).read())
