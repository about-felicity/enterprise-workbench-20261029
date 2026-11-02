from pathlib import Path
root=Path(__file__).resolve().parents[2];old=root/'maintenance/performance-entry-20261031';new=root/'maintenance/performance-mention-fix-20261031'
for name in ['stage_remote.py','deploy_remote.py','verify_remote.py','final_remote.py','preserve_sources.py','probe_public_slow.py']:
 source=(old/name).read_text('utf8').replace('performance-entry-20261031','performance-mention-fix-20261031')
 if name=='stage_remote.py':source=source.replace("=='monitor-dashboard:performance-clean-20261031'","=='monitor-dashboard:performance-entry-20261031'")
 if name=='deploy_remote.py':
  source=source.replace('-before-entry-20261031','-before-mention-fix-20261031').replace("['traffic','budget','scores']","['traffic','budget']").replace("'tests':12","'tests':15")
 (new/name).write_text(source,encoding='utf8')
print('Mention deployment scripts prepared')
