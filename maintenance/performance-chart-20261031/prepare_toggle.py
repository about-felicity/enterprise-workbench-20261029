from pathlib import Path
root=Path(__file__).resolve().parents[2];old=Path(__file__).parent;new=root/'maintenance/performance-view-toggle-20261031';new.mkdir(exist_ok=True)
for name in ['package.py','stage.py','deploy.py','verify.py','preserve_sources.py','render_check.mjs']:
 text=(old/name).read_text('utf8').replace('performance-chart-20261031','performance-view-toggle-20261031')
 if name=='package.py':text=text.replace("['PerformanceCenter.tsx','PerformanceTrend.tsx','globals.css']","['PerformanceCenter.tsx','globals.css']")
 if name=='stage.py':text=text.replace("=='monitor-dashboard:performance-weights-20261031'","=='monitor-dashboard:performance-chart-20261031'")
 if name=='deploy.py':text=text.replace('-before-chart-20261031','-before-view-toggle-20261031')
 (new/name).write_text(text,encoding='utf8')
