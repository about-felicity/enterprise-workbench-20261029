import json,sqlite3,sys,tarfile
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import runtime
from geo_source_cards.runtime import atomic_json,atomic_write
from multi_run import STATE,root_for,CACHE
from geo_source_cards.rewrite_v2.common import digest
out=BASE/'multi-results';verification=runtime.read(out/'verification.json')
lines=['# 三产品 V2 真实测试进度','',
 '本轮使用工作区三个原始 Word 知识库。每种产品两条问题、百度和文心两个渠道、各一轮，共计划12次采集。三份新范文骨架尚待用户校验；目前没有生成这三篇全文，因此不能称为端到端验收通过。','',
 '| 产品 | 百度完成 | 文心完成 | 来源记录数（未去重） | 已结算模型费用（元） |','|---|---:|---:|---:|---:|']
details=[];total_cost=0;total_captures=0
for item in STATE['products']:
    root=root_for(item);folder=out/item['key'];product=runtime.read(root/'product.json')
    check=next(x for x in verification if x['key']==item['key']);total_captures+=len(check['captures'])
    status=runtime.read(folder/'runtime-status.json');cost=round(sum(x['charged'] or 0 for x in status['costs']),6);total_cost+=cost
    count={m:sum(r['model']==m for r in check['captures']) for m in ('baidu_ai','wenxin_card')}
    sources=sum(r['source_count'] for r in check['captures'])
    lines += [f"| {product['name']} | {count['baidu_ai']}/2 | {count['wenxin_card']}/2 | {sources} | {cost:.6f} |"]
    details += ['','## '+product['name'],'']+['- '+q for q in item['questions']]
    details += ['','计划ID：`'+item['plan_id']+'`；写作任务：`'+root.name+'`。','']
    selected=runtime.read(folder/'selected-source.json')
    details += ['范文：['+selected['source']['article']['title']+']('+selected['source']['url']+')。','']
    material=CACHE/'material'/(check['material_cache_key']+'.json')
    atomic_json(folder/'material.json',runtime.read(material))
    for model in ('baidu_ai','wenxin_card'):
        lane=Path(item['capture_root'])/'days'/item['date']/model
        recovery=runtime.read(lane/'collector/search_recovery.json')
        if recovery.get('error') and count[model]<2:
            details += ['尚未完成：'+model+'；最近错误：'+recovery['error']+'。失败记录保留，不计作成功。','']
            atomic_json(folder/(model+'-recovery.json'),recovery)
    atomic_json(folder/'product-snapshot.json',product)
lines+=['',f'实际完整采集 {total_captures}/12；模型费用合计约 {total_cost:.6f} 元，使用原共享账本，单篇上限仍为0.35元。',
 '', '## 已核验','',
 '- 三份原Word的文件哈希、全部文字内容与产品快照一致（只忽略提取中的空白差异）。',
 '- 三份素材缓存分别绑定对应产品；骨架和素材重复读取均为零额外模型调用。',
 '- 已完成的采集逐条核对问题、渠道、非空正文、正文完整标志、信源完整标志和来源链接。',
 '- 采集调度修复相关67项回归通过。新增覆盖：重试冷却释放共享锁；首题失败后同轮后续题不被饿死。',
 '- 只定点部署采集CLI修复，保留原任务记录、60秒间隔和预算。V2核心仍在隔离目录测试，UI未改。',
 '', '## 待继续','',
 '按用户V2.0文档3.1.7，三份新骨架须人工确认。详见同目录《骨架校验.md》。确认后沿用已解析骨架和素材缓存，执行全文生成→风格审核→事实审核→至多一次全文重写→Word导出及版面验证。',
 '', '精粹水第一条百度查询曾显示上游错误“抱歉，出了点小问题，请稍后重试”；失败截图与尝试记录保留。'+('随后同一问题重试成功，取得完整正文和5个信源，12次计划采集全部完成。' if total_captures==12 else '尚未成功的尝试不计作完成，也不用文心回答替代。'),
 '', '精粹水范文为单品讲解体，归入当前二分体系的科普类；它并非专业科学研究。范文仅提供文章组织参考，采集成功不代表来源功效宣称已经独立核实。']
atomic_write(out/'测试进度.md','\n'.join(lines+details)+'\n')
for name in ('capture-lane-deployment.json','capture-fairness-deployment.json','multi-capture-status.json'):
    atomic_json(out/name,runtime.read(BASE/name))
with tarfile.open(BASE/'multi-results-final.tar.gz','w:gz') as archive:
    archive.add(out,arcname='multi-results')
print(json.dumps({'captures':total_captures,'expected':12,'cost_cny':round(total_cost,6),'status':'awaiting_human_skeleton_review'},ensure_ascii=False))
