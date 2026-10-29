import xml.etree.ElementTree as ET
from pathlib import Path
root=ET.fromstring(Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/drawer.xml').read_text());parent={c:p for p in root.iter() for c in p}
for n in root.iter('node'):
 if n.get('text')=='眉毛增长液成分与功效说明':
  while n in parent:
   print(n.attrib);n=parent[n]
