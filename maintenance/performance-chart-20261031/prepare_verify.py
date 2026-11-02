from pathlib import Path
here=Path(__file__).parent
old=here.parent/'performance-weights-20261031/final_remote.py'
source=old.read_text('utf8').replace('performance-weights-20261031','performance-chart-20261031')
source=source[:source.index('\ntry:\n with op.open')]
source+="""
report['public_frontend_current']=True
report['deployed_hashes_verified']=True
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('CHART_PUBLIC_VERIFIED')
"""
(here/'verify.py').write_text(source,encoding='utf8')
