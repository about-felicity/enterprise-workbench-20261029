import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.daily_editorial import withdraw
from geo_source_cards.consumer_voice import issues
root=runtime.job_root('creation-1792479954-8a96bc88');folder=root/'approved/2026-10-20/科普类/05'
report=Path('/opt/monitor/geo-capture/maintenance/20261021-content-quality/pilot.json')
assert not report.exists(),'Already issued; inspect existing request'
assert not runtime.read(root/'control.json').get('paused')
assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
assert issues((folder/'draft.md').read_text())
reason='用户抽查退回：正文反复以原文/参考文章/知识库为主语，写成来源解读和审计报告。必须整体修订为可独立阅读的消费科普文章，直接围绕眼霜与面霜区别回答读者问题。保留有证据的内容、主题和产品举例，不只是删掉或替换原文二字；不使用相关资料/资料指出作替身。未核实功效/机制省略，不能删除归属后升级为事实。原文链接、核验状态、源句等仅放溯源附件。正文不堆免责声明或编排说明。按consumer-voice-v1及原篇幅、证据、预算门槛重新写作和独立审稿。'
result=withdraw(root,'2026-10-20','科普类',5,reason)
runtime.atomic_json(report,{'at':time.time(),**result,'job':root.name,'article':'2026-10-20/科普类/05'})
print(json.dumps(result,ensure_ascii=False))
