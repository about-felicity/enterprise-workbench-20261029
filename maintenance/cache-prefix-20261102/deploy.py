import ast,json,hashlib,tarfile,tempfile,shutil,os
from pathlib import Path
w=Path('/opt/monitor/maintenance/cache-prefix-20261102');w.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/cache-prefix-20261102.tar.gz') as t:
 assert all(not p.name.startswith('/') and '..' not in Path(p.name).parts for p in t.getmembers());t.extractall(w)
row=json.loads((w/'manifest.json').read_text())['files'][0];live=Path(row['server']);candidate=w/'full_writer.py'
assert hashlib.sha256(live.read_bytes()).hexdigest()==row['before']
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==row['sha256']
source=candidate.read_text();compile(source,str(candidate),'exec')
tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='serialize_writer_data')
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False))
ns={'json':json,'read':lambda p:json.loads(p.read_text()),'atomic_json':write}
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(candidate),'exec'),ns);serialize=ns['serialize_writer_data']
with tempfile.TemporaryDirectory(dir=w) as temp:
 base=Path(temp)
 def folder(name):p=base/name;p.mkdir();return p
 a={'skeleton':{'z':2,'a':1},'material':{'raw_product':{'name':'产品','facts':[{'text':'事实','approved':True}],'raw_source_text':'完整知识库'*100,'brand':'品牌'}},'assignment':{'name':'甲'}}
 b={'assignment':{'name':'甲'},'material':{'raw_product':dict(reversed(list(a['material']['raw_product'].items())))},'skeleton':{'a':1,'z':2}}
 first=serialize(a,folder('a'));assert json.loads(first)==a
 assert first==serialize(b,folder('b'))
 assert first.index('raw_source_text')<first.index('facts')
 assert a['material']['raw_product']['name']=='产品'
 p=folder('v1');write(p/'prompt_format.json',{'protocol':'product-prefix-compact-v1'})
 expected=json.dumps({'material':a['material'],**{k:v for k,v in a.items() if k!='material'}},ensure_ascii=False,separators=(',',':'))
 assert serialize(a,p)==expected
 for file in ['api_state.json','request.json','response.json']:
  p=folder(file);write(p/file,{})
  assert serialize(a,p)==json.dumps(a,ensure_ascii=False)
  assert not (p/'prompt_format.json').exists()
 p=folder('unknown');write(p/'prompt_format.json',{'protocol':'bad'})
 try:serialize(a,p)
 except ValueError:pass
 else:raise AssertionError('Unknown format must fail closed')
 # Changed source stays visible and produces a different request, never stale reuse.
 b['material']['raw_product']['raw_source_text']='更新后的知识库'
 assert first!=serialize(b,folder('changed'))
print('LOSSLESS_CANONICAL_PREFIX_AND_LEGACY_RECOVERY_TESTS_PASS',flush=True)
shutil.copy2(live,w/'full_writer.before.py');tmp=live.with_suffix('.cache.tmp');shutil.copy2(candidate,tmp);tmp.chmod(live.stat().st_mode);os.replace(tmp,live)
assert hashlib.sha256(live.read_bytes()).hexdigest()==row['sha256']
(w/'release.json').write_text(json.dumps({'files':[row]}))
print('DEPLOYED_AND_HASH_VERIFIED_NO_PAID_TEST_CALLS',flush=True)
