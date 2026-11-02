import subprocess,ast,collections,csv,hashlib,json,re,sqlite3,sys,html as html_module
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
now=datetime.now(ZoneInfo('Asia/Shanghai'));end=now.date().replace(day=15);start=end.replace(day=1)
out=Path('/tmp/geo-deepseek-length-20261030');out.mkdir(exist_ok=True)
def canonical(u):
 try:
  p=urlsplit(u);host=(p.hostname or '').lower().removeprefix('www.')
  q=parse_qsl(p.query,keep_blank_values=True)
  if host=='baijiahao.baidu.com' and dict(q).get('id'):q=[('id',dict(q)['id'])]
  else:q=[(k,v) for k,v in q if k.lower() not in {'refer','from','source','spm','srsltid','share_token'} and not k.lower().startswith('utm_')]
  return urlunsplit(('https',host,p.path.rstrip('/') or '/',urlencode(sorted(q)),''))
 except ValueError:return u
sys.path.insert(0,'/opt/monitor')
from monitor_core.owned_products import own_product_mentions,OWN_PRODUCT_RULES
# Use the production body cleanup rules without importing a live service.
tree=ast.parse(Path('/opt/monitor/doubao_source_content_worker.py').read_text());selected=[]
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in {'normalize_text','primary_article_text'}:selected.append(node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_BODY_END_PREFIXES' for t in node.targets):selected.append(node)
ns={'re':re,'html_module':html_module};exec(compile(ast.Module(body=selected,type_ignores=[]),'body_cleanup','exec'),ns)

sql="""select jsonb_build_object('model','deepseek','question',r.question,'task_id',r.run_id,'captured_at',r.finished_at,'day',r.day,'source_capture_complete',r.payload->'source_capture_complete','body_capture_complete',r.payload->'body_capture_complete','sources',coalesce((select jsonb_agg(jsonb_build_object('url',s.url,'title',s.title,'own_brand',s.own_brand,'own_products',s.payload->'own_products')) from monitor_sources s where s.model_id=r.model_id and s.run_id=r.run_id and s.production_valid is true),'[]'::jsonb)) from monitor_runs r where r.model_id='deepseek' and r.status='success' and r.day between '2026-10-01' and '2026-10-15';"""
result=subprocess.run(['docker','exec','monitor-postgres','sh','-c','psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"','sh',sql],capture_output=True,text=True,timeout=40)
assert result.returncode==0,result.stderr
records={};bad=0;duplicate_flags=0
for line in result.stdout.splitlines():
 r=json.loads(line);r['captured_at']=r.get('captured_at') or r['day']+'T00:00:00+08:00'
 records[('deepseek',r['task_id'])]=r
articles={};capture_rows=[]
for i,r in records.items():
 day=r['day'];model=r['model'];question=r.get('question','');seen=set()
 capture_rows.append({'date':day,'model':model,'question':question,'task_id':r.get('task_id',''),'source_count':len(r.get('sources',[])),'run_id':r.get('task_id'),'captured_at':r.get('captured_at'),'source_complete':r.get('source_capture_complete'),'duplicate_answer':bool(r.get('duplicate_of'))})
 for s in r.get('sources',[]):
  url=str(s.get('url') or s.get('href') or '').strip()
  if not url.startswith(('http://','https://')):continue
  key=canonical(url)
  if key in seen:continue
  seen.add(key)
  a=articles.setdefault(key,{'url':url,'canonical_url':key,'title':s.get('title',''),'events':[]})
  a.setdefault('source_titles',[]).append(s.get('title',''));a.setdefault('db_own_brand_flags',[]).append(bool(s.get('own_brand')))
  a['events'].append({'day':day,'model':model,'question':question,'run_id':r.get('task_id'),'captured_at':r.get('captured_at'),'source_complete':r.get('source_capture_complete'),'duplicate_answer':bool(r.get('duplicate_of'))})
print('CAPTURES',len(records),'UNIQUE_LINKS',len(articles),flush=True)
for a in articles.values():a['title_products']=own_product_mentions('\n'.join(a.get('source_titles',[])));a['body_products']=[];a['own_products']=list(a['title_products'])
matched=collections.defaultdict(list)
with sqlite3.connect('file:/opt/monitor/doubao_source_content.db?mode=ro',uri=True) as db:
 db.execute('pragma query_only=ON')
 for url,final,status,quality in db.execute('select url,final_url,status,extraction_quality from source_content'):
  for key in {canonical(url),canonical(final or url)}:
   if key in articles:matched[key].append((url,status,quality))
 for key,a in articles.items():
  choices=sorted(matched.get(key,[]),key=lambda x:(x[1]=='ok',x[2]=='high'),reverse=True)
  a['status']=choices[0][1] if choices else 'missing'
  if a['status']!='ok':continue
  row=db.execute('select title,content_text,text_length,extraction_quality,fetched_at from source_content where url=?',(choices[0][0],)).fetchone()
  text=ns['primary_article_text'](row[1] or '')
  a.update(body_chars=len(re.sub(r'\s+','',text)),han_chars=len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]',text)),alnum_chars=len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]',text)),raw_chars=row[2],quality=row[3],fetched_at=row[4],article_title=row[0],content_sha256=hashlib.sha256(text.encode()).hexdigest())
  a['title_products']=own_product_mentions('\n'.join(a.get('source_titles',[]))+'\n'+str(row[0] or ''));a['body_products']=own_product_mentions(text);a['own_products']=sorted(set(a['title_products'])|set(a['body_products']));a['product_evidence']={}
  for rule in OWN_PRODUCT_RULES:
   if rule['name'] not in a['own_products']:continue
   at=text.find(rule['brand']);a['product_evidence'][rule['name']]=text[max(0,at-30):at+140] if at>=0 else str(row[0] or a['title'])[:180]
  if a['body_chars']<80:a['status']='too_short'
  # Inspect a bounded sample separately for page chrome and truncation.
  if len(list(out.glob('sample-*.txt')))<12:
   (out/('sample-'+str(len(list(out.glob('sample-*.txt'))))+'.txt')).write_text(json.dumps({'url':a['url'],'title':row[0],'body_chars':a['body_chars']},ensure_ascii=False)+'\n'+text[:700],encoding='utf8')
payload={'window_start':str(start),'window_end':str(end),'as_of':now.isoformat(),'bad_json_lines':bad,'duplicate_answer_records_retained':duplicate_flags,'captures':capture_rows,'articles':list(articles.values())}
(out/'owned_dataset.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf8')
print('STATUS',dict(collections.Counter(a['status'] for a in articles.values())),flush=True)
print('OUTPUT',str(out/'owned_dataset.json'),(out/'owned_dataset.json').stat().st_size,flush=True)



