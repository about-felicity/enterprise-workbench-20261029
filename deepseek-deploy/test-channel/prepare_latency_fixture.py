from pathlib import Path
s=Path('geo-monitor-deploy/maintenance/20261017-scrcpy-public/qa_fixture.py').read_text(encoding='utf8')
s=s.replace('maintenance/20261017-scrcpy-public','maintenance/20261017-input-latency')
old="kind,payload=validate_input(value);inputs.append({'model':model,'kind':kind,'payload':payload});self.send({'ok':True})"
new="kind,payload=validate_input(value);parts=payload if kind=='batch' else [(kind,payload)];inputs.extend({'model':model,'kind':k,'payload':v} for k,v in parts);self.send({'ok':True})"
assert old in s;s=s.replace(old,new)
s=s.replace("v['kind']=='touch'","v['kind']=='click'")
Path('deepseek-deploy/test-channel/qa_latency_fixture.py').write_text(s,encoding='utf8')
