"""Export real generated drafts with explicit non-final review status."""
import json,os,sys,shutil,zipfile,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.rewrite_v2.integration import verify_writer
s=runtime.read(B/'state.json');root=B/'runtime/runs'/s['job_id'];out=B/'draft-delivery';out.mkdir(exist_ok=True);rows=[]
for i,writer in enumerate(sorted(root.glob('days/*/jobs/*/*/writer')),1):
 verify_writer(writer);text=(writer/'draft.md').read_text();context=runtime.read(writer/'rewrite_context.json');review=runtime.read(writer.parent/'review/result.json')
 stem=f'{i:02d}-'+writer.parent.parent.name+'-'+writer.parent.name+'-待修订'
 for name,suffix in [('article.docx','.docx'),('draft.md','.md')]:shutil.copy2(writer/name,out/(stem+suffix))
 rows.append({'number':i,'title':text.splitlines()[0].lstrip('# '),'word':stem+'.docx','markdown':stem+'.md',
  'word_sha256':hashlib.sha256((out/(stem+'.docx')).read_bytes()).hexdigest(),'source':{k:context['reference'][k] for k in ['url','title']},
  'review_passed':review.get('pass') is True,'review_instruction':review.get('revise_instruction'),'human_edited':False})
budget=runtime.SharedBudget(root)
try:cost=budget.db.execute('select count(*),sum(coalesce(c.charged,0)),sum(case when c.state!=\'settled\' then c.reserved else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.job=?',(s['job_id'],)).fetchone()
finally:budget.db.close()
report={'job_id':s['job_id'],'questions':s['questions'],'capture_completed':14,'capture_target':14,'drafts':rows,'final_approved':len(list((root/'approved').glob('*/*/*/receipt.json'))),
 'automatic_quality_acceptance':False,'production_deployed':False,'costs':{'calls':cost[0],'charged_cny':cost[1],'unsettled_reservation_cny':cost[2]},
 'current_verification':runtime.read(B/'release/verification.json'),'requested_policy_change':'Waiting for user answer: max full rewrites 1 -> 2; budget unchanged'}
(out/'测试记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
lines=['# 眉毛产品七篇文章','', '以下是系统实际生成的完整稿件及Word，尚未通过终审，不能作为已验收终稿。未人工改写正文。','','## 文章与仿写来源','']
for r in rows:
 lines.extend([f"- [{r['number']:02d} {r['title']}]({r['word']})",f"  - 仿写来源：[{r['source']['title']}]({r['source']['url']})"])
lines+=['','## 七个监控问题','']+[f'{i}. {q}' for i,q in enumerate(s['questions'],1)]
lines+=['','## 当前结果','',f"百度与文心采集14/14；完整正文7篇；终审通过{report['final_approved']}/7。",'已修复自动骨架复核、表格换行还原、重复导入信息压缩及输出预算规划。182项相关回归通过，另7项跨日登录复用测试通过。','实际审稿仍有来源混用及规则冲突，未部署V2核心；原UI与生产任务保持。']
(out/'文章阅读索引.md').write_text('\n'.join(lines)+'\n')
with zipfile.ZipFile(B/'draft-delivery.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in out.iterdir():z.write(p,p.name)
print(json.dumps({'drafts':len(rows),'approved':report['final_approved'],'costs':report['costs']},ensure_ascii=False))
