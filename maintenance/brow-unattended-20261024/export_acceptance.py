"""Export only unchanged, automatically approved articles and their provenance."""
import hashlib,json,os,shutil,sys,zipfile
from pathlib import Path
B=Path(__file__).resolve().parent
os.environ['GEO_CREATION_ROOT']=str(B/'runtime')
sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime,materials
from geo_source_cards.runtime import atomic_json
s=runtime.read(B/'state.json');root=runtime.job_root(s['job_id']);out=B/'delivery';out.mkdir(exist_ok=True)
articles=runtime.articles(root)
assert len(articles)==7 and all(a['quality_status']=='ready' for a in articles)
records=[]
for i,a in enumerate(articles,1):
 folder=root/'approved'/a['id'];context=runtime.read(folder/'rewrite_context.json');review=runtime.read(folder/'semantic_review.json')
 assert context['skeleton']['approval']['kind']=='automatic'
 assert review['pass'] and review['style_check']['pass'] and review['compliance_check']['pass']
 stem=f"{i:02d}-眉毛精华液文章"
 for kind,suffix in [('word','.docx'),('markdown','.md')]:
  downloaded=runtime.download(s['job_id'],a['id'],kind)
  shutil.copy2(downloaded,out/(stem+suffix))
 records.append({'number':i,'title':a['title'],'id':a['id'],'files':[stem+'.docx',stem+'.md'],
  'word_sha256':hashlib.sha256((out/(stem+'.docx')).read_bytes()).hexdigest(),
  'reference':a['primary_reference'],'automatic_skeleton_review':True,'style_review':'advisory','fact_review':True,
  'review_protocol':review.get('review_protocol'),'decision_rules':review.get('decision_rules'),
  'dismissed_review_objections':len(review.get('dismissed_findings',[])),
  'human_edited':False})
bundle=runtime.download(s['job_id'],'','bundle');shutil.copy2(bundle,out/'系统原始导出包.zip')
budget=runtime.SharedBudget(root)
try:
 costs=[dict(zip(['stage','calls','charged_cny'],row)) for row in budget.db.execute('select c.stage,count(*),sum(coalesce(c.charged,0)) from costs c join studio_cost_scopes s on s.id=c.id where s.job=? group by c.stage',(s['job_id'],))]
finally:budget.db.close()
report={'job_id':s['job_id'],'plan_id':s['plan_id'],'knowledge_source':'新眉毛产品库信息.docx','knowledge_sha256':s['source_sha256'],
 'questions':s['questions'],'capture':materials.progress(s['date'],store_root=Path(s['capture_root'])),
 'articles':records,'costs':costs,'manual_skeleton_confirmation':False,'manual_article_editing':False,
 'status':runtime.read(B/'acceptance-status.json'),'regression':runtime.read(B/'release/verification.json')}
atomic_json(out/'验收记录.json',report)
lines=['# 眉毛精华液七问题自动生产测试','', '知识库：新眉毛产品库信息.docx。正文由系统生成、定点修改，经独立内容审核和程序校验；未人工改写。工程修复期间有人工干预，下一自然日完整运行另行观察。','','## 最终文章','']
for row in records:
 lines.append(f"- [{row['number']:02d} {row['title']}]({row['files'][0]})")
 ref=row['reference'];lines.append('  - 仿写来源：'+json.dumps(ref,ensure_ascii=False))
lines+=['','## 监控问题','']+[f'{i}. {q}' for i,q in enumerate(s['questions'],1)]
(out/'阅读索引.md').write_text('\n'.join(lines)+'\n')
with zipfile.ZipFile(B/'delivery.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in out.iterdir():z.write(p,p.name)
print(json.dumps(report,ensure_ascii=False,indent=2))
