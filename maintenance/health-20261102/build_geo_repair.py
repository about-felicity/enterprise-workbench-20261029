from pathlib import Path
import hashlib,json
w=Path(__file__).parent
p=Path('redroid-deploy/question_only_worker.py')
new=p.read_text()
old=new[:]
start=old.index('\n\ndef interrupted_original_expired(');end=old.index('\n\ndef native_auth_required',start)
old=old[:start]+old[end:]
start=old.index("                    if interrupted_original_expired(config['model']");end=old.index("                    health['status']='running_recovery'",start)
old=old[:start]+old[end:]
production=w/'worker-production.py'
assert old==production.read_text(), 'Unexpected semantic difference'
data={'before':hashlib.sha256(production.read_bytes()).hexdigest(),'text':new}
script=(w/'geo_repair_template.py').read_text()
(w/'run_geo_repair.py').write_text('CHANGE='+repr(data)+'\n'+script,encoding='utf-8')
