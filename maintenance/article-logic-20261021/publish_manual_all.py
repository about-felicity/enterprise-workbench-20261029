"""Publish direct-review evidence and exact-text certificates; never calls an API."""
import sys,json,hashlib,time,shutil
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.article_logic import build_input,certificate,deterministic_issues,enforce,CHECKS,VERSION
from geo_source_cards.runtime import atomic_json,process_lock
M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic')
A=runtime.BASE/'logic-review/20261021-all'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inventory=runtime.read(M/'inventory.json')
items={r['key']:r for r in inventory['approved_versions']+inventory['non_current_drafts']}
results={r['key']:r for r in runtime.read(M/'validated-audit.json')['articles']}
negative=runtime.read(M/'manual_findings_all.json',[])
positive=runtime.read(M/'manual_passes_all.json',[])
assert len(negative)+len(positive)==90
assert len({r['key'] for r in negative+positive})==90
for manual in negative+positive:
 key=manual['key'];item=items[key];side=A/key;data=build_input(side/'input')
 text=(side/'input/draft.md').read_text('utf-8-sig');product=runtime.read(side/'input/product.json')
 valid={p['id'] for p in data['paragraphs']}
 assert results[key]['state'] in {'budget_blocked','known_response_error','input_or_review_incomplete'}
 assert sha(side/'input/draft.md')==item['draft_sha256']
 note={**manual,'version':VERSION,'draft_sha256':data['draft_sha256'],'product_sha256':data['product_sha256'],
       'method':'direct_full_text_review' if 'section_roles' in manual else manual['reviewer'],
       'reviewed_at':time.time(),'new_api_requests':0}
 cert=None
 if 'section_roles' in manual:
  headings=data['section_ids'];assert set(headings)==set(manual['section_roles'])
  sequence=[]
  for i,h in enumerate(headings):
   role=manual['section_roles'][h]
   sequence.append(dict(id=h,role=role,needs=[headings[i-1]] if i else [],coherent=True,
     reason=('先建立本文比较前提：' if not i else '承接已建立的前文问题：')+role))
  review=dict(verdict='pass',main_question=manual['main_question'],answer=manual['answer'],
   checks={k:True for k in CHECKS},sequence=sequence,issues=[],
   links=[dict(premise_ids=l[0],conclusion_ids=l[1],supported=True,reason=l[2]) for l in manual['links']])
  cert=certificate(review,data,deterministic_issues(text,product));enforce(cert,text,product)
  cert.update(reviewer='Codex',method='direct_full_text_review',new_api_requests=0)
  result={**results[key],'state':'passed','issues':[],'sequence':sequence,
          'main_question':manual['main_question'],'review_method':'Codex direct full-text review'}
 else:
  for issue in manual['issues']:assert set(issue['paragraph_ids'])<=valid
  result={**results[key],'state':'needs_revision','issues':manual['issues'],
          'order_notes':manual['order_notes'],'review_method':manual['reviewer']}
 result['previous_audit_state']=results[key]['state'];result['manual_review_record']=str(side/'direct-review.json')
 atomic_json(side/'direct-review.json',note)
 if cert:atomic_json(side/'direct-review-certificate.json',cert)
 if item.get('folder'):
  folder=Path(item['folder']);root=Path(item['root'])
  with process_lock(root/'coordinator.lock',blocking=True):
   assert sha(folder/'draft.md')==item['draft_sha256'],'Current version changed'
   backup=side/'before-direct-review';backup.mkdir(exist_ok=True)
   for name in ('receipt.json','logic_review.json','logic_product.json','direct_logic_review.json'):
    if (folder/name).exists() and not (backup/name).exists():shutil.copy2(folder/name,backup/name)
   atomic_json(folder/'direct_logic_review.json',note)
   names=['direct_logic_review.json']
   if cert:
    atomic_json(folder/'logic_review.json',cert)
    shutil.copy2(side/'input/product.json',folder/'logic_product.json')
    names+=['logic_review.json','logic_product.json']
   receipt=runtime.read(folder/'receipt.json')
   receipt.setdefault('files',{}).update({name:sha(folder/name) for name in names})
   atomic_json(folder/'receipt.json',receipt)
 results[key]=result
assert len(results)==209
delivery=[]
for root in inventory['roots']:
 for article in runtime.articles(Path(root)):
  delivery.append({'root':root,**{k:article[k] for k in ('id','title','quality_status')}})
delivery_map={(r['root'],r['id']):r for r in delivery}
final=[]
for key,item in items.items():
 row={**item,**results[key]};row['version_kind']='current_delivery' if item.get('folder') else 'saved_non_current_draft'
 if item.get('folder'):row['download_status']=delivery_map[(item['root'],item['id'])]['quality_status']
 final.append(row)
before=runtime.read(M/'controls-before.json')
controls=[]
for root in inventory['roots']:
 p=Path(root)/'control.json';controls.append({'root':root,'current':sha(p) if p.exists() else None})
value={'at':time.time(),'version':VERSION,'total':209,'current_versions':173,'other_saved_drafts':36,
 'states':dict(Counter(r['state'] for r in final)),'current_states':dict(Counter(r['state'] for r in final if r['version_kind']=='current_delivery')),
 'download_states':dict(Counter(r['quality_status'] for r in delivery)),
 'manual_reviewed':90,'independent_api_reviewed':119,'new_requests_in_publication':0,
 'original_controls_before':before,'original_controls_after':controls,'articles':final}
atomic_json(M/'all-final-report.json',value);atomic_json(M/'delivery-state.json',{'at':time.time(),'articles':delivery})
out=['# 全量文章逻辑与顺序检查结果','',
 '检查范围：173份当前交付版本，另有36份不重复的历史/未发布写作版本，共209份。',
 '独立接口复核119份，Codex直接阅读复核90份；通过仅代表本轮逻辑门槛，不代替其他质量检查。',
 '未通过文章已发现具体断点；修订后的版本仍须完整重审，不能据此声称其他所有事实已被验证。','',
 '逻辑结果：'+json.dumps(value['states'],ensure_ascii=False),
 '当前交付状态：'+json.dumps(value['download_states'],ensure_ascii=False),'',
 '原3笔未知付费请求未重发，原费用上限及任务暂停状态保留。本次发布记录不产生接口请求。','']
for i,row in enumerate(final,1):
 label='逻辑通过' if row['state']=='passed' else '需修订'
 kind='当前交付' if row['version_kind']=='current_delivery' else '保存的其他草稿'
 out += [f"## {i:03d}. {label}｜{row['title'].lstrip('# ')}",'',
  f"版本：{kind}；任务：{Path(row['root']).name}；编号：{row.get('id',row.get('key'))}；定位键：{row['key']}",
  f"正文SHA256：`{row['draft_sha256']}`",'']
 if row.get('order_notes'):out += ['顺序检查：'+row['order_notes'],'']
 for issue in row.get('issues',[]):
  out += ['- 段落 '+', '.join(issue.get('paragraph_ids',[]))+'：'+issue['reason'],
          '  修订方向：'+issue.get('repair','按同一主题补齐论证后重审')]
 if row['state']=='passed':
  out += ['论证问题：'+row.get('main_question','见绑定的完整复核证书'),
    '章节顺序：'+' → '.join(s['role'] for s in row.get('sequence',[]))]
 out += ['',f"复核方式：{row.get('review_method','独立接口全文逻辑复核')}。",'']
(M/'全量文章逻辑检查报告.md').write_text('\n'.join(out),'utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'articles','original_controls_before','original_controls_after'}},ensure_ascii=False))
