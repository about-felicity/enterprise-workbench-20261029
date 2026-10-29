import sys,json,shutil
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,product_images
ps={p['product_id']:p['product']['name'] for p in studio.products()}
print(json.dumps([dict(i,name=ps.get(i.get('product_id'))) for i in product_images.images()],ensure_ascii=False))
print('libreoffice',shutil.which('libreoffice'),'pdftoppm',shutil.which('pdftoppm'))
