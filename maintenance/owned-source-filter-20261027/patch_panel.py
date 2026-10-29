from pathlib import Path
p=Path('geo-monitor-deploy/creation/panel.html')
old=Path('maintenance/owned-source-filter-20261027/panel.html').read_text(encoding='utf8')
assert p.read_text(encoding='utf8')==old
start=old.index(' const target=',old.index('function taskListItem'))
end=old.index(' const finished=',start)
wizard=Path('geo-monitor-deploy/creation/wizard.js').read_text(encoding='utf8')
a=wizard.index(" const capture='';",wizard.index('function taskListItem'));b=wizard.index(' const finished=',a)
p.write_text(old[:start]+wizard[a:b]+old[end:],encoding='utf8')
