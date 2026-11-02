import ast,collections,csv,hashlib,json,re,sqlite3,sys,html as html_module
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
now=datetime.now(ZoneInfo('Asia/Shanghai'));end=now.date();start=end-timedelta(days=14)
out=Path('/tmp/geo-source-length-20261030');out.mkdir(exist_ok=True)
def canonical(u):
 try:
  p=urlsplit(u);host=(p.hostname or '').lower().removeprefix('www.')
  q=parse_qsl(p.query,keep_blank_values=True)
  if host=='baijiahao.baidu.com' and dict(q).get('id'):q=[('id',dict(q)['id'])]
  else:q=[(k,v) for k,v in q if k.lower() not in {'refer','from','source','spm','srsltid','share_token'} and not k.lower().startswith('utm_')]
  return urlunsplit(('https',host,p.path.rstrip('/') or '/',urlencode(sorted(q)),''))
 except ValueError:return u
# Use the production body cleanup rules without importing a live service.
tree=ast.parse(Path('/opt/monitor/doubao_source_content_worker.py').read_text());selected=[]
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in {'normalize_text','primary_article_text'}:selected.append(node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_BODY_END_PREFIXES' for t in node.targets):selected.append(node)
ns={'re':re,'html_module':html_module};exec(compile(ast.Module(body=selected,type_ignores=[]),'body_cleanup','exec'),ns)
records={};bad=0;duplicate_flags=0
for path in Path('/opt/monitor/geo-capture/batches').glob('*/results.jsonl'):
 for line in path.open():
  if not line.strip():continue
  try:r=json.loads(line)
  except ValueError:bad+=1;continue
  if r.get('model') not in {'baidu_ai','wenxin_card'}:continue
  try:
   captured=datetime.fromisoformat(str(r['captured_at']).replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai'))
  except (ValueError,KeyError):continue
  if not start<=captured.date()<=end:continue
  if r.get('duplicate_of'):duplicate_flags+=1
  identity=(r['model'],r.get('task_id') or (r.get('question'),r.get('captured_at'),r.get('round')))
  records[identity]=r
articles={};capture_rows=[]
for i,r in records.items():
 day=str(r['captured_at'])[:10];model=r['model'];question=r.get('question','');seen=set()
 capture_rows.append({'date':day,'model':model,'question':question,'task_id':r.get('task_id',''),'source_count':len(r.get('sources',[])),'source_complete':r.get('source_capture_complete'),'duplicate_answer':bool(r.get('duplicate_of'))})
 for s in r.get('sources',[]):
  url=str(s.get('url') or s.get('href') or '').strip()
  if not url.startswith(('http://','https://')):continue
  key=canonical(url)
  if key in seen:continue
  seen.add(key)
  a=articles.setdefault(key,{'url':url,'canonical_url':key,'title':s.get('title',''),'events':[]})
  a['events'].append({'day':day,'model':model,'question':question,'source_complete':r.get('source_capture_complete'),'duplicate_answer':bool(r.get('duplicate_of'))})
print('CAPTURES',len(records),'UNIQUE_LINKS',len(articles),flush=True)
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
  if a['body_chars']<80:a['status']='too_short'
  # Inspect a bounded sample separately for page chrome and truncation.
  if len(list(out.glob('sample-*.txt')))<12:
   (out/('sample-'+str(len(list(out.glob('sample-*.txt'))))+'.txt')).write_text(json.dumps({'url':a['url'],'title':row[0],'body_chars':a['body_chars']},ensure_ascii=False)+'\n'+text[:700],encoding='utf8')
payload={'window_start':str(start),'window_end':str(end),'as_of':now.isoformat(),'bad_json_lines':bad,'duplicate_answer_records_retained':duplicate_flags,'captures':capture_rows,'articles':list(articles.values())}
(out/'dataset.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf8')
print('STATUS',dict(collections.Counter(a['status'] for a in articles.values())),flush=True)
print('OUTPUT',str(out/'dataset.json'),(out/'dataset.json').stat().st_size,flush=True)


