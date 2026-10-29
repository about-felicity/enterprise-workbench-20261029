import sys,json
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio
for p in studio.products():
 if '染发' in p['product']['name']:print(json.dumps({'id':p['product_id'],'version':p['version'],'name':p['product']['name'],'brand':p['product']['brand'],'source':p.get('word_source')},ensure_ascii=False))

