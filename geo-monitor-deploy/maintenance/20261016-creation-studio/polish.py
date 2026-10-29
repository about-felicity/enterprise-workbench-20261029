from pathlib import Path
p=Path('geo-monitor-deploy/creation/panel.html')
s=p.read_text('utf8').replace('*{box-sizing:border-box}','*{box-sizing:border-box}[hidden]{display:none!important}')
s=s.replace('${paused?`<p class=', '${paused&&!complete?`<p class=')
s=s.replace("paused:'已手动暂停',waiting_for_geo:", "paused:'已手动暂停',pausing:'正在收尾后暂停',waiting_for_geo:")
p.write_text(s,encoding='utf8')
