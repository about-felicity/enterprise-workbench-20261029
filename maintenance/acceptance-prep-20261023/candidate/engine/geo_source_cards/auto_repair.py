"""Bounded editorial recovery of delivered failures; never retry unknown sends."""
import shutil
from pathlib import Path

from .runtime import atomic_json, atomic_write, process_lock
from .pipeline_control import event, state
from .staged_editorial import read

MAX_ROUNDS = 3
MAX_ASSISTED_ROUNDS = 2


def correction(error, stage):
    rules = [
        ('Article plan checks','logic','按照实际产品清单修正标题与计数，保留正确的产品正文及证据，重新接受全文审稿。'),
        ('Logical review requests revision','logic','逐条修复独立逻辑审稿指出的前提缺口、前后矛盾和章节承接。保留正确产品身份、证据和已通过段落，删去未被证明的结论、重复凑字；修订后的完整稿必须重新接受事实及全文逻辑审稿，不复制旧通过结论。'),
        ('Source claims must not be promoted to verified facts','evidence_status','媒体原文记载的产品组成、规格仍是source_claim，verification必须not_independently_verified。不得把转述、营销或报告编号改为verified。缺少证据的效果删除或保留risk，不用opinion包装事实。'),
        ('自有产品实质介绍不足','product_detail','按product_detail_contract充分展开已批准的不同PF资料，补齐产品介绍目标字数，不重复核对标签、免责声明或虚构功效。保留正确知识与竞品段落。'),
        ('自有产品事实覆盖不足','product_detail','从已提供PF选择不同事实，组成、用法、有条件试验分别解释；每个实际使用的事实建立逐字PF映射，不将同一事实改写多遍凑数量。'),
        ('有条件检测摘要不足','product_detail','补充合同要求数量的已提供supplier_report_summary，保留方法、必要条件与准确指标，不把体外结果外推成人体功效。'),
        ('引用品牌检测摘要缺少','product_detail','在检测数据附近用一句话明确这是品牌提供的报告摘要记录，保持数据条件与正文消费文章语气，不反复写核验日志。'),
        ('首段缺少独立背景', 'consumer_voice', '首段须独立交代读者问题，不能用还有一层/其次等承接语起头；把补充内容接在原导语之后，并检查衔接和重复。'),
        ('正文混入来源解读', 'consumer_voice', '重写来源解读段为直接面向读者的文章。原文/主参考/知识库/编排等只属于内部溯源，不改成相关资料作替身；有证据的产品组成直接简洁介绍，未经证实的功效省略，不能删除归属后升级为事实。'),
        ('正文反复使用资料核验', 'consumer_voice', '删除重复的审计套话，不拿免责声明凑字数。保留一处必要披露，以具体内容和有依据的比较取舍重写，不引入新功效。'),
        ('产品决策禁止植入', 'product_gate', '本稿NO_INSERT：删除所有自有品牌、产品举例和商业披露，保留可用知识章节，不能换称呼继续植入。'),
        ('invalid_response', 'format', '返回单个完整JSON对象，严格使用任务要求的键和类型，字符串引号和换行必须正确转义，不加代码围栏、解释或省略号。'),
        ('invalid_stage_schema', 'schema', '逐项检查JSON结构及失败详情；产品逐款提供对应Ri证据的可用KU，不能漏项或用其他产品证据代替。'),
        ('Medical mechanisms', 'medical_classification', '未核验的医学机制、炎症、抑菌、用药疗程只能归risk/conflict，不进入提纲。添加原文称不能使其可用；从同一原文抽取成分名称、组成、资料分类、比较方法等有证据的信息。'),
        ('正文汉字不足', 'length', '输出完整正文，不能摘要替代。排行目标3200汉字，科普目标2800汉字；导语至少220汉字。按实际产品数量或知识章节分配篇幅，标题英文标点不算字数，禁止重复凑字或编造事实。'),
        ('正文过短', 'length', '输出完整稿件而非摘要，排行至少2800汉字、科普至少2400汉字，导语至少220汉字；不靠编造或重复填充。'),
        ('科普导语', 'introduction', '导语至少220汉字，具体解释文章问题与阅读目的，不能先介绍品牌。'),
        ('产品名单前', 'introduction', '在产品名单前写足600—850汉字的问题导入与选购依据，随后再进入产品逐款介绍；不能靠标题、英文和重复句充数。'),
        ('导入不得', 'introduction', '移除导入中的品牌推销，先解释读者问题与选购依据；自有产品放在产品名单第一位。'),
        ('出处映射', 'mapping', '先完成正文，再从正文逐字摘录事实短句生成claim_map，包含实际标点。只用本稿KU/PF；不能复制知识原句冒充正文，删除无出处的功效推断。纯编排和商业披露不当产品事实。'),
        ('正文超过', 'length', '压缩重复和冗长段落，符合本稿上下限，同时保留全部提纲与产品名单，不能改成摘要。'),
        ('连续复制', 'originality', '重新组织与表达被指出的段落，保留证据含义，禁止逐字粘贴来源或简单换词；所有声明映射重做为新正文原句。'),
        ('Missing product-specific evidence', 'product_evidence', '每个竞品至少一条含完整产品名、对应Ri证据的source_claim，仅写有出处的组成或规格；不能只给会被降级的机制疗效句。'),
        ('Semantic review requests revision', 'review', '逐条处理独立审稿列出的阻断原因，修订实际正文并重建全部映射；排行的选购标准须位于逐款介绍之前，保留正确资料、篇幅和产品名单。'),
    ]
    matched = [(kind, note) for token, kind, note in rules if token in error]
    if not matched or stage not in {'research', 'writer', 'review'}:
        return None
    return ','.join(dict.fromkeys(k for k, _ in matched)), '\n'.join(dict.fromkeys(n for _, n in matched))


def schedule(root, date, target_article=None):
    from .daily_editorial import publish_ticket, repair_research
    root = Path(root)
    if state(root).get('paused'):
        return 0
    scheduled = 0
    with process_lock(root/'coordinator.lock'):
        jobs = [read(p) for p in (root/'queue').glob('*/ticket.json')]
        for job in jobs:
            meta = job['meta']
            key = tuple(meta.get(k) for k in ('date','category','number'))
            if meta.get('date') != date or job['state'] != 'needs_attention':
                continue
            if target_article is not None and key != target_article:
                continue
            path = root/'queue'/job['id']
            if (path/'auto_repair_blocked.json').exists():
                continue
            receipt = path/'receipt.json'
            # Only completed/failed deliveries are eligible, not network ambiguity.
            if not receipt.is_file() or read(receipt).get('state') not in {'completed','failed'}:
                continue
            if read(receipt).get('error_code')=='topic_not_feasible':continue
            article_location=root/job['location'];writer_location=article_location.parent/'writer' if job['stage']=='review' else article_location
            compiled_path=root/'api/runs'/job.get('execution',{}).get('run_id','missing')/'compilation.json'
            compiled=(read(writer_location/'writer_done.json').get('compilation') if (writer_location/'writer_done.json').is_file() else None) or (read(compiled_path) if compiled_path.is_file() else None)
            if compiled:
                attempts=meta.get('compiled_repair_round',0)
                if attempts>=2:
                    atomic_json(path/'auto_repair_blocked.json',{'status':'REPAIR_EXHAUSTED','max_repairs':2})
                    continue
            plan = correction(str(job.get('error') or ''), job['stage'])
            if plan is None:
                continue
            replacements = [j for j in jobs if j['meta'].get('replaces') == job['id']]
            if replacements:
                atomic_json(path/'ticket.json', {**job,'state':'revision_requested','replaced_by':replacements[0]['id']})
                continue
            if any(j['state'] in {'pending','claimed'} and tuple(j['meta'].get(k) for k in ('date','category','number')) == key for j in jobs):
                continue
            round_number = meta.get('auto_repair_round', 0) + 1
            assisted = round_number > MAX_ROUNDS and job['stage'] in {'writer','review'}
            assisted_round = meta.get('assisted_repair_round', 0) + 1 if assisted else 0
            from .append_repair import eligible_error
            early_append=(not compiled and job['stage']=='writer' and read(receipt).get('state')=='completed' and eligible_error(str(job.get('error',''))) and (root/job['location']/'draft.md').is_file() and not meta.get('append_repair_round'))
            append_only = early_append or (not compiled and assisted and assisted_round > MAX_ASSISTED_ROUNDS and job['stage']=='writer'
                           and 'length' in plan[0] and not meta.get('append_repair_round'))
            if round_number > MAX_ROUNDS and (not assisted or assisted_round > MAX_ASSISTED_ROUNDS) and not append_only:
                if not (path/'auto_repair_exhausted.json').exists():
                    atomic_json(path/'auto_repair_exhausted.json', {'limit':MAX_ROUNDS})
                    event(root, 'repair', '自动修复已达上限，保留证据；其他稿件继续', category=meta['category'],number=meta['number'],date=date)
                continue
            strategy, note = plan
            reason = f'自动定向修复第{round_number}/{MAX_ROUNDS}轮，策略：{strategy}。\n{note}\n实际错误：{job.get("error", "")}\n保留当天资料、来源合同、全部质量门槛与预算上限。'
            if assisted:
                reason = f'DeepSeek辅助诊断修订第{assisted_round}/{MAX_ASSISTED_ROUNDS}轮。先分析失败稿和实际错误，再局部修订；保留正确段落，不从头重写。\n{note}\n实际错误：{job.get("error", "")}\n保留原来源、质量检查和预算。'
            if append_only:
                reason = '[APPEND_REPAIR_V1]\n只增补一次，不重写原稿，程序保留原文并拼接。\n'+note+'\n实际错误：'+job.get('error','')
            if round_number > 1:
                reason += '\n前轮仍未通过；重新逐项核对错误，不复用上轮错误文本，完成后自行检查全部输出字段。'
            if job['stage'] == 'research':
                try:
                    result = repair_research(root, job, reason)
                except (ValueError, KeyError, TypeError) as error:
                    atomic_json(path/'auto_repair_blocked.json', {'reason':str(error)[:500]})
                    event(root,'repair','自动修复输入检查未通过，保留证据；其他稿件继续',category=meta['category'],number=meta['number'],date=date)
                    continue
                identity = result['ticket']
                new_path = root/'queue'/identity/'ticket.json'
                new = read(new_path)
                atomic_json(new_path,{**new,'meta':{**new['meta'],'auto_repair_round':round_number,'revision':1,'auto_repair_strategy':strategy}})
            elif job['stage']=='review' and read(receipt).get('state')=='failed' and read(receipt).get('error_code') in {'invalid_response','invalid_stage_schema','logic_invalid_response','logic_output_incomplete'}:
                # Judge-output failures must not trigger an article rewrite.
                import hashlib
                location=root/job['location'];source=root/'api/runs'/job['execution']['run_id']
                inputs=list(job['inputs']);known=False
                if (source/'logic-call/api_state.json').is_file():
                    proof=read(location/'known_response.json') if meta.get('known_response_replay') and (location/'known_response.json').is_file() else {
                        'source_run':source.name,'source_ticket':job['id'],
                        'response_sha256':hashlib.sha256((source/'call/response.json').read_bytes()).hexdigest()}
                    atomic_json(location/'known_response.json',proof)
                    inputs=list(dict.fromkeys(inputs+['known_response.json']));known=True
                identity=publish_ticket(root,'review',location,inputs,['result.json'],{
                    **meta,'revision':1,'replaces':job['id'],'auto_repair_round':min(round_number,MAX_ROUNDS),
                    **({'assisted_repair_round':min(assisted_round,MAX_ASSISTED_ROUNDS)} if assisted else {}),
                    'known_response_replay':known,'auto_repair_strategy':'review_output_recovery'})
                atomic_json(path/'ticket.json',{**job,'state':'revision_requested','replaced_by':identity})
            else:
                location = root/job['location']
                writer = location.parent/'writer' if job['stage']=='review' else location
                archive = root/'repair_evidence'/('auto-'+job['id'])
                if archive.exists():
                    continue  # Incomplete publication is preserved for diagnosis.
                shutil.copytree(path,archive/'ticket')
                shutil.copytree(writer,archive/'writer')
                inputs = ['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
                inputs += [n for n in ('draft.md','claim_map.json','knowledge_to_sections.json') if (writer/n).is_file()]
                from .paragraph_repair import prepare,MARKER as PARAGRAPH_MARKER
                try:repair_files=[] if append_only else prepare(writer,job.get('error',''),attempts=meta.get('compiled_repair_round',0))
                except (ValueError,KeyError,TypeError) as error:
                    atomic_json(path/'auto_repair_blocked.json',{'reason':str(error)[:500]})
                    event(root,'repair','本篇返修证据未通过校验，其他稿件继续',category=meta['category'],number=meta['number'],date=date)
                    continue
                if repair_files:
                    reason=PARAGRAPH_MARKER+'\n'+reason
                    inputs+=repair_files
                atomic_write(writer/'revision_note.txt',reason)
                identity = publish_ticket(root,'writer',writer,[*inputs,'revision_note.txt'],['draft.md','article.docx','claim_map.json','knowledge_to_sections.json','writer_done.json'],{**meta,'revision':1,'replaces':job['id'],'auto_repair_round':min(round_number,MAX_ROUNDS),'auto_repair_strategy':strategy,**({'assisted_repair_round':min(assisted_round,MAX_ASSISTED_ROUNDS)} if assisted else {}),**({'append_repair_round':1} if append_only else {}),'paragraph_repair':bool(repair_files),'known_response_replay':False,'compiled_repair_round':meta.get('compiled_repair_round',0)+1})
                atomic_json(path/'ticket.json',{**job,'state':'revision_requested','replaced_by':identity,'operator_reason':reason})
            message = f'已安排DeepSeek辅助诊断修订，第{assisted_round}/{MAX_ASSISTED_ROUNDS}轮：{strategy}' if assisted else f'已自动安排定向修复，第{round_number}/{MAX_ROUNDS}轮：{strategy}'
            if append_only:
                message = '已安排一次DeepSeek增补修订：保留原稿，仅插入补充段落'
            event(root,'repair',message,category=meta['category'],number=meta['number'],date=date,ticket=identity)
            jobs.append(read(root/'queue'/identity/'ticket.json'))
            scheduled += 1
    return scheduled
