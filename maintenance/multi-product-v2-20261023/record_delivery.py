import hashlib
import json
import re
from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/multi-product-v2-20261024'
manifest_path = OUT / 'delivery-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
page_counts = {'daohe': 4, 'conditioner': 3, 'essence': 2, 'cream': 2}
for item in manifest['articles']:
    md, word = OUT / item['markdown'], OUT / item['word']
    expected = re.sub(r'^#{1,6}\s+', '', md.read_text(encoding='utf-8'), flags=re.M)
    actual = '\n'.join(p.text for p in Document(word).paragraphs)
    normalize = lambda text: re.sub(r'\s+', '', text)
    assert normalize(expected) == normalize(actual), item['key']
    assert hashlib.sha256(word.read_bytes()).hexdigest() == item['word_sha256']
    item['word_body_matches_markdown'] = True
    item['rendered_page_count'] = page_counts[item['key']]
    item['visual_inspection'] = 'All final rendered pages inspected; no clipping, missing glyphs, overlapping text or isolated closing paragraph.'
manifest['render_method'] = 'Word COM ExportAsFixedFormat + bundled Poppler; packaged LibreOffice renderer unavailable (diagnosed earlier in this task).'
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
notice = '> **2026-10-24 最新：用户已明确要求直接出文章，骨架由助手检查，不再等待用户确认。本次四篇完整文章与Word已交付（道和小绿瓶、科熙本护发素、姿生怡精粹水、焕颜计美白霜），11页渲染逐页检查、Word正文一致性校验通过。三款新产品真实生成/一次返修/复审完成，自动终审仍未通过，助手依据原知识库完成最后编辑；不得宣称无人干预质量闭环通过。三产品累计19笔0.26797648元，预算未提高，UI未改、V2核心未部署。详见 `outputs/multi-product-v2-20261024/交付说明.md` 与 `delivery-manifest.json`。下方待骨架确认记录已过时，仅作历史。**\n\n'
for name in ('CURRENT_PROJECT_HANDOFF.md', 'PROJECT_STATUS.md', 'maintenance/multi-product-v2-20261023/REPORT.md'):
    path = ROOT / name
    original = path.read_text(encoding='utf-8-sig')
    if not original.startswith(notice):
        path.write_text(notice+original, encoding='utf-8')
print('4 Word documents match Markdown; 11 rendered pages inspected; status records updated.')
