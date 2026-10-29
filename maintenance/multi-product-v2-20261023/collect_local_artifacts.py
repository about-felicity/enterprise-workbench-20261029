import json,shutil,tarfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
target=W/'outputs/multi-product-v2-20261023'
with tarfile.open(D/'multi-results-final.tar.gz','r:gz') as archive:
    archive.extractall(D/'downloaded',filter='data')
shutil.copytree(D/'downloaded/multi-results',target,dirs_exist_ok=True)
note='''> **2026-10-23 18:35（北京时间）：三产品 V2 实测已完成百度/文心12/12次采集，共232条来源记录（未去重）。三份完整Word及独立素材缓存核验通过，3份新范文骨架已解析并提出校正稿，待用户按V2.0第3.1.7条确认；尚未生成这三篇全文，不能宣称端到端质量通过。真实6次模型调用已结算约0.070967元，预算未提高。修复并定点部署采集CLI：冷却释放共享锁、失败首题不再拖住同轮后续题；67项相关回归通过。V2核心仍隔离验证、UI未改。见[三产品测试进度](outputs/multi-product-v2-20261023/测试进度.md)与[骨架校验稿](outputs/multi-product-v2-20261023/骨架校验.md)。**

'''
for name in ('CURRENT_PROJECT_HANDOFF.md','PROJECT_STATUS.md'):
    path=W/name;old=path.read_text('utf8')
    if note not in old:path.write_text(note+old,encoding='utf8')
control=W/'SOURCE_CONTROL.md';old=control.read_text('utf8')
entry='''> 2026-10-23 18:35：采集CLI锁释放与同轮失败题调度修复已定点部署。服务器实读SHA与本地一致，仅更新该文件的恢复包、映射和两份快照；557个快照条目校验无错。未将尚未部署的V2文章候选写入生产快照。详见 `maintenance/multi-product-v2-20261023/capture-fairness-deployment.json` 与三产品测试报告。

'''
if entry not in old:control.write_text(entry+old,encoding='utf8')
verification=json.loads((target/'verification.json').read_text('utf8'))
print(json.dumps({'captures':sum(len(x['captures']) for x in verification),'output':str(target)},ensure_ascii=False))
