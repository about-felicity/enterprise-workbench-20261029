"""Compare reviewed reference JS on the SAME live Baidu page, after queue completion."""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, '/opt/monitor/geo-capture')
from wenxin_monitor.controller import WenxinWebCollector, BAIDU_AI_SNAPSHOT_JS
from geo_source_cards.runtime import process_lock

base = Path('/opt/monitor/geo-capture')
batch = base / 'batches/geo-panel-baidu-ai-20261016-095851-ff407fd3'
health = json.loads((batch / 'bridge_health.json').read_text())
assert health['tasks'] == {'completed': 15}, 'Finish the requested collection before diagnostic navigation'
assert health['status'] in {'complete', 'complete_with_unavailable'}
reference = json.loads(Path('/tmp/baidu-reference-scripts-20261016.json').read_text())
root = base / 'batches/geo-panel-baidu-ai-20261015-181822-d44632b8/collector'
out = base / 'maintenance/20261016-daily-start/reference-live-comparison'
out.mkdir(exist_ok=True)
os.environ['WENXIN_STEALTH_HEADLESS'] = '1'
reports = []
with process_lock(root / 'collector.lock'):
    collector = WenxinWebCollector(profile=root / 'profiles/baidu/scrapling_profile')
    try:
        for index, question in enumerate(('推荐一款卸妆油', '推荐一款防晒霜')):
            collector.page.call('Page.navigate', {'url': 'https://www.baidu.com/'}, timeout=30)
            collector._navigate_fresh(collector.search_url(question))
            for _ in range(35):
                before = collector.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
                if collector._is_security_verification(before):
                    raise RuntimeError('Security verification; diagnostic stopped without retrying')
                if before.get('cardPresent') and before.get('readyState') == 'complete':
                    break
                time.sleep(1)
            clicked = collector._expand_ai_card()
            collector._scroll_ai_card()
            time.sleep(2)
            after_current = collector.page.evaluate(BAIDU_AI_SNAPSHOT_JS)
            point = collector.page.evaluate(reference['expand_js'])
            reference_clicked = isinstance(point, dict)
            if reference_clicked:
                collector.page.click(int(point['x']), int(point['y']))
                time.sleep(1)
            collector._scroll_ai_card()
            after_reference = collector.page.evaluate(reference['BAIDU_AI_SNAPSHOT_JS'])
            drawer = collector.page.evaluate(reference['BAIDU_OPEN_SOURCE_DRAWER_JS'])
            time.sleep(1)
            direct = collector.page.evaluate(reference['BAIDU_CARD_DIRECT_SOURCES_JS'])
            provenance = collector.public_card_references()
            details = collector.page.evaluate(r'''(()=>{const c=document.querySelector('#content_left [tpl="new_baikan_index"],#content_left [tpl="wenda_generate"],#content_left .cosc-card');return {html:c?.outerHTML||'',text:c?.innerText||'',controls:[...(c?.querySelectorAll('div,span,a,button')||[])].filter(e=>/^(收起|展开)/.test((e.innerText||'').trim())&&(e.innerText||'').length<40).map(e=>({text:e.innerText,visible:e.getBoundingClientRect().height>0,class:e.className})),links:[...(c?.querySelectorAll('a[href]')||[])].map(a=>({text:a.innerText,url:a.href,parent:a.parentElement?.className,goods:!!a.closest('[class*="goods"],[class*="shopping"]')}))}})()''')
            item = {'question': question, 'before': before, 'our_expand_clicked': clicked,
                    'after_our_expand': after_current, 'reference_expand_clicked': reference_clicked,
                    'after_reference_expand': after_reference, 'reference_drawer': drawer,
                    'reference_direct_links': direct, 'our_provenance': provenance, 'details': details}
            (out / f'{index}.json').write_text(json.dumps(item, ensure_ascii=False, indent=2))
            if getattr(collector.page, 'page', None):
                collector.page.page.screenshot(path=str(out / f'{index}.png'), full_page=True)
            reports.append({'question': question, 'initial_folded': before.get('folded'),
                            'our_expand_clicked': clicked, 'reference_extra_expand': reference_clicked,
                            'our_body_length': len(after_current.get('body', '')),
                            'reference_body_length': len(after_reference.get('body', '')),
                            'same_body': after_current.get('body') == after_reference.get('body'),
                            'final_folded': after_reference.get('folded'),
                            'citation_count': after_reference.get('citationCount'), 'drawer': drawer,
                            'direct_links': len(direct.get('sources', [])), 'provenance': provenance,
                            'collapse_controls': [c for c in details['controls'] if c['visible']]})
    finally:
        collector.close()
(out / 'summary.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2))
print(json.dumps(reports, ensure_ascii=False))
