import json,sys,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards import daily_editorial as d
from geo_source_cards.api_worker import Worker
from geo_source_cards.pipeline_control import event
from geo_source_cards.reference_design import design
from geo_source_cards.product_identity import bind as bind_product
from geo_source_cards.source_contract import bind as bind_source
from geo_source_cards.staged_editorial import prepare
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');proof=m/'recover-v3.json'
assert not proof.exists()
c=d.read(r/'control.json');a=d.read(r/'api/active.json')
assert c.get('reason')=='research_quality_gate_failed' and c.get('revision')==3 and c.get('paused_epoch')==1792556764.7568088
assert a['state']=='AUTHORIZING' and a['ticket']=='08e500f1f2ee543b33ea76fc'
assert not any((r/'api/runs'/a['run_id']).rglob('api_state.json'))
backup=m/'recovery-v3';backup.mkdir(exist_ok=True)
for n in ['control.json','api/active.json','days/2026-10-21/category_plan.json','days/2026-10-21/article_allocation.json']:
 p=r/n;dst=backup/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
j=d.read(r/'queue'/a['ticket']/'ticket.json')
if not (backup/'writer02-ticket').exists():shutil.copytree(r/'queue'/j['id'],backup/'writer02-ticket')
else:assert d.read(backup/'writer02-ticket/ticket.json')==j
# This old writer was never sent, not a paid unknown.
w=Worker(r,None);w.failed(j,{**a,'execution':j['execution']},'research_material_insufficient',detail='主参考缺少产品中性资料，未发送任何writer请求；针对同一已采来源重做研究')
research02=next(d.read(p) for p in (r/'queue').glob('*/ticket.json') if d.read(p)['stage']=='research' and d.read(p)['meta'].get('category')=='排行类' and d.read(p)['meta'].get('number')==2)
reason='肌养堂原研究仅引用标题导致无中性事实。必须从同一主参考的产品对应R1完整段落中提取明确规格50g、价格148元或具体成分名称，至少一个对应正文R1引文；不得重复只引用全肤质四效标题、任何夸张功效百分比及人群保证。所有竞品均提取对应R编号的具体中性资料，保留原文名单。'
res=d.repair_research(r,research02,reason);new02=res['ticket']
j=d.read(r/'queue'/j['id']/'ticket.json');atomic_json(r/'queue'/j['id']/'ticket.json',{**j,'state':'revision_requested','replaced_by':new02,'resolution':'known_unsent_preflight_replaced_by_same_source_research'})
# Preserve the bad category-as-product article and all paid outputs.
bad=r/'approved/2026-10-21/排行类/01';assert bad.exists();wordsha=d.file_hash(bad/'article.docx')
quarantine=r/'quarantine/source-category-20261021/排行类/01';quarantine.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(bad),str(quarantine))
atomic_json(r/'revocations'/('category-'+wordsha[:24]+'.json'),{'word_sha256':wordsha,'reason':'把面膜类型误作为独立产品，退出成稿并换真正的多产品主参考','at':time.time(),'quarantine':str(quarantine.relative_to(r))})
# New sibling inputs keep old source contracts immutable. Same article number/budget.
day=r/'days/2026-10-21';sources=d.read(day/'media_articles.json')
url='https://fashion.sohu.com/a/1087273182_122989824';source=next(s for s in sources if s['url']==url)
blue=bind_source(bind_product(design([source],'排行类'),d.read(day/'product.json')),[source],'2026-10-21')
assert len(blue['products'])==4
loc=day/'jobs/排行类/01-source-replacement';loc.mkdir()
records=[{'model':'daily_media','question':'保湿面膜选购','body':'多产品逐款介绍','sources':[source]}]
atomic_write(loc/'articles.jsonl',''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in records))
prepare(loc/'research',loc/'articles.jsonl',day/'product.json',reference_design=blue)
oldcat=d.read(day/'jobs/排行类/01/category.json');atomic_json(loc/'category.json',{**oldcat,'angle':source['article']['title'],'source_urls':[url],'replaces_source':d.read(day/'jobs/排行类/01/research/research_input.json')['reference_design']['primary_url']})
new01=d.publish_ticket(r,'research',loc/'research',['research_input.json','research_task.txt'],['research_result.json'],{'date':'2026-10-21','category':'排行类','number':1,'source_replacement':1})
for p in (r/'queue').glob('*/ticket.json'):
 v=d.read(p)
 if v['meta'].get('category')=='排行类' and v['meta'].get('number')==1 and v['id']!=new01:
  assert v['state'] not in ['claimed','pending'];shutil.copytree(p.parent,backup/'old01-tickets'/v['id']);atomic_json(p,{**v,'previous_state':v['state'],'state':'revision_requested','replaced_by':new01,'resolution':'category_source_rejected'})
plan=d.read(day/'category_plan.json')
for v in plan['planned']:
 if v['category']=='排行类' and v['number'] in [1,2]:v['replaces_ticket']=v['ticket'];v['ticket']=new01 if v['number']==1 else new02
atomic_json(day/'category_plan.json',plan)
allocation=d.read(day/'article_allocation.json');old=allocation['selected']['排行类'][0];allocation['selected']['排行类'][0]=url;allocation.setdefault('source_replacements',[]).append({'before':old,'after':url,'reason':'类型冒充产品'});atomic_json(day/'article_allocation.json',allocation)
with process_lock(r/'control.lock',blocking=True):
 assert d.read(r/'control.json')==c
 atomic_json(r/'control.json',{'paused':False,'revision':4,'resumed_epoch':time.time(),'resolved_system_pause':c,'reason':'source_preflight_recovery'})
event(r,'quality','修复纯类型名单误判及单篇资料阻断；只解除本次系统质量暂停，原费用保留',replacements=[new01,new02])
proof.write_text(json.dumps({'at':time.time(),'replacements':[new01,new02],'old_article_withdrawn':True,'paid_unknowns_replayed':False,'original_budgets_preserved':True},ensure_ascii=False,indent=2));print(proof.read_text())
