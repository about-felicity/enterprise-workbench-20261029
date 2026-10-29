"""Human-readable summaries; raw events remain available for diagnosis."""
from datetime import datetime, timedelta, timezone

STAGES = {'writer': '文章写作', 'review': '文章审稿', 'research': '信源分析', 'taxonomy': '信源分类', 'cost': '费用', 'capture': '网页采集', 'scheduler': '每日调度', 'source_fetch': '信源正文抓取', 'analysis': '分类与写作准备', 'environment': '环境检查', 'resumed': '继续任务', 'paused': '暂停', 'capture_warning': '采集提醒', 'capture_error': '采集异常', 'deployment': '版本更新'}


def error_summary(error):
    text = str(error or '')
    for needle, summary in (
        ('章节映射未覆盖', '文章章节与提纲不一致，需要补齐或修正章节对应关系'),
        ('出处映射', '部分陈述没有匹配到有效出处，需要修订证据对应关系'),
        ('evidence coverage', '审稿结果缺少证据核对记录，需要补齐'),
        ('泵数', '稿件用按压次数推算使用时长，但缺少每次用量依据，需要修订'),
        ('claim evidence', '审稿引用与正文或证据不一致，需要核对'),
    ):
        if needle in text:
            return summary
    return text.replace('Draft checks rejected: ', '稿件检查未通过：') or '请到任务与诊断查看具体原因'


def summarize_logs(events, attention=()):
    contexts = {item.get('ticket'): item for item in attention if item.get('ticket')}
    for event in events:
        if event.get('ticket') and event.get('category'):
            contexts[event['ticket']] = event
    capture_contexts = {e['task_id']: e for e in events if e.get('task_id') and e.get('model')}
    output = []
    for event in events:
        if event.get('phase') == 'capture_recovery':
            event = {**capture_contexts.get(event.get('task_id'), {}), **event}
        task = event.get('task') or contexts.get(event.get('ticket'), {})
        category = event.get('category') or task.get('category')
        number = event.get('number') or task.get('number') or task.get('article')
        target = category or '批次任务'
        if number and number != 'shared':
            target += f' · 第{number}篇'
        elif number == 'shared':
            target += ' · 共用资料'
        phase = event.get('phase', '')
        stage = STAGES.get(task.get('stage') if phase == 'cost' else phase, '运行记录')
        failed = bool(event.get('error')) or event.get('state') in {'needs_attention', 'failed'} or phase in {'capture_error', 'paused'}
        if phase == 'capture_recovery':
            status = '待处理' if event.get('exhausted') else '冷却等待'
            failed = bool(event.get('exhausted'))
            message = ('验证页面' if event.get('kind') in {'security', 'verification'} else '页面读取未成功') + f"，本题累计第{event.get('attempt', '?')}次尝试。"
            if event.get('attempt_limit'):
                message += f"当前上限{event['attempt_limit']}次。"
            message += '已达到重试上限，请查看任务与诊断。' if failed else '按有限重试规则等待后继续，不重复已完成题目。'
            if event.get('error'):
                message += '\n原因：' + error_summary(event['error'])
        elif phase == 'environment':
            status = '通过' if event.get('result', {}).get('ok') else '待处理'
            failed = status == '待处理'
            message = 'DeepSeek 登录与 API 可用性检测通过' if not failed else '环境检测未通过，请查看任务与诊断'
        elif phase == 'resumed':
            status, message = '已继续', str(event.get('message', '任务已恢复'))
        elif phase == 'capture' and event.get('message') == '开始本题采集':
            status, message = '进行中', '正在等待当前问题的回答及信源'
        elif phase == 'capture' and event.get('message') == '本题采集完成':
            if event.get('availability') == 'no_card':
                status, message = '未识别到卡片', '本次搜索结果页已加载，但未识别到百度 AI 卡片；可能页面未展示卡片，也可能卡片结构未被识别。本题未取得卡片回答和信源，已保存页面观测供核对。'
            elif event.get('availability') == 'supplement_unavailable':
                status, message = '采集未成功', '百度补充采集未成功，不能据此判断页面没有卡片或信源。'
            elif event.get('sources') == 0:
                status, message = '待核对', '本题记录的信源为 0 条，尚不能确认采集完整，请核对页面与原始记录。'
            else:
                status, message = '已完成', '本题回答和信源已保存'
        elif phase == 'cost':
            message = f"本次{stage}估算费用 ¥{float(event.get('estimated_cny') or 0):.4f}（非实际扣款账单）"
            status = '费用记录'
        elif failed:
            status, message = '待处理', error_summary(event.get('error'))
        elif event.get('state') == 'accepted':
            status, message = '通过', f'{stage}阶段已通过检查'
        elif event.get('state') == 'revision_requested':
            status, message = '待修订', '检查发现问题，已安排修订'
        elif '开始 API' in str(event.get('message', '')):
            status, message = '进行中', f'开始{stage}，预算检查已通过'
        else:
            status, message = '记录', str(event.get('message') or '状态已更新')
        if phase.startswith('capture') and event.get('model'):
            target = {'deepseek': 'DeepSeek', 'wenxin_card': '文心卡片', 'baidu_ai': '百度卡片（补充）'}.get(event['model'], event['model'])
            if event.get('ordinal'):
                target += f" · 第{event['ordinal']}/{event.get('total', '?')}题"
            if event.get('question'):
                message += "\n问题：" + str(event['question'])
            if 'sources' in event:
                message += f"\n取得信源 {event['sources']} 条"
            if phase == 'capture_error':
                message = str(event.get('message', '采集暂停')) + "\n问题：" + str(event.get('question', '')) + "\n原因：" + str(event.get('error_type', '详见原始日志')) + "；请到任务与诊断处理，未知发送状态不会自动重发"
        if phase == 'capture_warning':
            status = '提醒'
        if phase == 'source_fetch' and event.get('observations') is not None:
            message += f"\n已汇总 {event['observations']} 条平台回答；抓取完成后自动分类"
        batch_date = event.get('date') or task.get('batch_date')
        if batch_date:
            target = str(batch_date) + ' · ' + target
        epoch = event.get('epoch')
        time = datetime.fromtimestamp(epoch, timezone(timedelta(hours=8))).strftime('%m-%d %H:%M:%S') if isinstance(epoch, (int, float)) else '时间未知'
        output.append({'text': f'{time}  【{status}】{target}\n{message}', 'failed': failed})
    return output
