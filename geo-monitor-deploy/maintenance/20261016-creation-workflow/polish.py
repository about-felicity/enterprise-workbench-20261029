from pathlib import Path
p=Path('geo-monitor-deploy/creation/panel.html');s=p.read_text('utf8')
s=s.replace("const selectedKB=kbId,selectedPlan=planId;", "const selectedKB=kbId,selectedPlan=planId,selectedPlanProduct=$('planProduct').value;")
s=s.replace("const pp=$('planProduct').dataset.selected||'';", "const pp=selectedPlanProduct;")
s=s.replace("$('planProduct').addEventListener('change',()=>{$('planProduct').dataset.selected=$('planProduct').value});",'')
s=s.replace("function renderMaterials(){", "function legacyRenderMaterials(){")
p.write_text(s,encoding='utf8')
