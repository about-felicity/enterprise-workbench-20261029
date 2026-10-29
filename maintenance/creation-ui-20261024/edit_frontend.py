from pathlib import Path
R=Path(__file__).resolve().parents[2]/'geo-monitor-deploy/creation'
p=R/'panel.html';s=p.read_text('utf8');w=(R/'wizard.js').read_text('utf8')
def replace(old,new):
 global s
 assert old in s,old[:90];s=s.replace(old,new)
replace("const finished=['complete','capture_only_complete'].includes(state),resume=['paused','needs_attention','waiting_login'].includes(state);", "const finished=isTerminal(state),resume=dayActions(t).includes('day_resume');")
replace("const canControl=!!t&&!finished&&state!=='not_enabled';", "const canControl=dayActions(t).length>0;")
replace("${finished?'已完成':p.enabled?'等待执行':'未启用'}", "${finished?(state==='complete'||state==='capture_only_complete'?'已完成':'已结束'):p.enabled?'等待执行':'未启用'}")
replace('${control}<button data-edit-plan="${p.plan_id}">查看与编辑</button>', '${control}<button data-edit-plan="${p.plan_id}">查看与编辑</button><button class="danger" data-delete-plan="${p.plan_id}">删除任务</button>')
replace("!['complete','not_enabled','capture_only','capture_only_complete','scheduled'].includes(t.status)", "dayActions(t).length>0")
replace("document.querySelectorAll('[data-edit-plan]').forEach(b=>b.onclick=()=>{editCreationPlan(b.dataset.editPlan)});", "document.querySelectorAll('[data-edit-plan]').forEach(b=>b.onclick=()=>{editCreationPlan(b.dataset.editPlan)});\n document.querySelectorAll('[data-delete-plan]').forEach(b=>b.onclick=()=>askDelete(b.dataset.deletePlan));buttons();")
replace("complete=j.day?.status==='complete',paused=j.control.paused", "complete=j.day?.status==='complete',terminal=isTerminal(j.day?.status)||j.control?.reason==='plan_deleted',paused=j.control.paused")
replace('${!complete?`<button data-action=', '${!terminal?`<button data-action=')
replace("if(name==='plan_save'){newCreationTask();showView('tasks')}", "if(name==='plan_save'){newCreationTask();showView('tasks')}\n if(name==='plan_delete'){data.studio.plans=data.studio.plans.filter(p=>p.plan_id!==r.plan_id);data.studio.daily_tasks=data.studio.daily_tasks.filter(t=>t.plan_id!==r.plan_id);if(planId===r.plan_id)newCreationTask();showView('tasks');renderDailyTasks()}")
# Use one status component near each submit, plus a visible global notice for list actions.
replace('</style></head>', '''
.action-feedback{padding:12px 14px;margin:14px 0 0;border:1px solid #c9ddd3;border-radius:8px;background:#f0f8f4;line-height:1.7;overflow-wrap:anywhere}
.action-feedback[data-state="working"]:before,button[aria-busy="true"]:before{content:'';display:inline-block;width:12px;height:12px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;margin-right:8px;vertical-align:-2px;animation:spin .9s linear infinite}
.action-feedback[data-state="error"]{background:#fff2ed;border-color:#e6b8aa;color:#943c2c}
.action-feedback[data-state="success"]{background:#edf8f1;color:#14664f}
@keyframes spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.action-feedback:before,button[aria-busy="true"]:before{animation:none!important}}
.queue-item button.danger,button.danger{color:#a14638;border-color:#e0bcb5;background:white}
button.danger.primary{color:white;background:#a14638}button:disabled{opacity:.55;cursor:not-allowed}
#message{position:sticky;top:10px;z-index:20;box-shadow:0 4px 16px #19372f12;white-space:pre-line}
#deleteDialog{max-width:480px}#deleteDialog .row{justify-content:flex-end;margin-top:22px}
.queue-controls{max-width:330px}.queue-controls .row{justify-content:flex-end}
@media(max-width:700px){.queue-controls{max-width:none}.queue-controls .row{justify-content:flex-start}}
</style></head>''')
replace('<div id="message" role="status"></div>', '<div id="message" role="status" aria-live="polite" aria-atomic="true"></div>')
replace('<script>', '''<dialog id="deleteDialog" aria-labelledby="deleteTitle" aria-describedby="deleteDescription"><h2 id="deleteTitle">删除这个任务？</h2><p id="deleteTaskName"></p><p id="deleteDescription" class="muted">删除后从任务列表移除，并停止后续采集和创作。正在处理的请求会安全收尾，已有文章、素材和费用记录保留。</p><div class="row"><button id="deleteCancel" autofocus>取消</button><button id="deleteConfirm" class="danger primary">确认删除</button></div></dialog><script>''')
start=s.index('function message(');end=s.index('async function request(',start)
s=s[:start]+'''let operation=null,operationTimer=null,lockedFields=new Map(),deleteTarget='';
const terminalStates=new Set(['complete','capture_only_complete','complete_with_failures','insufficient_materials','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles']);
function isTerminal(state){return terminalStates.has(state)}
function dayActions(t){return t?.allowed_actions||(!t||isTerminal(t.status)?[]:['paused','needs_attention','waiting_login'].includes(t.status)?['day_resume']:['collecting','creating','waiting_for_geo','waiting_writing'].includes(t.status)?['day_pause']:[])}
function message(text,error=false,state='success'){
 const kind=error?'error':state;
 const box=$('message');box.textContent=text;box.style.display='block';box.className='action-feedback';box.dataset.state=kind;box.setAttribute('role',error?'alert':'status');
 const section=document.querySelector('[data-step="'+wizardStep+'"]');
 if(activeView==='editor'&&section){let feedback=section.querySelector('.action-feedback');if(!feedback){feedback=document.createElement('p');feedback.className='action-feedback';feedback.setAttribute('role','status');section.querySelector('.wizard-actions').before(feedback)}feedback.textContent=text;feedback.dataset.state=kind;feedback.hidden=false}
 if(operation?.name==='kb_import'){$('kbSource').textContent=text}
}
function operationButton(b){
 if(!operation)return false;
 const ids={kb_import:'kbImport',kb_save:'kbSave',plan_save:operation.body?.enabled?'planEnable':'planSave',balance:'balance',new:'new'};
 return b.id===ids[operation.name]||(b.dataset.plan===operation.body?.plan_id&&b.dataset.date===operation.body?.date&&b.dataset.dayAction===operation.name)||(b.dataset.job===operation.body?.job_id&&b.dataset.action===operation.name)||(operation.name==='plan_delete'&&b.dataset.deletePlan===operation.body?.plan_id);
}
function buttons(){
 const blocked=busy||!connected||!!pendingAction;
 document.querySelectorAll('button').forEach(b=>{
  const readonly=b.hasAttribute('data-view')||b.classList.contains('article-view')||b.classList.contains('preview')||b.id==='deleteCancel';
  b.disabled=b.hasAttribute('data-control-unavailable')||(!readonly&&blocked)||(b.id==='kbImport'&&!$('kbWord').files.length);
  if(busy&&operationButton(b)){if(!b.dataset.idleLabel)b.dataset.idleLabel=b.textContent;b.textContent=operation.label;b.setAttribute('aria-busy','true')}
  else if(b.dataset.idleLabel){b.textContent=b.dataset.idleLabel;delete b.dataset.idleLabel;b.removeAttribute('aria-busy')}
 });
 if(busy){document.querySelectorAll('[data-workspace="editor"] input,[data-workspace="editor"] textarea,[data-workspace="editor"] select').forEach(e=>{if(!lockedFields.has(e))lockedFields.set(e,e.disabled);e.disabled=true})}
 else if(lockedFields.size){for(const[e,disabled]of lockedFields)e.disabled=disabled;lockedFields.clear();scheduleSummary()}
 $('retryAction').hidden=!pendingAction||busy;$('retryAction').disabled=busy||!connected;
}
function askDelete(id){if(busy||pendingAction||!connected)return;const p=data.studio.plans.find(p=>p.plan_id===id);if(!p)return;deleteTarget=id;$('deleteTaskName').textContent=p.name||p.product.name;$('deleteDialog').showModal()}
''' +s[end:]
start=s.index('async function act(');end=s.index("$('new').onclick",start)
s=s[:start]+'''async function act(name,body){
 if(busy)return;if(!connected){message('暂时未连接，请等待连接恢复后再操作。',true);return}
 const labels={kb_import:['正在分析文档…','正在上传并提取产品资料，请稍候…'],kb_save:['正在保存…','正在保存产品知识库，完成后进入问题配置…'],plan_save:['正在保存任务…','正在保存任务配置并确认执行安排…'],plan_delete:['正在删除…','正在停止后续执行并移除任务…'],day_pause:['正在暂停…','正在提交暂停请求，已发送的请求会安全收尾…'],day_resume:['正在检查…','正在检查任务状态并恢复执行…'],pause:['正在暂停…','正在提交暂停请求…'],resume:['正在检查…','正在检查并恢复创作…'],balance:['正在查询…','正在查询API余额…'],new:['正在建立…','正在准备素材并建立创作任务…']};
 const [label,note]=labels[name]||['正在处理…','正在提交操作…'];
 busy=true;operation={name,body:typeof body==='function'?null:body,label,note,start:Date.now()};buttons();message(note,false,'working');
 operationTimer=setInterval(()=>{if(operation)message(operation.note+' 已等待 '+Math.floor((Date.now()-operation.start)/1000)+' 秒，请勿重复提交。',false,'working')},1000);
 try{
  if(typeof body==='function'){operation.note='正在读取本地Word文件…';message(operation.note,false,'working');body=await body();operation.body=body;operation.note=note;message(note,false,'working')}
  const result=await request('control/'+name,body);clearInterval(operationTimer);
  if(name==='materials_settings')materialDirty=false;
  if(['kb_import','kb_save','plan_save','plan_delete','day_pause','day_resume'].includes(name))studioResult(name,result.result);
  if(name==='balance')$('balanceText').textContent=result.result?.is_available?'API余额可用':'API余额不可用';
  const success=name==='kb_import'?'文档已解析，产品信息已填入下方。确认后点击“确认产品信息，下一步”。':name==='new'?'创作任务已建立，可在“执行进度”查看。':result.result?.message||'操作已完成';
  if(refreshing)await refreshing;const refreshed=await refresh();
  if(name==='kb_save'){$('planProduct').value=kbId;showStep(2)}
  message(success+(refreshed?'':' 最新列表暂未获取，连接恢复后会自动更新。'));
 }catch(e){message(e.message||'操作失败，输入内容已保留，请重试。',true)}
 finally{clearInterval(operationTimer);busy=false;operation=null;buttons()}
}
''' +s[end:]
# Serialize refreshes and never replace action feedback with a background polling error.
start=s.index('async function refresh(');end=s.index('function fillCatalog(',start)
s=s[:start]+'''async function refresh(){
 if(refreshing)return refreshing;
 refreshing=(async()=>{try{data=await request('panel');csrf=data.csrf;connected=true;$('connection').textContent='已连接 · '+dt(data.at);$('limits').textContent='费用上限：单篇含共享分析 ¥'+data.settings.article_budget_cny+'，每日共享 ¥'+data.settings.daily_budget_cny+'。成稿不会自动发布。';renderFilterOptions();renderLibrary();renderJobs();renderStudio();buttons();return true}catch(e){connected=false;$('connection').textContent='连接中断，正在重连；后台任务继续执行';buttons();if(!busy)message('暂时无法获取最新状态，已保留输入与进度，正在自动重连。',true);return false}})();
 try{return await refreshing}finally{refreshing=false}
}
''' +s[end:]
start=s.index("$('kbImport').onclick=");end=s.index("$('kbSave').onclick",start)
s=s[:start]+'''$('kbWord').onchange=()=>{const f=$('kbWord').files[0];$('kbSource').textContent=f?'已选择 '+f.name+'，点击“导入并分析产品信息”开始。':'请选择Word文件';buttons()};
$('kbImport').onclick=()=>{const file=$('kbWord').files[0];if(!file){message('请先选择Word文件',true);return}if(!file.name.toLowerCase().endsWith('.docx')||file.size>5*1024*1024){message('请选择5MB以内的.docx文件',true);return}act('kb_import',()=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({filename:file.name,content_base64:String(reader.result).split(',')[1]});reader.onerror=()=>reject(Error('文件读取失败，请重新选择Word文件。'));reader.onabort=()=>reject(Error('文件读取已取消，请重新选择文件。'));reader.readAsDataURL(file)}))};
$('deleteCancel').onclick=()=>$('deleteDialog').close();
$('deleteConfirm').onclick=()=>{const id=deleteTarget;$('deleteDialog').close();act('plan_delete',{plan_id:id})};
''' +s[end:]
replace("setTimeout(()=>controller.abort(),45000)", "setTimeout(()=>controller.abort(),path==='control/kb_import'?120000:45000)")
# Clear old success/error notices when starting a new editor session.
replace("loadKnowledge('');loadPlan('');$('kbWord').value='';showStep(1);", "loadKnowledge('');loadPlan('');$('kbWord').value='';document.querySelectorAll('[data-step] .action-feedback').forEach(e=>e.hidden=true);showStep(1);buttons();")
replace("if(n>1&&!knowledgeReady())", "if(busy&&operation?.name!=='kb_save'&&operation?.name!=='plan_save'&&operation?.name!=='plan_delete')return;\n if(n>1&&!knowledgeReady())")
# Keep editable wizard source in sync with its embedded deployment copy.
start=s.index("let activeView='tasks';");end=s.index('</script>',start)
(R/'wizard.js').write_bytes(s[start:end].replace('\n','\r\n').encode('utf8'))
p.write_bytes(s.replace('\n','\r\n').encode('utf8'))
