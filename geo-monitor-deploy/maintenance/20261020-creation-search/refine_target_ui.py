from pathlib import Path
base=Path(__file__).resolve().parents[2]/'creation'
for name in ('panel.html','wizard.js'):
 p=base/name;t=p.read_text(encoding='utf8')
 t=t.replace("const el=$(id);if(!el.value.trim()||!el.checkValidity())", "const el=$(id);if(id==='planCount'&&Number($('planTarget').value)>0)continue;if(!el.value.trim()||!el.checkValidity())")
 t=t.replace("function scheduleSummary(){\n", "function scheduleSummary(){\n $('planCount').disabled=Number($('planTarget').value)>0;\n")
 t=t.replace(".some(id=>!$(id).value)){ $('schedulePreview')", ".some(id=>!(id==='planCount'&&Number($('planTarget').value)>0)&&!$(id).value)){ $('schedulePreview')")
 t=t.replace("max_per_category:Number($('planCount').value),", "max_per_category:Number($('planCount').value)||10,")
 p.write_text(t,encoding='utf8')
