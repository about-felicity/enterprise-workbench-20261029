import sys,json
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio
rows=[]
for p in studio.products():
 product=p.get('product',{})
 rows.append({'name':product.get('name'),'brand':product.get('brand'),'product_id':p.get('product_id'),'facts':len(product.get('facts',[])),'updated_at':p.get('updated_at')})
print(json.dumps({'count':len(rows),'products':rows},ensure_ascii=False,indent=2))
