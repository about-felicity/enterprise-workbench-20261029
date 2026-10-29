from pathlib import Path
W=Path(__file__).resolve().parents[2];p=W/'geo-monitor-deploy/creation/panel.html';s=p.read_text('utf8')
start=s.index('<dialog id="deleteDialog"');end=s.index('<script>',start)
s=s[:start]+s[end:]
s=s.replace('#deleteDialog{max-width:480px}#deleteDialog .row{justify-content:flex-end;margin-top:22px}', '#deleteDialog{width:100%;padding:14px;border:1px solid #e0bcb5;border-radius:9px;background:#fff9f6;scroll-margin:24px}#deleteDialog .row{margin-top:12px}#deleteDialog h3{color:#943c2c}#deleteFeedback{margin-top:10px}')
s=s.replace("deleteTarget='';", "deleteTarget='',deleteFeedback=null;")
s=s.replace(" const section=document.querySelector", " if(operation?.name==='plan_delete'){deleteFeedback={text,kind};renderDeleteFeedback()}\n const section=document.querySelector",1)
s=s.replace("||b.id==='deleteCancel'", "")
s=s.replace("(operation.name==='plan_delete'&&b.dataset.deletePlan===operation.body?.plan_id)", "(operation.name==='plan_delete'&&(b.id==='deleteConfirm'||b.dataset.deletePlan===operation.body?.plan_id))")
old="function askDelete(id){if(busy||pendingAction||!connected)return;const p=data.studio.plans.find(p=>p.plan_id===id);if(!p)return;deleteTarget=id;$('deleteTaskName').textContent=p.name||p.product.name;$('deleteDialog').showModal()}"
new="""function renderDeleteFeedback(){const box=$('deleteFeedback');if(box&&deleteFeedback){box.textContent=deleteFeedback.text;box.dataset.state=deleteFeedback.kind;box.hidden=false}}
function askDelete(id){if(busy||pendingAction||!connected)return;if(!data.studio.plans.some(p=>p.plan_id===id))return;deleteTarget=id;deleteFeedback=null;renderDailyTasks();$('deleteCancel').focus({preventScroll:true});$('deleteDialog').scrollIntoView({block:'nearest'})}
function bindDeleteControls(){
 if($('deleteCancel'))$('deleteCancel').onclick=()=>{const id=deleteTarget;deleteTarget='';deleteFeedback=null;renderDailyTasks();document.querySelector('[data-delete-plan="'+id+'"]')?.focus({preventScroll:true})};
 if($('deleteConfirm'))$('deleteConfirm').onclick=()=>act('plan_delete',{plan_id:deleteTarget});
 renderDeleteFeedback();
}"""
assert old in s;s=s.replace(old,new)
s=s.replace("$('deleteCancel').onclick=()=>$('deleteDialog').close();\n$('deleteConfirm').onclick=()=>{const id=deleteTarget;$('deleteDialog').close();act('plan_delete',{plan_id:id})};\n",'')
p.write_text(s,'utf8')
w=W/'geo-monitor-deploy/creation/wizard.js';js=w.read_text('utf8')
js=js.replace("if(name==='plan_delete'){data.studio", "if(name==='plan_delete'){deleteTarget='';deleteFeedback=null;data.studio")
old='<button class="danger" data-delete-plan="${p.plan_id}">删除任务</button></div></div></article>'
new='''<button class="danger" data-delete-plan="${p.plan_id}" aria-expanded="${deleteTarget===p.plan_id}">删除任务</button></div>${deleteTarget===p.plan_id?`<div id="deleteDialog" role="group" aria-labelledby="deleteTitle"><h3 id="deleteTitle">确定删除这个任务？</h3><p class="muted">停止后续采集和创作，并从任务列表移除。已有文章、素材和费用记录保留。</p><div class="row"><button id="deleteCancel">取消</button><button id="deleteConfirm" class="danger primary">确认删除</button></div><p id="deleteFeedback" class="action-feedback" role="status" aria-live="polite" hidden></p></div>`:''}</div></article>'''
assert old in js;js=js.replace(old,new)
js=js.replace('askDelete(b.dataset.deletePlan));buttons();','askDelete(b.dataset.deletePlan));bindDeleteControls();buttons();')
# wizard.js is the canonical trailing script embedded in panel.html.
original=w.read_text('utf8');assert original in s
s=s.replace(original,js);p.write_text(s,'utf8');w.write_text(js,'utf8')
