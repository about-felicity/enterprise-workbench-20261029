let activeView='tasks';
function showView(view,scroll=true){
 activeView=view;
 document.querySelectorAll('[data-workspace]').forEach(e=>e.hidden=e.dataset.workspace!==view);
 document.querySelectorAll('[data-view]').forEach(e=>{const active=e.dataset.view===view;e.classList.toggle('active',active);e.setAttribute('aria-selected',String(active))});
 if(scroll)$('workspaceTop').scrollIntoView({block:'start',behavior:'smooth'});
}
let wizardStep=1,confirmedKnowledge='',confirmedQuestions='';
function knowledgeSignature(){return JSON.stringify([kbId,...['kbName','kbBrand','kbAudience','kbFacts'].map(id=>$(id).value)])}
function questionsSignature(){return JSON.stringify([$('planProduct').value,$('planQuestions').value,$('planRounds').value,[...document.querySelectorAll('[name=planChannel]:checked')].map(e=>e.value)])}
function knowledgeReady(){return !!kbId&&!kbDirty&&confirmedKnowledge===knowledgeSignature()&&$('planProduct').value===kbId}
function confirmQuestions(){
 if(!validateQuestions())return;
 const rounds=$('planRounds');if(!rounds.value||!rounds.checkValidity()){message('请填写每题采集轮数（1至10）后确认。',true);rounds.focus();return}
 confirmedQuestions=questionsSignature();showStep(3);
}
function showStep(n){
 showView('editor',false);
 if(busy&&operation?.name!=='kb_save'&&operation?.name!=='plan_save'&&operation?.name!=='plan_delete')return;
 if(n>1&&!knowledgeReady()){showStep(1);message('请先点击下方“选择此产品，下一步”，确认成功后才能继续。',true);return}
 if(n===3&&confirmedQuestions!==questionsSignature()){showStep(2);message('请先点击“确认问题和渠道，下一步”，确认后才能设置时间与预算。',true);return}
 const hint=$('wizardFeedback');hint.hidden=false;hint.className='hint';
 hint.textContent=kbDirty?'产品资料待确认，保存任务前请先完成第一步。':n===1?'选择已建好的产品知识库，再配置问题。':n===2?'填写监测问题并选择采集渠道。':'填写执行时间与创作预算，然后保存任务。';
 wizardStep=n;document.querySelectorAll('[data-step]').forEach(e=>e.hidden=Number(e.dataset.step)!==n);
 document.querySelectorAll('[data-wizard]').forEach(e=>{e.classList.toggle('primary',Number(e.dataset.wizard)===n);e.setAttribute('aria-current',Number(e.dataset.wizard)===n?'step':'false')});
 scheduleSummary();$('wizardNav').scrollIntoView({block:'start',behavior:'smooth'});
}
function validateQuestions(){
 if(!knowledgeReady()){showStep(1);message('产品资料尚未确认或有未保存的修改，请在下方点击“选择此产品，下一步”后再保存任务。',true);return false}
 if(!$('planProduct').value){message('请先保存产品知识库',true);return false}
 const qs=$('planQuestions').value.split('\n').map(s=>s.trim()).filter(Boolean);
 if(!qs.length){message('请填写本任务要监测的问题，每行一题',true);return false}
 if(new Set(qs).size!==qs.length){message('问题存在重复，请去重后继续',true);return false}
 if(!document.querySelector('[name=planChannel]:checked')){message('请至少选择一个采集渠道',true);return false}
 return true;
}
function validateSchedule(){
 if(!validateQuestions())return false;
 if(confirmedQuestions!==questionsSignature()){showStep(2);message('问题、渠道或轮数已修改，请重新确认后继续。',true);return false}
 for(const id of ['planName','planFrequency','planTaskType','planStart','planCapture','planWriting','planRounds','planCount','planArticleBudget','planTaskBudget']){
  const el=$(id);if(id==='planCount'&&Number($('planTarget').value)>0)continue;if(!el.value.trim()||!el.checkValidity()){showStep(3);message('请完整填写时间与预算，检查任务名称、周期、类型、日期、时间、轮数、篇数和预算。',true);el.focus();return false}
 }if($('planTarget').value&&!$('planTarget').checkValidity()){message('任务总篇数应为1至100篇',true);return false}return true;
}
function scheduleSummary(){
 $('planCount').disabled=Number($('planTarget').value)>0;
 if(['planFrequency','planTaskType','planStart','planCapture','planWriting','planCount'].some(id=>!(id==='planCount'&&Number($('planTarget').value)>0)&&!$(id).value)){ $('schedulePreview').textContent='请选择任务周期、日期和时间，并填写篇数与预算后保存。';return}
 const n=$('planQuestions').value.split('\n').filter(s=>s.trim()).length,count=Number($('planCount').value)||1;
 $('schedulePreview').textContent=($('planFrequency').value==='once'?'仅执行一次：'+$('planStart').value:'每天常规执行，首次日期 '+$('planStart').value)+'，'+$('planCapture').value+' 开始采集，'+$('planWriting').value+' 起在素材齐全后分析。'+($('planTaskType').value==='capture_only'?'本任务只采集素材。':Number($('planTarget').value)>0?'汇总'+n+'个问题的独立素材，本次目标'+Number($('planTarget').value)+'篇，按真实体裁分配。':n+'个问题，每类最多'+count+'篇，排行类与科普类合计最多'+n*count*2+'篇。')+' 共享账号忙时等待，任务不会抢占主GEO。';
}
function fillAnalysis(a){
 $('kbExtracted').hidden=!a;
 $('kbExtracted').textContent=a?[a.specification&&'规格：'+a.specification,a.manufacturer&&'生产企业：'+a.manufacturer,a.filing_number&&'备案/标准号：'+a.filing_number].filter(Boolean).join('；'):'';
 $('kbAnalysis').textContent=a?JSON.stringify({识别依据:a.field_evidence,专利号原文:a.patent_numbers,需复核的原文声明:a.claims_to_review,说明:a.note},null,2):'尚未导入Word';
}
function newCreationTask(){
 loadKnowledge('');loadPlan('');$('kbWord').value='';document.querySelectorAll('[data-step] .action-feedback').forEach(e=>e.hidden=true);showStep(1);renderSelectedKnowledge();buttons();
}
function selectKnowledge(id){
 loadKnowledge(id);$('planProduct').value=kbId;planDirty=true;renderSelectedKnowledge();
}
function editCreationPlan(id){
 const p=(data.studio?.plans||[]).find(p=>p.plan_id===id);
 if(p)loadKnowledge(p.product_id);loadPlan(id);confirmedKnowledge=knowledgeSignature();confirmedQuestions=questionsSignature();renderSelectedKnowledge();showStep(1);
}
function loadKnowledge(id){
 confirmedKnowledge='';confirmedQuestions='';kbId=id||'';importId='';kbDirty=false;const kb=(data.studio?.products||[]).find(p=>p.product_id===kbId),p=kb?.product||{};
 $('kbSelect').value=kbId;$('kbName').value=p.name||'';$('kbBrand').value=p.brand||'';$('kbAudience').value=p.audience||'';$('kbFacts').value=(p.facts||[]).map(f=>f.text).join('\n');fillAnalysis(kb?.word_source?.analysis);
 $('kbSource').textContent=kb?.word_source?.filename?'已导入：'+kb.word_source.filename:kb?'已有产品知识库，可编辑或重新导入':'请选择Word文件，系统将自动识别并填入信息';
}
function loadPlan(id){
 planId=id||'';planDirty=false;const p=(data.studio?.plans||[]).find(p=>p.plan_id===planId)||{};
 $('planSelect').value=planId;$('planProduct').value=p.product_id||kbId||'';
 $('editorTitle').textContent=planId?'编辑创作任务':'新建创作任务';$('editorMode').textContent=planId?'正在编辑：'+(p.name||p.product?.name||'已有任务')+'。修改后点击保存修改。':'填写三步配置后保存，新任务才会加入队列。';$('planSave').textContent=planId?'保存修改':'保存为草稿';
 $('planName').value=p.name||(planId?p.product.name+'创作任务':'');$('planFrequency').value=p.frequency||(planId?'daily':'');$('planTaskType').value=p.task_type||(planId?'collect_write':'');
 $('planStart').value=p.start_date||'';$('planCapture').value=p.capture_time||'';$('planWriting').value=p.writing_time||'';$('planRounds').value=p.rounds??'';$('planCount').value=p.max_per_category??'';$('planTarget').value=p.article_target||'';$('planEnabled').checked=!!p.enabled;
 $('planArticleBudget').value=planId?(p.article_budget_cny??data.settings.article_budget_cny):'';$('planTaskBudget').value=planId?(p.task_budget_cny??data.settings.daily_budget_cny):'';
 $('planArticleBudget').max=data.settings.article_budget_cny;$('planTaskBudget').max=data.settings.daily_budget_cny;
 $('planQuestions').value=(p.questions||[]).join('\n');
 $('planChannels').innerHTML=[['deepseek','DeepSeek'],['baidu_ai','百度卡片'],['wenxin_card','文心卡片']].map(([id,name])=>`<label class="channel-option"><input type="checkbox" name="planChannel" value="${id}" ${(p.channels||[]).includes(id)?'checked':''} onchange="planDirty=true">${name}</label>`).join('');
 $('planHint').textContent=p.legacy_capture&&!p.enabled?'这是原独立素材采集配置，自动付费创作尚未启用。':'保存任务后按设置执行。素材未齐时等待；达到预算上限保留进度。';scheduleSummary();
}
function studioResult(name,r){
 if(name==='product_image_upload'){$('productImageFile').value='';$('productImagePreview').hidden=true}

 if(name==='kb_upload'){$('libraryWord').value='';$('libraryNotes').value='';$('libraryName').value='';libraryNextTarget=r.library_id}
 if(name==='kb_edit'){libraryEditVersion=r.version;$('libraryEditor').hidden=true}

 if(name==='kb_import'){
  confirmedKnowledge='';confirmedQuestions='';importId=r.import_id;kbId='';kbDirty=true;$('kbSelect').value='';const a=r.analysis||{};
  $('kbName').value=a.name||'';$('kbBrand').value=a.brand||'';$('kbAudience').value=a.audience||'';$('kbFacts').value=(a.facts||r.text.split('\n')).join('\n');fillAnalysis(a);
  $('kbSource').textContent='已识别 '+r.filename+'（'+r.paragraphs+'段），请确认下方自动填入的信息。';
 }
 if(name==='kb_save'){kbId=r.product_id;kbDirty=false;importId='';planDirty=true;confirmedKnowledge=knowledgeSignature();confirmedQuestions=''}
 if(name==='plan_save'){newCreationTask();showView('tasks')}
 if(name==='plan_delete'){deleteTarget='';deleteFeedback=null;data.studio.plans=data.studio.plans.filter(p=>p.plan_id!==r.plan_id);data.studio.daily_tasks=data.studio.daily_tasks.filter(t=>t.plan_id!==r.plan_id);if(planId===r.plan_id)newCreationTask();showView('tasks');renderDailyTasks()}
}
function planPayload(enable){return{...(planId?{plan_id:planId}:{}),name:$('planName').value,frequency:$('planFrequency').value,task_type:$('planTaskType').value,article_budget_cny:Number($('planArticleBudget').value),task_budget_cny:Number($('planTaskBudget').value),product_id:$('planProduct').value,questions:$('planQuestions').value.split('\n').map(s=>s.trim()).filter(Boolean),channels:[...document.querySelectorAll('[name=planChannel]:checked')].map(c=>c.value),capture_time:$('planCapture').value,writing_time:$('planWriting').value,start_date:$('planStart').value,rounds:Number($('planRounds').value),max_per_category:Number($('planCount').value)||10,article_target:Number($('planTarget').value)||0,enabled:enable??false}}
function renderStudio(){
 const st=data.studio;if(!st)return;const selectedKB=kbId,selectedPlan=planId,selectedProduct=$('planProduct').value;
 $('kbSelect').innerHTML='<option value="">请选择已建好的产品</option>'+st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');
 $('planProduct').innerHTML='<option value="">请选择产品知识库</option>'+st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');
 $('planSelect').innerHTML='<option value="">新建任务</option>'+st.plans.map(p=>`<option value="${p.plan_id}">${escape(p.name||p.product.name)} · ${p.frequency==='once'?'仅一次':'每日'}</option>`).join('');
 if(!studioLoaded){studioLoaded=true;loadKnowledge('');loadPlan('')}
 else{$('kbSelect').value=selectedKB;$('planSelect').value=selectedPlan;$('planProduct').value=selectedProduct}
 $('studioLimits').textContent='共享限额：单篇含分析 ¥'+data.settings.article_budget_cny+'，每日所有任务合计 ¥'+data.settings.daily_budget_cny+'。你设置的任务预算会额外限制本次执行，不会自动提高共享限额。';
 renderDailyTasks();renderLibrary();renderSelectedKnowledge();
}
function taskListItem(p,st){
 const days=st.daily_tasks.filter(t=>t.plan_id===p.plan_id);
 const t=(p.frequency==='once'?days.find(t=>t.date===p.start_date):days.find(t=>t.date===st.today))||days.slice().sort((a,b)=>b.date.localeCompare(a.date))[0];
 const state=t?.status||(p.enabled?'scheduled':'not_enabled');
 const target=Math.max(0,Number(t?.target_per_model)||p.questions.length*(p.rounds||1));
 const channels=p.channels||[],total=target*channels.length;
 const done=t?channels.reduce((sum,id)=>sum+Math.min(target,Math.max(0,Number(t.progress.find(v=>v.id===id)?.completed)||0)),0):0;
 const questions=Number(t?.questions)||p.questions.length,writing=Math.min(questions,Math.max(0,Number(t?.writing_complete)||0));
 const bar=(label,value,max,caption)=>`<div class="queue-progress"><div><span>${label}</span><small>${caption}</small></div><progress value="${value}" max="${max||1}" aria-label="${label}" aria-valuetext="${value}/${max}"></progress></div>`;
 const capture=bar('素材采集',done,total,`${done} / ${total} 次 · ${total?Math.floor(done*100/total):0}%`);
 const outputTarget=Number(t?.article_target||p.article_target)||0;const creation=(t?.task_type||p.task_type)==='capture_only'?'<small class="queue-note">仅采集素材，不执行文章创作</small>':outputTarget?bar('文章创作',Math.min(outputTarget,t?.articles||0),outputTarget,`${t?.articles||0} / ${outputTarget} 篇已审稿成稿`):bar('文章创作',writing,questions,`${writing} / ${questions} 个问题完成 · ${t?.articles||0} 篇成稿`);
 const finished=isTerminal(state),resume=dayActions(t).includes('day_resume');
 const canControl=dayActions(t).length>0;
 const control=canControl?`<button data-day-action="${resume?'day_resume':'day_pause'}" data-plan="${p.plan_id}" data-date="${t.date}">${resume?(state==='paused'?'继续':'检查并继续'):'暂停'}</button>`:`<button disabled data-control-unavailable>${finished?(state==='complete'||state==='capture_only_complete'?'已完成':'已结束'):p.enabled?'等待执行':'未启用'}</button>`;
 const status=studioStates[state]||({'scheduled':'等待定时','not_enabled':'草稿，未启用','capture_only':'仅采集素材'}[state])||state;
 return `<article class="queue-item"><div class="task-description"><b>${escape(p.name||p.product.name+'创作任务')}</b><small>${p.frequency==='once'?'临时 · '+escape(p.start_date)+' '+escape(p.capture_time)+'，仅执行一次':'每天 '+escape(p.capture_time)+' 开始采集 · 首次 '+escape(p.start_date)}（北京时间）</small><small>${p.task_type==='capture_only'?'仅采集素材':'最早 '+escape(p.writing_time)+' 分析仿写'} · ${p.questions.length}题 · ${p.article_target?'每次目标'+p.article_target+'篇':'每题每类最多'+p.max_per_category+'篇'} · 本次预算 ¥${p.task_budget_cny??data.settings.daily_budget_cny}</small><div class="queue-progress-group"><small class="queue-note">执行日期：${escape(t?.date||p.start_date)}${state==='paused'?' · 已暂停，已完成进度保留':finished&&p.frequency==='daily'&&p.enabled?' · 本次已结束，后续仍按每日计划执行':''}</small>${capture}${creation}${t?.error?`<small class="queue-note">${escape(t.error)}</small>`:''}</div></div><div class="queue-controls"><span class="badge">${escape(status)}</span><div class="row">${control}<button data-edit-plan="${p.plan_id}">查看与编辑</button><button class="danger" data-delete-plan="${p.plan_id}" aria-expanded="${deleteTarget===p.plan_id}">删除任务</button></div>${deleteTarget===p.plan_id?`<div id="deleteDialog" role="group" aria-labelledby="deleteTitle"><h3 id="deleteTitle">确定删除这个任务？</h3><p class="muted">停止后续采集和创作，并从任务列表移除。已有文章、素材和费用记录保留。</p><div class="row"><button id="deleteCancel">取消</button><button id="deleteConfirm" class="danger primary">确认删除</button></div><p id="deleteFeedback" class="action-feedback" role="status" aria-live="polite" hidden></p></div>`:''}</div></article>`;
}
function renderDailyTasks(){
 const st=data?.studio;if(!st)return;const date=$('dateFilter').value||st.today;
 $('dailyProduct').innerHTML=$('productFilter').innerHTML;$('dailyProduct').value=$('productFilter').value;$('dailyDate').innerHTML=[...$('dateFilter').options].filter(o=>o.value).map(o=>`<option value="${escape(o.value)}">${escape(o.text)}</option>`).join('');$('dailyDate').value=date;
 const tasks=st.daily_tasks.filter(t=>t.date===date&&(!$('productFilter').value||t.product.id===$('productFilter').value));
 $('dailyDateHint').textContent='进度日期：'+date+'（北京时间），任务队列同时列出未来计划。';
 $('dailyMetrics').innerHTML=[['当天任务',tasks.length],['正在执行',tasks.filter(t=>['collecting','creating'].includes(t.status)).length],['已完成 / 需处理',tasks.filter(t=>t.status==='complete').length+' / '+tasks.filter(t=>['needs_attention','waiting_login'].includes(t.status)).length]].map(([k,v])=>`<div class="metric"><small>${k}</small><b>${v}</b></div>`).join('');
 const term=($('taskSearch')?.value||'').trim().toLowerCase(),state=$('taskState')?.value||'';
 const visiblePlans=st.plans.filter(p=>(!term||(p.name||p.product.name).toLowerCase().includes(term)||p.product.name.toLowerCase().includes(term))&&(!state||String(!!p.enabled)===state));
 $('taskTotals').innerHTML=[['已保存任务',st.plans.length],['已启用',st.plans.filter(p=>p.enabled).length],['今日执行中',st.daily_tasks.filter(t=>t.date===st.today&&['collecting','creating'].includes(t.status)).length]].map(([k,v])=>`<div><span>${k}</span><strong>${v}</strong></div>`).join('');
 $('planQueue').innerHTML=visiblePlans.length?visiblePlans.map(p=>taskListItem(p,st)).join(''):'<div class="empty">'+(st.plans.length?'没有符合筛选条件的任务。':'还没有任务，点击右上角“新建任务”开始。')+'</div>';
 $('dailyCards').innerHTML=tasks.length?tasks.map(t=>`<article class="job"><div class="row between"><h3>${escape(t.name||t.product.name)}</h3><span class="badge">${escape(studioStates[t.status]||t.status)}</span></div><small>${escape(t.date)} · ${escape(t.product.name)} · ${t.frequency==='once'?'临时一次':'每天常规'} · ${t.capture_time} 采集 / ${t.writing_time} 起分析</small><div class="material-progress">${t.progress.map(m=>`<div class="card"><small>${escape(m.name)}</small><b>${m.completed} / ${t.target_per_model}</b><small>${m.blocked?.kind?'需要登录或验证':m.recovery?.status==='cooling_down'?(m.recovery.kind==='verification'?'平台安全验证，冷却等待':'读取未完成，退避等待'):'问题采集进度'}</small></div>`).join('')}</div><p><b>${t.writing_complete}/${t.questions}个问题已完成创作 · ${t.articles}篇成稿</b></p>${t.error?`<p class="error">${escape(t.error)}</p>`:''}<div class="row">${dayActions(t).length>0?`<button data-day-action="${['paused','needs_attention','waiting_login'].includes(t.status)?'day_resume':'day_pause'}" data-plan="${t.plan_id}" data-date="${t.date}">${['paused','needs_attention','waiting_login'].includes(t.status)?'检查并继续':'暂停任务'}</button>`:''}<a class="button" href="${link('all-approved','','bundle')+'&'+new URLSearchParams({plan:t.plan_id,date:t.date})}">下载本任务成稿与日志</a><button data-edit-plan="${t.plan_id}">查看任务配置</button></div></article>`).join(''):'<div class="empty">所选日期暂无执行记录，请在上方队列查看计划执行时间。</div>';
 document.querySelectorAll('[data-day-action]').forEach(b=>b.onclick=()=>act(b.dataset.dayAction,{plan_id:b.dataset.plan,date:b.dataset.date}));
 document.querySelectorAll('[data-edit-plan]').forEach(b=>b.onclick=()=>{editCreationPlan(b.dataset.editPlan)});
 document.querySelectorAll('[data-delete-plan]').forEach(b=>b.onclick=()=>askDelete(b.dataset.deletePlan));bindDeleteControls();buttons();
}
function renderLibrary(){
 const raw=library(),held=raw.filter(a=>a.quality_status==='needs_revision'),all=raw.filter(a=>a.quality_status!=='needs_revision'),term=$('search').value.trim().toLowerCase(),filter=$('outputFilter').value;
 const rows=all.filter(a=>matchesTask(a)&&(!term||a.title.toLowerCase().includes(term))&&(filter==='all'||(filter==='new'?a.job!=='legacy-original':a.job==='legacy-original')));
 $('library').innerHTML=rows.length?rows.map(a=>`<article class="output"><div><h3>${escape(a.title)}</h3><small>${escape(a.date)} · ${escape(a.task_name||a.product.name)} · ${escape(a.category||a.id.split('/')[1])} · ${a.quality_status==='ready_with_disputes'?'待核对意见已保留，可供审阅':'已通过审稿'}</small>${a.quality_status==='ready_with_disputes'?'<p class="muted">尚有未确认意见；下载包保留复核记录，未将争议认定为正确。</p>':''}<p class="source-line">参考原文：${a.primary_reference?.url?`<a href="${escape(a.primary_reference.url)}" target="_blank" rel="noopener noreferrer">${escape(a.primary_reference.title||a.primary_reference.domain)}</a>`:'历史记录未标注'}<small>${escape(a.primary_reference?.media||'')} · ${escape(a.primary_reference?.domain||'')} · 账号身份以原文记录为准</small></p></div><div class="row"><button class="article-view" data-kind="markdown" data-job="${a.job}" data-id="${escape(a.id)}">预览文章</button><button class="article-view" data-kind="info" data-job="${a.job}" data-id="${escape(a.id)}">来源与执行日志</button><a class="button primary" href="${link(a.job,a.id,'package')}">下载文章及溯源</a><a class="button" href="${link(a.job,a.id,'word')}">Word</a></div></article>`).join(''):'<div class="empty">当前筛选暂无成稿。执行完成后会出现在这里。</div>';
 $('totalArticles').textContent=rows.length;$('newArticles').textContent=rows.filter(a=>a.job!=='legacy-original').length;$('legacyCount').textContent=rows.filter(a=>a.job==='legacy-original').length;$('filterSummary').textContent='当前筛选 '+rows.length+' 篇 / 可下载 '+all.length+' 篇，下载包含文章、原文出处与执行日志。'+(held.length?' 另有 '+held.length+' 篇旧稿未通过正文质量复核，已停止下载；原稿和日志保留，修订通过后恢复。':'');
 const dl=$('downloadAll');dl.textContent='打包下载筛选结果（'+rows.length+'篇）';dl.href=link('all-approved','','bundle')+'&'+new URLSearchParams({date:$('dateFilter').value,product:$('productFilter').value,source:filter,search:$('search').value.trim()});if(!rows.length)dl.removeAttribute('href');
 document.querySelectorAll('.article-view').forEach(b=>b.onclick=async()=>{try{$('previewText').textContent='正在读取…';$('preview').showModal();const r=await fetch(link(b.dataset.job,b.dataset.id,b.dataset.kind));if(!r.ok)throw Error('读取失败，请刷新后重试');$('previewText').textContent=await r.text()}catch(e){$('previewText').textContent=e.message}});
}
document.querySelectorAll('[data-step]').forEach(e=>e.hidden=Number(e.dataset.step)!==wizardStep);
document.querySelector('[data-wizard="1"]').classList.add('primary');

// Validate downloads before saving: an expired login/error page must never become a .zip.
async function downloadArticleFile(anchor){
 let status=$('downloadStatus');
 if(!status){status=document.createElement('p');status.id='downloadStatus';status.setAttribute('role','status');$('outputs').prepend(status)}
 if(anchor.dataset.downloading)return;
 anchor.dataset.downloading='1';anchor.setAttribute('aria-busy','true');status.textContent='正在打包并校验文件，请稍候…';
 try{
  const r=await fetch(anchor.href,{credentials:'same-origin',redirect:'follow',cache:'no-store'});
  const mime=(r.headers.get('content-type')||'').split(';')[0];
  if(!r.ok||!['application/zip','application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(mime)){
   let message='下载失败，请刷新页面后重试。';
   if(mime==='application/json'){try{message=(await r.json()).message||message}catch{}}
   else if(mime==='text/html'||r.url.includes('/login'))message='登录已过期，请重新登录面板后下载；未保存错误文件。';
   throw Error(message);
  }
  const bytes=new Uint8Array(await r.arrayBuffer()),expected=Number(r.headers.get('x-download-bytes')||0);
  if(bytes.length<22||bytes[0]!==80||bytes[1]!==75||(expected&&bytes.length!==expected))throw Error('文件传输不完整，未保存损坏文件，请重新下载。');
  let end=false;for(let i=bytes.length-22;i>=Math.max(0,bytes.length-65557);i--){if(bytes[i]===80&&bytes[i+1]===75&&bytes[i+2]===5&&bytes[i+3]===6&&i+22+bytes[i+20]+256*bytes[i+21]===bytes.length){end=true;break}}
  if(!end)throw Error('文件缺少完整压缩目录，未保存，请重新下载。');
  const digest=r.headers.get('x-content-sha256');
  if(digest&&globalThis.crypto?.subtle){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==digest)throw Error('文件校验不一致，未保存，请重新下载。')}
  const ext=mime==='application/zip'?'.zip':'.docx',blob=new Blob([bytes],{type:mime}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='创作成稿_'+new Date().toISOString().slice(0,10)+ext;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
  status.textContent='文件完整性校验通过，已开始保存。压缩包请先完整解压，再打开其中的Word。';
 }catch(e){status.textContent=e.message||'下载失败，请稍后重试'}
 finally{delete anchor.dataset.downloading;anchor.removeAttribute('aria-busy')}
}
document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||!u.pathname.endsWith('/download')||!['bundle','package','word'].includes(u.searchParams.get('kind')))return;e.preventDefault();downloadArticleFile(a)});

// Optional per-task detail and genre targets; loading old tasks preserves their contracts.
const detailControls=document.createElement('details');detailControls.className='hint';
detailControls.innerHTML='<summary>产品介绍与分类篇数（可选）</summary><div class="grid"><label>排行类目标篇数<input id="planRankingTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label><label>测评类目标篇数<input id="planReviewTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label><label>科普类目标篇数<input id="planScienceTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label></div><label><input id="planRichProduct" type="checkbox"> 增加自有产品信息量</label><div class="grid"><label>排行产品介绍目标汉字<input id="planRankingDetail" type="number" min="200" max="2000" placeholder="例如1000"></label><label>科普产品举例目标汉字<input id="planScienceDetail" type="number" min="200" max="2000" placeholder="例如600"></label></div><small>成分、规格和有条件的检测摘要按知识库展开。检测摘要保留来源与试验边界；篇数不足时显示缺额，不以另一类别顶替。</small>';
$('planHint').before(detailControls);
const detailBaseLoadPlan=loadPlan,detailBasePayload=planPayload;
loadPlan=function(id){detailBaseLoadPlan(id);const p=(data.studio?.plans||[]).find(p=>p.plan_id===planId)||{};const c=p.writing_profile||{};
 $('planRankingTarget').value=p.genre_targets?.['排行类']??'';$('planScienceTarget').value=p.genre_targets?.['科普类']??'';$('planReviewTarget').value=p.genre_targets?.['测评类']??'';
 $('planRichProduct').checked=!!c.ranking_hanzi;$('planRankingDetail').value=c.ranking_hanzi??'';$('planScienceDetail').value=c.science_hanzi??'';};
planPayload=function(enable){const p=detailBasePayload(enable),r=Number($('planRankingTarget').value),s=Number($('planScienceTarget').value),v=Number($('planReviewTarget').value);
 p.genre_targets=(r||s||v)?{...(r?{'排行类':r}:{}),...(s?{'科普类':s}:{}),...(v?{'测评类':v}:{})}:{};
 p.writing_profile=$('planRichProduct').checked?{ranking_hanzi:Number($('planRankingDetail').value),science_hanzi:Number($('planScienceDetail').value),ranking_facts:8,science_facts:5}:{};return p;};
detailControls.addEventListener('input',()=>{planDirty=true});
showView('tasks',false);

