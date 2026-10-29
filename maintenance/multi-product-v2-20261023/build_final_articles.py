"""Export editor-finished articles, keeping automated review results separate."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'geo-source-card-collectors'))
from geo_source_cards.word_export import export_docx

OUT = ROOT / 'outputs/multi-product-v2-20261024'
KEYS = ['conditioner', 'essence', 'cream']
manifest = {'completion_mode': 'assistant_editorial_finish_after_model_review',
            'human_skeleton_review_required_for_this_batch': False,
            'authorization': 'REDACTED_CONFIGURE_LOCALLY',
            'automated_quality_pass': False, 'articles': []}
for key, source in zip(KEYS, sorted(OUT.glob('0[1-3]-*-最终文章.md'))):
    text = source.read_text(encoding='utf-8')
    target = source.with_suffix('.docx')
    typography = ({'chinese_font': '宋体', 'latin_font': 'Cambria', 'body_size': 11,
                   'title_size': 20, 'heading_size': 14, 'line_spacing': 1.4}
                  if key == 'cream' else None)
    export_docx(text, target, typography=typography)
    if key == 'cream':
        from docx import Document
        from docx.shared import Pt
        document = Document(target)
        document.styles['Normal'].paragraph_format.space_after = Pt(4)
        for name in ('Heading 1', 'Heading 2'):
            document.styles[name].paragraph_format.space_before = Pt(6)
            document.styles[name].paragraph_format.space_after = Pt(6)
        document.save(target)
    raw = OUT / 'raw-system-output' / key
    review = json.loads((raw / 'review.json').read_text(encoding='utf-8'))
    status = json.loads((raw / 'runtime-status.json').read_text(encoding='utf-8'))
    costs = status.get('costs', [])
    item = {'key': key, 'markdown': source.name, 'word': target.name,
            'markdown_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'word_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'characters': len(text), 'raw_review_pass': review.get('pass'),
            'raw_draft_sha256': hashlib.sha256((raw / 'draft.md').read_bytes()).hexdigest(),
            'charged_cny': sum(float(c.get('charged') or 0) for c in costs),
            'model_calls': len(costs),
            'final_editorial_checks': ['checked_against_original_knowledge',
                'no_invented_personal_experience', 'test_scope_and_attribution_preserved',
                'unsupported_comparison_scores_removed'],
            'independent_model_review_of_editorial_finish': False}
    manifest['articles'].append(item)
source = next(OUT.glob('00-*-最终文章.md'))
target = source.with_suffix('.docx')
export_docx(source.read_text(encoding='utf-8'), target)
manifest['articles'].insert(0, {
    'key': 'daohe', 'markdown': source.name, 'word': target.name,
    'markdown_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'word_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'characters': len(source.read_text(encoding='utf-8')),
    'raw_review_pass': False,
    'raw_system_output': '../rewrite-v2-real-sample-20261023',
    'model_execution_date': '2026-10-23',
    'new_model_calls_on_20261024': 0,
    'independent_model_review_of_editorial_finish': False,
    'editorial_changes': 'Remove invented commercial relationship, current competitor prices, unsupported effectiveness comparisons; retain product limitations and scope of supplied test summaries.'
})
(OUT / 'delivery-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
