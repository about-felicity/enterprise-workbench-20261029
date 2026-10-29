"""Explicit quality withdrawal; never resume or mutate user-paused task control."""
import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.daily_editorial import withdraw
from geo_source_cards.consumer_voice import issues
R=Path('/opt/monitor/geo-capture/maintenance/20261021-content-quality')
pilot='--pilot' in sys.argv
new_pilot='--pilot2' in sys.argv
pilot=pilot or new_pilot
report=R/('structured-pilot.json' if new_pilot else 'compact-pilot.json' if pilot else 'rewrite-queue.json')
assert not report.exists(),'Already queued; read existing queue report'
report_data={'at':time.time(),'queued':[],'held':[],'controls_unchanged':True,'old_captures_and_costs_preserved':True}
reason='用户要求修复正文，按consumer-voice-v1整体重写为面向读者的独立文章。不得写成原文/参考文章/知识库解读；也不把原文替换为相关资料。保留有依据的主题与产品信息，省略无依据主张、用法泛化和互相矛盾的品类概括；首段独立建立问题，不用还有一层等承接语起头。溯源只放附件。使用精简的consumer_rewrite写作与独立审稿合同；篇幅、质量和原预算不变。'
for path in sorted((runtime.BASE/'runs').glob('*/job.json'),reverse=True):
 root=path.parent;control=runtime.read(root/'control.json')
 if pilot and root.name!=('creation-1792526406-8f93ccca' if new_pilot else 'creation-1792479954-8a96bc88'):continue
 for a in runtime.articles(root):
  if pilot and a['id']!=('2026-10-21/科普类/04' if new_pilot else '2026-10-20/科普类/05'):continue
  if not a.get('quality_issues'):continue
  if control.get('paused'):
   report_data['held'].append({'job':root.name,'id':a['id'],'reason':'user_or_existing_pause_preserved'});continue
  active=runtime.read(root/'api/active.json')
  assert active.get('state') in (None,'SUBMITTED'),root.name
  day,category,number=a['id'].split('/')
  result=withdraw(root,day,category,int(number),reason)
  ticket=root/'queue'/result['ticket']/'ticket.json';t=runtime.read(ticket)
  runtime.atomic_json(ticket,{**t,'meta':{**t['meta'],'consumer_rewrite':True,'consumer_rewrite_version':'v1','auto_repair_round':0,'assisted_repair_round':0}})
  report_data['queued'].append({'job':root.name,'id':a['id'],'ticket':result['ticket'],'old_title':a['title'],'archive':result['archive']})
  runtime.atomic_json(report,report_data)
  if pilot:break
 assert runtime.read(root/'control.json')==control,'Task control changed during queue operation'
runtime.atomic_json(report,report_data)
print(json.dumps({'queued':len(report_data['queued']),'held':len(report_data['held']),'controls_unchanged':True},ensure_ascii=False))
