from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
notice = '> **2026-10-23 V2核心重构：四模块候选已接入原UI接口，175项隔离回归通过，未部署。用户指定小绿瓶知识库真实生成两版，复审仍待修订，合格0/1；6次调用估算0.187792元，预算未提高。已完成5页Word排版检查。见[重构与真实测试记录](maintenance/rewrite-v2-20261023/REPORT.md)及[待修订样稿](outputs/rewrite-v2-real-sample-20261023/小绿瓶仿写样稿_待修订.docx)。下方为历史记录。**\n\n'
for name in ('CURRENT_PROJECT_HANDOFF.md', 'PROJECT_STATUS.md'):
    path = ROOT / name
    content = path.read_text('utf8')
    if not content.startswith(notice):
        path.write_text(notice + content, encoding='utf8')
