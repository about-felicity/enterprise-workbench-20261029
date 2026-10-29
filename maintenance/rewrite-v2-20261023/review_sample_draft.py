"""Assistant's explicit content rejection; preserve the independent model's malformed verdict."""
import shutil
from run_sample import ROOT, DAY
from geo_source_cards.api_worker import Worker
from geo_source_cards.runtime import atomic_json, process_lock
from geo_source_cards.staged_editorial import read
from geo_source_cards.rewrite_v2.common import digest, seal, text_hash

class NoCalls:
    def complete(self, *args, **kwargs): raise AssertionError('This review is local, no model call')

worker = Worker(ROOT, NoCalls())
active = read(ROOT / 'api/active.json')
ticket = ROOT / 'queue' / active['ticket']
job = read(ticket / 'ticket.json')
receipt = read(ticket / 'receipt.json')
run = ROOT / 'api/runs' / active['run_id']
assert job['stage'] == 'review' and job['state'] == 'needs_attention'
assert receipt['error_code'] == 'rewrite_v2_invalid_output'
assert read(run / 'review-calls/style/api_state.json')['state'] == 'RESPONDED'
draft = (run / 'draft.md').read_text()
feedback = '''全文重写：1. 当前“销量口碑和功效依据”段把完整知识库的数据全部概括成“资料里记有”，未完成骨架的实测数据功能。按品牌知识库归属具体呈现4周43.96%、12周33.96%，明确不是作者亲测；发缝27.53%和14200根在知识库中存在2周/12周冲突，只说明冲突不作确定效果。理化指标5.9、40℃泡沫140mm、有效物16.0%可分别支持对应项目，不推成人体功效。价格写资料记载158元/200ml，注明活动与当前价格以页面为准，不能全部删成无信息摘要。2. 合并反复“需要你核验/未附报告”的说明，来源边界集中交代，正文应帮助读者比较，不是资料审计说明书。3. 补全原知识库产品局限：染烫后3天、过敏体质耳后24小时观察及出现异常48小时内联系商家、头皮疾病先遵医嘱治疗后使用、毛囊闭合限制和个体差异；不得将本品限制扩成“任何洗发水”的医学定论。4. 不说卡诗价格明显高于小绿瓶，不把不同容量直接作单价或体验优劣结论。5. 不能照抄原文“直播间里…神药…智商税”开头，按同一功能重写句子。6. 保持已确认的全部段落功能顺序，仍一次性重写全文。'''
result = seal({'workflow': 'rewrite-v2', 'pass': False,
    'style_check': {'pass': False, 'issue': '核心数据段空泛、资料核验式措辞反复，且开头与原文过近。', 'revise_instruction': feedback},
    'compliance_check': None, 'draft_sha256': text_hash(draft),
    'context_sha256': digest(read(run / 'rewrite_context.json')),
    'material_sha256': read(run / 'rewrite_material.json')['sha256'],
    'revise_instruction': feedback, 'reviewer': 'assistant_direct_read',
    'independent_model_verdict_preserved': 'review-calls/style/response.json'})
with process_lock(ROOT / 'coordinator.lock', blocking=True):
    archive = ticket / 'original-malformed-verdict'
    archive.mkdir(exist_ok=False)
    for name in ('ticket.json', 'receipt.json'):
        shutil.copy2(ticket / name, archive / name)
    (ticket / 'receipt.json').rename(archive / 'failed-receipt.json')
    atomic_json(run / 'assistant_content_review.json', result)
    atomic_json(run / 'answer.json', result)
    atomic_json(ticket / 'ticket.json', {**job, 'state': 'claimed'})
    atomic_json(ROOT / 'api/active.json', {**active, 'state': 'RESPONDED'})
print(worker.finish(read(ticket / 'ticket.json'), read(ROOT / 'api/active.json')))
print('Assistant rejected first draft; original model result retained; one full rewrite scheduled.')
