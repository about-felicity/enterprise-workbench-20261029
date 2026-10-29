
document.body.dataset.embedded=String(window.parent!==window);
const API='/api/';let kbDirty=false,planDirty=false,kbId='',planId='',importId='',studioLoaded=false;let csrf='',busy=false,connected=false,data=null,catalogData=null,productData={},materialDirty=false,refreshing=false;
let pendingAction=JSON.parse(sessionStorage.getItem('geo.creation.pending')||'null');const $=id=>document.getElementById(id),escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const dt=v=>v?new Date(typeof v==='number'?v*1000:v).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'等待下一次采集';
let operation=null,operationTimer=null,lockedFields=new Map(),deleteTarget='',deleteFeedback=null;
const terminalStates=new Set(['complete','capture_only_complete','complete_with_failures','insufficient_materials','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles']);
function isTerminal(state){return terminalStates.has(state)}
function dayActions(t){return t?.allowed_actions||(!t||isTerminal(t.status)?[]:['paused','needs_attention','waiting_login'].includes(t.status)?['day_resume']:['collecting','creating','waiting_for_geo','waiting_writing','waiting_capture_capacity','capture_retrying'].includes(t.status)?['day_pause']:[])}
function message(text,error=false,state='success'){
 const kind=error?'error':state;
 const box=$('message');box.textContent=text;box.style.display='block';box.className='action-feedback';box.dataset.state=kind;box.setAttribute('role',error?'alert':'status');
 if(operation?.name==='plan_delete'){deleteFeedback={text,kind};renderDeleteFeedback()}
 if(activeView==='knowledge'){const feedback=$(operation?.name==='product_image_upload'?'productImageFeedback':operation?.name==='kb_edit'&&!$('libraryEditor').hidden?'libraryEditFeedback':'libraryFeedback');feedback.textContent=text;feedback.dataset.state=kind;feedback.hidden=false}
 const section=document.querySelector('[data-step="'+wizardStep+'"]');
 if(activeView==='editor'&&section){let feedback=section.querySelector('.action-feedback');if(!feedback){feedback=document.createElement('p');feedback.className='action-feedback';feedback.setAttribute('role','status');section.querySelector('.wizard-actions').before(feedback)}feedback.textContent=text;feedback.dataset.state=kind;feedback.hidden=false}
 if(operation?.name==='kb_import'){$('kbSource').textContent=text}
}
function operationButton(b){
 if(!operation||operation.finishing)return false;
 const ids={product_image_upload:'productImageUpload',kb_upload:'libraryUpload',kb_edit:'libraryEditSave',kb_import:'kbImport',kb_save:'kbSave',plan_save:operation.body?.enabled?'planEnable':'planSave',balance:'balance',new:'new'};
 return b.id===ids[operation.name]||(b.dataset.plan===operation.body?.plan_id&&b.dataset.date===operation.body?.date&&b.dataset.dayAction===operation.name)||(b.dataset.job===operation.body?.job_id&&b.dataset.action===operation.name)||(operation.name==='plan_delete'&&(b.id==='deleteConfirm'||b.dataset.deletePlan===operation.body?.plan_id));
}
function buttons(){
 const blocked=busy||!connected||!!pendingAction;
 document.querySelectorAll('button').forEach(b=>{
  const readonly=b.hasAttribute('data-view')||b.classList.contains('article-view')||b.classList.contains('preview');
  b.disabled=b.hasAttribute('data-control-unavailable')||(!readonly&&blocked)||(b.id==='kbImport'&&!$('kbWord').files.length)||(b.id==='libraryUpload'&&!$('libraryWord').files.length)||(b.id==='productImageUpload'&&(!imageBatchQueue.some(i=>['waiting','failed'].includes(i.status))));
  if(busy&&operationButton(b)){if(!b.dataset.idleLabel)b.dataset.idleLabel=b.textContent;b.textContent=operation.label;b.setAttribute('aria-busy','true')}
  else if(b.dataset.idleLabel){b.textContent=b.dataset.idleLabel;delete b.dataset.idleLabel;b.removeAttribute('aria-busy')}
 });
 if(busy){document.querySelectorAll('[data-workspace="editor"] input,[data-workspace="editor"] textarea,[data-workspace="editor"] select,[data-workspace="knowledge"] input,[data-workspace="knowledge"] textarea,[data-workspace="knowledge"] select').forEach(e=>{if(!lockedFields.has(e))lockedFields.set(e,e.disabled);e.disabled=true})}
 else if(lockedFields.size){for(const[e,disabled]of lockedFields)e.disabled=disabled;lockedFields.clear();scheduleSummary()}
 if($('imageUploadHint'))renderImageUploadHint();
 $('imageBatchRetry').hidden=!pendingAction||!imageBatchQueue.some(i=>i.status==='uncertain');$('imageBatchRetry').disabled=busy||imageBatchActive||!connected;
 $('retryAction').hidden=!pendingAction||busy;$('retryAction').disabled=busy||!connected;
 syncUploadControls();
}
function renderDeleteFeedback(){const box=$('deleteFeedback');if(box&&deleteFeedback){box.textContent=deleteFeedback.text;box.dataset.state=deleteFeedback.kind;box.hidden=false}}
function askDelete(id){if(busy||pendingAction||!connected)return;if(!data.studio.plans.some(p=>p.plan_id===id))return;deleteTarget=id;deleteFeedback=null;renderDailyTasks();$('deleteCancel').focus({preventScroll:true});revealDelete(id)}
function revealDelete(id){
 const reveal=()=>{if(deleteTarget===id)$('deleteDialog')?.scrollIntoView({block:'nearest'})};
 // The dashboard resizes its iframe asynchronously after our layout message.
 // Reveal again after the actual host height changes, not after a guessed delay.
 const host=window.frameElement;if(host){const observer=new MutationObserver(()=>{reveal();observer.disconnect()});observer.observe(host,{attributes:true,attributeFilter:['style','height']});setTimeout(()=>observer.disconnect(),2000)}
 reveal();
}
function bindDeleteControls(){
 if($('deleteCancel'))$('deleteCancel').onclick=()=>{const id=deleteTarget;deleteTarget='';deleteFeedback=null;renderDailyTasks();document.querySelector('[data-delete-plan="'+id+'"]')?.focus({preventScroll:true})};
 if($('deleteConfirm'))$('deleteConfirm').onclick=()=>act('plan_delete',{plan_id:deleteTarget});
 renderDeleteFeedback();
}
async function request(path,body){const headers={};let item;if(body){const payload=JSON.stringify(body);if(pendingAction&&(pendingAction.path!==path||pendingAction.payload!==payload))throw Error('上次操作尚未确认，请先核对');item=pendingAction||{path,payload,key:[...crypto.getRandomValues(new Uint8Array(16))].map(x=>x.toString(16).padStart(2,'0')).join('')};pendingAction=item;try{if(item.payload.length<600000)sessionStorage.setItem('geo.creation.pending',JSON.stringify(item))}catch{};Object.assign(headers,{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Action-Id':item.key})}const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),path==='control/kb_import'?120000:45000);try{const r=await fetch(API+path,{method:body?'POST':'GET',headers,body:item?.payload,signal:controller.signal,cache:'no-store'});let result;try{result=await r.json()}catch{if(body&&r.status>=400&&r.status<500){pendingAction=null;sessionStorage.removeItem('geo.creation.pending')}throw Error(r.status===413?'上传被入口拒绝：请求过大，请尝试单张较小图片。':r.status===401||r.status===403?'登录已失效，请刷新页面后再上传。':'服务返回了无法识别的响应（HTTP '+r.status+'），请稍后重试。')}if(body&&r.status>=500)throw Error('操作结果未确认');if(body){pendingAction=null;sessionStorage.removeItem('geo.creation.pending')}if(!r.ok||result.ok===false)throw Error(result.message||'请求失败');return result}catch(e){if(body&&pendingAction)throw Error('操作结果未确认，已保留原操作编号；请点击核对重试，避免重复执行。');throw e}finally{clearTimeout(timer)}}

function renderArticlePreview(text,kind){
 const host=$('previewText');host.replaceChildren();
 if(kind!=='markdown'){host.textContent=text;return;}
 for(const line of text.split('\n')){
  const image=line.match(/^!\[产品图片\]\(\/api\/geo-creation\/product_image\?id=(image-[a-f0-9]{32})\)$/);
  if(image){const img=document.createElement('img');img.src=API+'product_image?id='+image[1];img.alt='产品图片';img.style.cssText='display:block;max-width:min(100%,530px);max-height:340px;width:auto;height:auto;object-fit:contain;margin:16px auto';host.append(img);continue;}
  if(!line.trim())continue;
  const heading=line.match(/^(#{1,6})\s+(.*)$/);const node=document.createElement(heading?'h'+Math.min(heading[1].length+1,6):'p');
  node.textContent=(heading?heading[2]:line).replace(/\*\*([^*]+)\*\*/g,'$1');host.append(node);
 }
}

function link(job,article,kind){return API+'download?'+new URLSearchParams({job,article:article||'',kind})}
const unknownProduct={id:'unknown',name:'未标注产品',brand:''};
function library(){if(!data)return[];return [...data.jobs.flatMap(j=>j.articles.map(a=>({...a,job:j.job_id,date:a.date||j.date,product:a.product||j.product||unknownProduct,origin:j.material_source==='dedicated'?'专用素材创作':'GEO素材创作'}))),...(data.legacy_articles||[]).map(a=>({...a,job:'legacy-original',date:a.date||a.id.split('/')[0],product:a.product||unknownProduct,origin:'历史成稿'}))]}
function beijingToday(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())}
function renderFilterOptions(){const all=library(),products=new Map(),dates=new Set([beijingToday()]);for(const a of [...all,...data.jobs,...(data.studio?.daily_tasks||[])]){const p=a.product||unknownProduct;products.set(p.id,p);if(a.date)dates.add(a.date)}const productValue=$('productFilter').value,dateValue=$('dateFilter').value;$('productFilter').innerHTML='<option value="">全部产品</option>'+[...products.values()].sort((a,b)=>a.name.localeCompare(b.name,'zh-CN')).map(p=>`<option value="${escape(p.id)}">${escape(p.name)}</option>`).join('');$('dateFilter').innerHTML='<option value="">全部日期</option>'+[...dates].sort().reverse().map(d=>`<option value="${escape(d)}">${escape(d)}</option>`).join('');$('productFilter').value=products.has(productValue)?productValue:'';$('dateFilter').value=dates.has(dateValue)?dateValue:''}
function matchesTask(item){return (!$('productFilter').value||(item.product||unknownProduct).id===$('productFilter').value)&&(!$('dateFilter').value||item.date===$('dateFilter').value)}
function applyFilters(){renderArticleLibrary();$('library').scrollTop=0;renderJobs();renderDailyTasks();buttons()}
function todayFilter(){$('dateFilter').value=beijingToday();applyFilters()}
function clearFilters(){$('productFilter').value='';$('dateFilter').value='';$('search').value='';$('outputFilter').value='all';applyFilters()}
function legacyRenderArticleLibrary(){const scroll=$('library').scrollTop,all=library(),term=$('search').value.trim().toLowerCase(),filter=$('outputFilter').value,rows=all.filter(a=>matchesTask(a)&&(!term||a.title.toLowerCase().includes(term))&&(filter==='all'||(filter==='new'?a.job!=='legacy-original':a.job==='legacy-original')));$('library').innerHTML=rows.length?rows.map(a=>`<article class="output"><div><h3>${escape(a.title)}</h3><small>${escape(a.date)} · ${escape(a.product.name)} · ${escape(a.origin)} · ${a.receipt?.delivery_mode==='direct'?'直接输出':a.quality_status==='ready_with_disputes'?'待核对意见已保留，可供审阅':'已通过审稿'}</small>${a.quality_status==='ready_with_disputes'?'':''}</div><div class="row"><button class="preview" data-job="${escape(a.job)}" data-id="${escape(a.id)}">预览正文</button>${a.word?`<a class="button primary" href="${link(a.job,a.id,'word')}">下载 Word</a>`:''}${a.markdown?`<a class="button" href="${link(a.job,a.id,'markdown')}">下载 Markdown</a>`:''}</div></article>`).join(''):'<div class="empty">该产品、日期和搜索条件下暂无成稿。可以清除筛选查看其他日期。</div>';$('library').scrollTop=scroll;$('totalArticles').textContent=rows.length;$('newArticles').textContent=rows.filter(a=>a.job!=='legacy-original').length;$('legacyCount').textContent=rows.filter(a=>a.job==='legacy-original').length;$('filterSummary').textContent='当前筛选 '+rows.length+' 篇 / 全库 '+all.length+' 篇';const params=new URLSearchParams({date:$('dateFilter').value,product:$('productFilter').value,source:filter,search:$('search').value.trim()});const dl=$('downloadAll');dl.textContent='打包下载筛选结果（'+rows.length+'篇）';dl.href=link('all-approved','','bundle')+'&'+params;dl.setAttribute('aria-disabled',String(!rows.length));if(!rows.length)dl.removeAttribute('href');document.querySelectorAll('.preview').forEach(b=>b.onclick=async()=>{try{$('previewText').textContent='正在读取成稿…';$('preview').showModal();const r=await fetch(link(b.dataset.job,b.dataset.id,'markdown'));if(!r.ok)throw Error('成稿暂时无法读取');renderArticlePreview(await r.text(),b.dataset.kind)}catch(e){$('previewText').textContent=e.message}})}
const stages={taxonomy:'素材分类',research:'证据分析',writer:'写稿',review:'独立审稿'};
function renderJobs(){const jobs=data.jobs.filter(matchesTask);$('jobs').innerHTML=jobs.length?jobs.map(j=>{const ready=j.articles.filter(a=>a.quality_status!=='needs_revision').length,held=j.articles.length-ready,complete=j.day?.status==='complete',terminal=isTerminal(j.day?.status)||j.control?.reason==='plan_deleted',paused=j.control.paused,state=complete?(held?'生成完成，部分稿件待修订':'本任务已完成'):j.day?.status==='complete_with_failures'?'已结束，部分文章未生成':paused?'已暂停':j.preparation==='pending'?'正在准备完整媒体素材':({completed_with_failures:'已结束，部分文章待修复',idle:'暂无待执行任务',queued:'排队等待执行',request_unknown:'请求结果待核对',response_saved:'已收到答复，待处理'})[j.health?.status]||'正在创作',counts=Object.entries(j.queue||{}).map(([key,n])=>{const [stage,status]=key.split(':');return(stages[stage]||stage)+'：'+n+'项'+({accepted:'已通过',pending:'待处理',revision_requested:'待修订',failed:'未通过'}[status]||status)}).join(' · ');return `<article class="job"><div class="row between"><h3>${escape(j.question)}</h3><span class="badge">${state}</span></div><small>${escape(j.date)} · ${escape((j.product||unknownProduct).name)} · ${j.material_source==='dedicated'?'创作专用素材':'GEO已有素材'} · 完整媒体素材 ${j.material_counts.full_articles} 篇</small><p><b>可供审阅 ${ready} 篇可下载成稿${held?`，另有 ${held} 篇待修订`:""}</b>，请在“成稿下载”中查看。</p>${paused&&!complete?``:''}${(j.quality_blocks||[]).map(b=>``).join('')}<div class="row">${ready?`<a class="button primary" href="${link(j.job_id,'','bundle')}">打包下载本任务成稿</a>`:''}${!terminal?`<button data-action="${paused?'resume':'pause'}" data-job="${j.job_id}">${paused?'继续创作':'暂停创作'}</button>`:''}</div><details><summary>执行详情与任务编号</summary><small>${escape(j.job_id)}</small><pre>${escape(JSON.stringify({queue:j.queue,worker:j.worker},null,2))}</pre></details></article>`}).join(''):'<div class="empty">当前产品和日期下暂无创作任务，可清除筛选或建立新任务。</div>';document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action,{job_id:b.dataset.job}))}
function legacyRenderMaterials(){const m=data.materials;if(!m)return;const cfg=m.settings,labels={scheduled:'等待定时',running:'专用素材采集中',complete:'今日采集完成',paused:'已手动暂停',pausing:'正在收尾后暂停',waiting_for_geo:'等待主GEO结束',waiting_for_geo_window:'已让出主监测时段',waiting_login_or_verification:'等待登录或人工验证',retrying:'异常恢复中'};$('materialState').textContent=labels[m.health.status]||'等待首次采集';$('materialProgress').innerHTML=m.progress.map(p=>`<div class="card"><small>${escape(p.name)}</small><b>${p.completed} / ${(cfg.questions||[]).length}</b><small>${p.blocked.kind?'需要登录或人工验证':'今日已采集'}</small></div>`).join('');if(!materialDirty){$('materialEnabled').checked=!!cfg.enabled;$('materialTime').value=cfg.time||'01:00';$('materialQuestions').value=(cfg.questions||[]).join('\n')}$('materialNext').textContent='下次计划：'+(m.next_run?dt(m.next_run)+'（北京时间）':'已关闭每日专用采集');$('questionCount').textContent=(cfg.questions||[]).length+'个专用问题 · 与GEO问题库独立'}
async function refresh(){
 if(refreshing)return refreshing;
 refreshing=(async()=>{try{await Promise.resolve();if(!uploadCsrf)await refreshUploads();if(activeView==='knowledge'){await refreshUploads();return true}data=await request('panel');csrf=data.csrf;connected=true;$('connectionNotice').hidden=true;$('connection').textContent='已连接 · '+dt(data.at);$('limits').textContent='费用上限：单篇含共享分析 ¥'+data.settings.article_budget_cny+'，每日共享 ¥'+data.settings.daily_budget_cny+'。';renderFilterOptions();renderArticleLibrary();renderKnowledgeLibrary();renderJobs();renderStudio();buttons();return true}catch(e){connected=false;$('connection').textContent='连接中断，正在重连；后台任务继续执行';buttons();$('connectionNotice').hidden=false;return false}})();
 try{return await refreshing}finally{refreshing=false}
}
function fillCatalog(){if(!catalogData)return;const c=catalogData[$('source').value]||catalogData;for(const[id,values]of[['date',c.dates||[]],['question',c.questions||[]]])$(id).innerHTML=values.length?values.map(v=>`<option value="${escape(v)}">${escape(v)}</option>`).join(''):'<option value="">暂无素材，请等待专用采集</option>';$('channels').innerHTML=(c.channels||[]).map(c=>`<label style="display:inline-flex;gap:6px;margin-right:12px"><input type="checkbox" name="channel" checked value="${escape(c.id)}">${escape(c.name)}</label>`).join('')}
function product(){const previous=new Map((productData.facts||[]).map(f=>[f.text,f])),facts=$('facts').value.split('\n').map(s=>s.trim()).filter(Boolean).map(text=>previous.get(text)||{text,approved:true,evidence:'用户在创作表单提供',independently_verified:false,approval_scope:'仅作为用户提供的草稿资料'});return{...productData,name:$('productName').value.trim(),brand:$('brand').value.trim(),audience:$('audience').value.trim(),facts}}
async function act(name,body){
 if(busy)return;if(!connected){message('暂时未连接，请等待连接恢复后再操作。',true);return}
 const labels={product_image_upload:['正在上传…','正在上传并保存产品图片…'],kb_upload:['正在上传…','正在保存原文件和上传记录，请稍候…'],kb_edit:['正在保存…','正在保存产品资料更新…'],kb_import:['正在分析文档…','正在上传并提取产品资料，请稍候…'],kb_save:['正在保存…','正在保存产品知识库，完成后进入问题配置…'],plan_save:['正在保存任务…','正在保存任务配置并确认执行安排…'],plan_delete:['正在删除…','正在停止后续执行并移除任务…'],day_pause:['正在暂停…','正在提交暂停请求，已发送的请求会安全收尾…'],day_resume:['正在检查…','正在检查任务状态并恢复执行…'],pause:['正在暂停…','正在提交暂停请求…'],resume:['正在检查…','正在检查并恢复创作…'],balance:['正在查询…','正在查询API余额…'],new:['正在建立…','正在准备素材并建立创作任务…']};
 const [label,note]=labels[name]||['正在处理…','正在提交操作…'];
 busy=true;operation={name,body:typeof body==='function'?null:body,label,note,start:Date.now()};buttons();message(note,false,'working');
 operationTimer=setInterval(()=>{if(operation)message(operation.note+' 已等待 '+Math.floor((Date.now()-operation.start)/1000)+' 秒，请勿重复提交。',false,'working')},1000);
 try{
  if(typeof body==='function'){operation.note=name==='product_image_upload'?'正在读取本地图片…':'正在读取本地Word文件…';message(operation.note,false,'working');body=await body();operation.body=body;operation.note=note;message(note,false,'working')}
  const result=await request('control/'+name,body);clearInterval(operationTimer);operation.finishing=true;buttons();
  if(name==='materials_settings')materialDirty=false;
  if(['product_image_upload','kb_upload','kb_edit','kb_import','kb_save','plan_save','plan_delete','day_pause','day_resume'].includes(name))studioResult(name,result.result);
  if(name==='balance')$('balanceText').textContent=result.result?.is_available?'API余额可用':'API余额不可用';
  const success=name==='kb_import'?'文档已解析，产品信息已填入下方。确认后点击“确认产品信息，下一步”。':name==='new'?'创作任务已建立，可在“执行进度”查看。':result.result?.message||'操作已完成';
  if(refreshing)await refreshing;const refreshed=await refresh();
  if(name==='kb_save'){$('planProduct').value=kbId;showStep(2)}
  message(success+(refreshed?'':' 最新列表暂未获取，连接恢复后会自动更新。'));
  return result;
 }catch(e){message(e.message||'操作失败，输入内容已保留，请重试。',true);return false}
 finally{clearInterval(operationTimer);busy=false;operation=null;buttons()}
}
$('new').onclick=()=>{if(!$('date').value||!$('question').value){message('请先选择已有素材的日期和问题',true);return}act('new',{material_source:$('source').value,date:$('date').value,question:$('question').value,channels:[...document.querySelectorAll('[name=channel]:checked')].map(c=>c.value),max_per_category:Number($('count').value),product:product()})};$('balance').onclick=()=>act('balance',{});$('retryAction').onclick=()=>{if(pendingAction)act(pendingAction.path.replace('control/',''),JSON.parse(pendingAction.payload))};

const studioStates={supplementing:'正在补充素材',waiting_previous_capture:'等待前一天采集处理',complete_with_failures:'已结束，部分文章未生成',insufficient_materials:'素材不足，已保留合格成稿',scheduled:'等待定时',capture_only:'已保留定时采集，自动创作未启用',capture_only_complete:'采集已完成，自动创作未启用',not_enabled:'尚未启用',collecting:'正在采集问题',waiting_for_geo:'等待主GEO让出账号',waiting_login:'需要登录或人工验证',waiting_writing:'素材已齐，等待创作槽位',waiting_capture_capacity:'等待空闲采集资源',capture_retrying:'采集失败，正在重试',creating:'正在分析和生成文章',complete:'已完成',paused:'已手动暂停',needs_attention:'需要处理'};
function loadKnowledge(id){kbId=id||'';importId='';kbDirty=false;const kb=(data.studio?.products||[]).find(p=>p.product_id===kbId),p=kb?.product||{};$('kbSelect').value=kbId;$('kbName').value=p.name||'';$('kbBrand').value=p.brand||'';$('kbAudience').value=p.audience||'';$('kbFacts').value=(p.facts||[]).map(f=>f.text).join('\n');$('kbSource').textContent=kb?.word_source?.filename?'已导入：'+kb.word_source.filename:kb?'已保留原项目产品资料，可更新或重新导入 Word':'选择 Word 文件，读取并确认后保存新产品'}
function loadPlan(id){planId=id||'';planDirty=false;const p=(data.studio?.plans||[]).find(p=>p.plan_id===planId)||{};$('planSelect').value=planId;$('planProduct').value=p.product_id||kbId||data.studio?.products[0]?.product_id||'';$('planStart').value=p.start_date||data.studio?.today||'';$('planCapture').value=p.capture_time||'01:00';$('planRounds').value=p.rounds||1;$('planCount').value=p.max_per_category||1;$('planEnabled').checked=!!p.enabled;$('planQuestions').value=(p.questions||data.materials?.settings.questions||[]).join('\n');$('planChannels').innerHTML=[['deepseek','DeepSeek'],['baidu_ai','百度卡片'],['wenxin_card','文心卡片']].map(([id,name])=>`<label style="display:inline-flex;margin-right:12px;gap:6px"><input type="checkbox" name="planChannel" value="${id}" ${(p.channels||['deepseek','baidu_ai','wenxin_card']).includes(id)?'checked':''} onchange="planDirty=true">${name}</label>`).join('');$('planHint').textContent=p.legacy_capture&&!p.enabled?'原01:00独立采集已保留。采集完成后会自动分析，请点击“保存并启用每日任务”接通自动分析与创作。':''}
function renderStudio(){const st=data.studio;if(!st)return;const selectedKB=kbId,selectedPlan=planId,selectedPlanProduct=$('planProduct').value;$('kbSelect').innerHTML='<option value="">新增产品知识库</option>'+st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');$('planProduct').innerHTML=st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');$('planSelect').innerHTML='<option value="">新增每日任务</option>'+st.plans.map(p=>`<option value="${p.plan_id}">${escape(p.product.name)} · ${p.capture_time}采集 · 完成后自动分析</option>`).join('');if(!studioLoaded){studioLoaded=true;loadKnowledge(st.products[0]?.product_id||'');loadPlan(st.plans[0]?.plan_id||'')}else{const kp=selectedKB;$('kbSelect').value=kp;if(!kbDirty)loadKnowledge(kp);const pp=selectedPlanProduct;$('planSelect').value=selectedPlan;if(!planDirty)loadPlan(selectedPlan);else if(pp)$('planProduct').value=pp}$('studioLimits').textContent='费用沿用原预算：单篇含共享分析 ¥'+data.settings.article_budget_cny+'，每日共享 ¥'+data.settings.daily_budget_cny+'。达到预算或遇到生成/API异常会保留进度并显示原因；成稿不会自动发布。';renderDailyTasks()}
function renderDailyTasks(){const st=data?.studio;if(!st)return;const date=$('dateFilter').value||st.today;$('dailyProduct').innerHTML=$('productFilter').innerHTML;$('dailyProduct').value=$('productFilter').value;$('dailyDate').innerHTML=[...$('dateFilter').options].filter(o=>o.value).map(o=>`<option value="${escape(o.value)}">${escape(o.text)}</option>`).join('');$('dailyDate').value=date;const rows=st.daily_tasks.filter(t=>t.date===date&&(!$('productFilter').value||t.product.id===$('productFilter').value));$('dailyDateHint').textContent='任务日期：'+date+'（北京时间）';const active=rows.filter(t=>['collecting','creating'].includes(t.status)).length,done=rows.filter(t=>t.status==='complete').length,attention=rows.filter(t=>['needs_attention','waiting_login'].includes(t.status)).length;$('dailyMetrics').innerHTML=[['当日任务',rows.length],['正在执行',active],['已完成 / 需处理',done+' / '+attention]].map(([k,v])=>`<div class="metric"><small>${k}</small><b>${v}</b></div>`).join('');$('dailyCards').innerHTML=rows.length?rows.map(t=>`<article class="job"><div class="row between"><h3>${escape(t.product.name)}</h3><span class="badge">${escape(studioStates[t.status]||t.status)}</span></div><small>${escape(t.date)} · ${t.questions}个问题 · ${t.capture_time}采集 · 完成后自动分析仿写</small><div class="material-progress">${t.progress.map(m=>`<div class="card"><small>${escape(m.name)}</small><b>${m.completed} / ${t.target_per_model}${m.failed?' · 缺失 '+m.failed:''}</b><small>${m.blocked.kind?'需要登录或验证':'问题采集进度'}</small></div>`).join('')}</div><p><b>分析创作 ${t.writing_complete} / ${t.questions} 项已完成 · ${t.articles} 篇成稿可下载</b></p>${t.error?`<p class="error">${escape(t.error)}</p>`:''}<div class="row">${!['complete','not_enabled','capture_only','capture_only_complete'].includes(t.status)?`<button data-day-action="${t.status==='paused'||t.status==='needs_attention'||t.status==='waiting_login'?'day_resume':'day_pause'}" data-plan="${t.plan_id}" data-date="${t.date}">${t.status==='paused'?'继续当日任务':t.status==='needs_attention'||t.status==='waiting_login'?'重新检查并继续':'暂停当日任务'}</button>`:''}<a class="button" href="#outputs" data-show-day="${t.date}" data-product="${t.product.id}">查看该产品当天成稿</a><a class="button" href="#dailyPlan" data-edit-plan="${t.plan_id}">修改任务配置</a></div></article>`).join(''):'<div class="empty">这一天没有每日任务。请先保存产品知识库，再配置并启用每日任务。</div>';document.querySelectorAll('[data-day-action]').forEach(b=>b.onclick=()=>act(b.dataset.dayAction,{plan_id:b.dataset.plan,date:b.dataset.date}));document.querySelectorAll('[data-show-day]').forEach(a=>a.onclick=()=>{$('dateFilter').value=a.dataset.showDay;$('productFilter').value=a.dataset.product;applyFilters()});document.querySelectorAll('[data-edit-plan]').forEach(a=>a.onclick=()=>loadPlan(a.dataset.editPlan))}
function syncDailyFilters(){$('productFilter').value=$('dailyProduct').value;$('dateFilter').value=$('dailyDate').value;applyFilters()}
function nextDailyTask(){const day=(data.studio?.daily_tasks||[]).map(t=>t.date).filter(d=>d>data.studio.today).sort()[0]||data.studio.today;$('dateFilter').value=day;applyFilters()}
function studioResult(name,r){if(name==='kb_import'){importId=r.import_id;kbDirty=true;$('kbFacts').value=r.text;$('kbSource').textContent='已读取 '+r.filename+'，共'+r.paragraphs+'段，请确认后保存产品知识库'}if(name==='kb_save'){kbId=r.product_id;kbDirty=false;importId=''}if(name==='plan_save'){planId=r.plan_id;planDirty=false}}
function planPayload(enable){return{...(planId?{plan_id:planId}:{}),product_id:$('planProduct').value,questions:$('planQuestions').value.split('\n').map(s=>s.trim()).filter(Boolean),channels:[...document.querySelectorAll('[name=planChannel]:checked')].map(c=>c.value),capture_time:$('planCapture').value,analysis_start:'after_capture',start_date:$('planStart').value,rounds:Number($('planRounds').value),max_per_category:Number($('planCount').value)||10,article_target:Number($('planTarget').value)||0,enabled:enable??$('planEnabled').checked}}

$('kbWord').onchange=()=>{const f=$('kbWord').files[0];$('kbSource').textContent=f?'已选择 '+f.name+'，点击“导入并分析产品信息”开始。':'请选择Word文件';buttons()};
$('kbImport').onclick=()=>{const file=$('kbWord').files[0];if(!file){message('请先选择Word文件',true);return}if(!file.name.toLowerCase().endsWith('.docx')||file.size>5*1024*1024){message('请选择5MB以内的.docx文件',true);return}act('kb_import',()=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({filename:file.name,content_base64:String(reader.result).split(',')[1]});reader.onerror=()=>reject(Error('文件读取失败，请重新选择Word文件。'));reader.onabort=()=>reject(Error('文件读取已取消，请重新选择文件。'));reader.readAsDataURL(file)}))};
$('kbSave').onclick=()=>confirmSelectedKnowledge();
$('planSave').onclick=()=>validateSchedule()&&act('plan_save',planPayload(planId?$('planEnabled').checked:false));$('planEnable').onclick=()=>validateSchedule()&&act('plan_save',planPayload(true));
(async()=>{await refresh();try{catalogData=await request('catalog');productData=catalogData.product||{};$('productName').value=productData.name||'';$('brand').value=productData.brand||'';$('audience').value=productData.audience||'';$('facts').value=(productData.facts||[]).map(f=>f.text||'').join('\n');$('productDetails').textContent=JSON.stringify(productData,null,2);fillCatalog()}catch(e){message(e.message,true)}})();setInterval(refresh,10000);new ResizeObserver(()=>parent.postMessage({type:'geo-creation:layout',height:document.body.scrollHeight+20},location.origin)).observe(document.body);

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
 const hint=$('wizardFeedback');hint.hidden=!kbDirty;hint.className='hint';
 hint.textContent=kbDirty?'产品资料待确认，保存任务前请先完成第一步。':'';
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
 for(const id of ['planName','planFrequency','planTaskType','planStart','planCapture','planRounds','planCount','planArticleBudget','planTaskBudget']){
  const el=$(id);if(id==='planCount'&&Number($('planTarget').value)>0)continue;
  if(!el.value.trim()||!el.checkValidity()){
   const labels={planName:'任务名称',planFrequency:'执行周期',planTaskType:'任务类型',planStart:'执行日期',planCapture:'开始采集时间',planRounds:'每题采集轮数',planCount:'每个问题、每类文章最多篇数',planArticleBudget:'单篇预算上限',planTaskBudget:'本任务每次执行预算上限'};
   const label=labels[id],budget=['planArticleBudget','planTaskBudget'].includes(id);
   let reason=el.validity.badInput?label+'格式不正确。':!el.value.trim()?'请填写'+label+'。':el.validity.rangeOverflow?label+'不能超过'+(budget?'共享限额 ':'')+el.max+(budget?' 元（当前填写 '+el.value+' 元）。':'。'):el.validity.rangeUnderflow?label+'不能低于 '+el.min+(budget?' 元。':'。'):el.validity.stepMismatch?label+(budget?'最多填写两位小数。':'请填写整数。'):label+'格式不正确，请检查后重试。';
   showStep(id==='planRounds'?2:3);message(reason,true);el.focus();return false;
  }
 }if($('planTarget').value&&!$('planTarget').checkValidity()){message('任务总篇数应为1至100篇',true);return false}return true;
}
function scheduleSummary(){
 $('planCount').disabled=Number($('planTarget').value)>0;
 if(['planFrequency','planTaskType','planStart','planCapture','planCount'].some(id=>!(id==='planCount'&&Number($('planTarget').value)>0)&&!$(id).value)){ $('schedulePreview').textContent='请选择任务周期、日期和时间，并填写篇数与预算后保存。';return}
 const n=$('planQuestions').value.split('\n').filter(s=>s.trim()).length,count=Number($('planCount').value)||1;
 $('schedulePreview').textContent=($('planFrequency').value==='once'?'仅执行一次：'+$('planStart').value:'每天常规执行，首次日期 '+$('planStart').value)+'，'+$('planCapture').value+' 开始采集；素材齐全后自动分析，分析完成后继续写作。'+($('planTaskType').value==='capture_only'?'本任务只采集素材。':Number($('planTarget').value)>0?'汇总'+n+'个问题的独立素材，本次目标'+Number($('planTarget').value)+'篇，按真实体裁分配。':n+'个问题，每类最多'+count+'篇，排行类与科普类合计最多'+n*count*2+'篇。')+' 共享账号忙时等待，任务不会抢占主GEO。';
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
 $('editorTitle').textContent=planId?'编辑创作任务':'新建创作任务';$('editorMode').textContent=planId?'正在编辑：'+(p.name||p.product?.name||'已有任务')+'。修改后点击保存修改。':'';$('planSave').textContent=planId?'保存修改':'保存为草稿';
 $('planName').value=p.name||(planId?p.product.name+'创作任务':'');$('planFrequency').value=p.frequency||(planId?'daily':'');$('planTaskType').value=p.task_type||(planId?'collect_write':'');
 $('planStart').value=p.start_date||'';$('planCapture').value=p.capture_time||'';$('planRounds').value=p.rounds??'';$('planCount').value=p.max_per_category??'';$('planTarget').value=p.article_target||'';$('planEnabled').checked=!!p.enabled;
 $('planArticleBudget').value=planId?(p.article_budget_cny??data.settings.article_budget_cny):'';$('planTaskBudget').value=planId?(p.task_budget_cny??data.settings.daily_budget_cny):'';
 $('planArticleBudget').max=data.settings.article_budget_cny;$('planTaskBudget').max=data.settings.daily_budget_cny;
 $('planQuestions').value=(p.questions||[]).join('\n');
 $('planChannels').innerHTML=[['deepseek','DeepSeek'],['baidu_ai','百度卡片'],['wenxin_card','文心卡片']].map(([id,name])=>`<label class="channel-option"><input type="checkbox" name="planChannel" value="${id}" ${(p.channels||[]).includes(id)?'checked':''} onchange="planDirty=true">${name}</label>`).join('');
 $('planHint').textContent=p.legacy_capture&&!p.enabled?'这是原独立素材采集配置，自动付费创作尚未启用。':'';scheduleSummary();
}
function studioResult(name,r){
 if(name==='product_image_upload')renderSavedImages();

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
function planPayload(enable){return{...(planId?{plan_id:planId}:{}),name:$('planName').value,frequency:$('planFrequency').value,task_type:$('planTaskType').value,article_budget_cny:Number($('planArticleBudget').value),task_budget_cny:Number($('planTaskBudget').value),product_id:$('planProduct').value,questions:$('planQuestions').value.split('\n').map(s=>s.trim()).filter(Boolean),channels:[...document.querySelectorAll('[name=planChannel]:checked')].map(c=>c.value),capture_time:$('planCapture').value,analysis_start:'after_capture',start_date:$('planStart').value,rounds:Number($('planRounds').value),max_per_category:Number($('planCount').value)||10,article_target:Number($('planTarget').value)||0,enabled:enable??false}}
function renderStudio(){
 const st=data.studio;if(!st)return;const selectedKB=kbId,selectedPlan=planId,selectedProduct=$('planProduct').value;
 $('kbSelect').innerHTML='<option value="">请选择已建好的产品</option>'+st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');
 $('planProduct').innerHTML='<option value="">请选择产品知识库</option>'+st.products.map(k=>`<option value="${k.product_id}">${escape(k.product.name)}</option>`).join('');
 $('planSelect').innerHTML='<option value="">新建任务</option>'+st.plans.map(p=>`<option value="${p.plan_id}">${escape(p.name||p.product.name)} · ${p.frequency==='once'?'仅一次':'每日'}</option>`).join('');
 if(!studioLoaded){studioLoaded=true;loadKnowledge('');loadPlan('')}
 else{$('kbSelect').value=selectedKB;$('planSelect').value=selectedPlan;$('planProduct').value=selectedProduct}
 $('studioLimits').textContent='共享限额：单篇含分析 ¥'+data.settings.article_budget_cny+'，每日所有任务合计 ¥'+data.settings.daily_budget_cny+'。你设置的任务预算会额外限制本次执行，不会自动提高共享限额。';
 renderDailyTasks();renderKnowledgeLibrary();renderSelectedKnowledge();
}
function taskListItem(p,st){
 const days=st.daily_tasks.filter(t=>t.plan_id===p.plan_id);
 const t=(p.frequency==='once'?days.find(t=>t.date===p.start_date):days.find(t=>t.date===st.today))||days.slice().sort((a,b)=>b.date.localeCompare(a.date))[0];
 const state=t?.status||(p.enabled?'scheduled':'not_enabled');
 const capture='';
 const creation=(t?.task_type||p.task_type)==='capture_only'?'<small class="queue-note">仅采集素材，不执行文章创作</small>':`<div class="queue-article-count"><span>已生成文章</span> <b>${Math.max(0,Number(t?.articles)||0)} 篇</b></div>`;
 const finished=isTerminal(state),resume=dayActions(t).includes('day_resume');
 const canControl=dayActions(t).length>0;
 const control=canControl?`<button data-day-action="${resume?'day_resume':'day_pause'}" data-plan="${p.plan_id}" data-date="${t.date}">${resume?(state==='paused'?'继续':'检查并继续'):'暂停'}</button>`:`<button disabled data-control-unavailable>${finished?(state==='complete'||state==='capture_only_complete'?'已完成':'已结束'):p.enabled?'等待执行':'未启用'}</button>`;
 const status=studioStates[state]||({'scheduled':'等待定时','not_enabled':'草稿，未启用','capture_only':'仅采集素材'}[state])||state;
 return `<article class="queue-item"><div class="task-description"><b>${escape(p.name||p.product.name+'创作任务')}</b><small>${p.frequency==='once'?'临时 · '+escape(p.start_date)+' '+escape(p.capture_time)+'，仅执行一次':'每天 '+escape(p.capture_time)+' 开始采集 · 首次 '+escape(p.start_date)}（北京时间）</small><small>${p.task_type==='capture_only'?'仅采集素材':'采集完成后自动分析、写作'} · ${p.questions.length}题 · ${p.article_target?'每次目标'+p.article_target+'篇':'每题每类最多'+p.max_per_category+'篇'} · 本次预算 ¥${p.task_budget_cny??data.settings.daily_budget_cny}</small><div class="queue-progress-group"><small class="queue-note">执行日期：${escape(t?.date||p.start_date)}${state==='paused'?' · 已暂停，已完成进度保留':finished&&p.frequency==='daily'&&p.enabled?' · 本次已结束，后续仍按每日计划执行':''}</small>${capture}${creation}${t?.error?`<small class="queue-note">${escape(t.error)}</small>`:''}</div></div><div class="queue-controls"><span class="badge">${escape(status)}</span><div class="row">${control}<button data-edit-plan="${p.plan_id}">查看与编辑</button><button class="danger" data-delete-plan="${p.plan_id}" aria-expanded="${deleteTarget===p.plan_id}">删除任务</button></div>${deleteTarget===p.plan_id?`<div id="deleteDialog" role="group" aria-labelledby="deleteTitle"><h3 id="deleteTitle">确定删除这个任务？</h3><div class="row"><button id="deleteCancel">取消</button><button id="deleteConfirm" class="danger primary">确认删除</button></div><p id="deleteFeedback" class="action-feedback" role="status" aria-live="polite" hidden></p></div>`:''}</div></article>`;
}
function renderDailyTasks(){
 const st=data?.studio;if(!st)return;const date=$('dateFilter').value||st.today;
 $('dailyProduct').innerHTML=$('productFilter').innerHTML;$('dailyProduct').value=$('productFilter').value;$('dailyDate').innerHTML=[...$('dateFilter').options].filter(o=>o.value).map(o=>`<option value="${escape(o.value)}">${escape(o.text)}</option>`).join('');$('dailyDate').value=date;
 const tasks=st.daily_tasks.filter(t=>t.date===date&&(!$('productFilter').value||t.product.id===$('productFilter').value));
 $('dailyDateHint').textContent='进度日期：'+date+'（北京时间）';
 $('dailyMetrics').innerHTML=[['当天任务',tasks.length],['正在执行',tasks.filter(t=>['collecting','creating'].includes(t.status)).length],['已完成 / 需处理',tasks.filter(t=>t.status==='complete').length+' / '+tasks.filter(t=>['needs_attention','waiting_login'].includes(t.status)).length]].map(([k,v])=>`<div class="metric"><small>${k}</small><b>${v}</b></div>`).join('');
 const term=($('taskSearch')?.value||'').trim().toLowerCase(),state=$('taskState')?.value||'';
 const visiblePlans=st.plans.filter(p=>(!term||(p.name||p.product.name).toLowerCase().includes(term)||p.product.name.toLowerCase().includes(term))&&(!state||String(!!p.enabled)===state));
 $('taskTotals').innerHTML=[['已保存任务',st.plans.length],['已启用',st.plans.filter(p=>p.enabled).length],['今日执行中',st.daily_tasks.filter(t=>t.date===st.today&&['collecting','creating'].includes(t.status)).length]].map(([k,v])=>`<div><span>${k}</span><strong>${v}</strong></div>`).join('');
 $('planQueue').innerHTML=visiblePlans.length?visiblePlans.map(p=>taskListItem(p,st)).join(''):'<div class="empty">'+(st.plans.length?'没有符合筛选条件的任务。':'还没有任务，点击右上角“新建任务”开始。')+'</div>';
 $('dailyCards').innerHTML=tasks.length?tasks.map(t=>`<article class="job"><div class="row between"><h3>${escape(t.name||t.product.name)}</h3><span class="badge">${escape(studioStates[t.status]||t.status)}</span></div><small>${escape(t.date)} · ${escape(t.product.name)} · ${t.frequency==='once'?'临时一次':'每天常规'} · ${t.capture_time} 采集 · 完成后自动分析</small><div class="material-progress">${t.progress.map(m=>`<div class="card"><small>${escape(m.name)}</small><b>${m.completed} / ${t.target_per_model}${m.failed?' · 缺失 '+m.failed:''}</b><small>${m.blocked?.kind?'需要登录或验证':m.recovery?.status==='cooling_down'?(m.recovery.kind==='verification'?'平台安全验证，冷却等待':'读取未完成，退避等待'):'问题采集进度'}</small></div>`).join('')}</div><p><b>${t.writing_complete}/${t.questions}个问题已完成创作 · ${t.articles}篇成稿</b></p>${t.error?`<p class="error">${escape(t.error)}</p>`:''}<div class="row">${dayActions(t).length>0?`<button data-day-action="${['paused','needs_attention','waiting_login'].includes(t.status)?'day_resume':'day_pause'}" data-plan="${t.plan_id}" data-date="${t.date}">${['paused','needs_attention','waiting_login'].includes(t.status)?'检查并继续':'暂停任务'}</button>`:''}<a class="button" href="${link('all-approved','','bundle')+'&'+new URLSearchParams({plan:t.plan_id,date:t.date})}">下载本任务成稿与日志</a><button data-edit-plan="${t.plan_id}">查看任务配置</button></div></article>`).join(''):'<div class="empty">所选日期暂无执行记录，请在上方队列查看计划执行时间。</div>';
 document.querySelectorAll('[data-day-action]').forEach(b=>b.onclick=()=>act(b.dataset.dayAction,{plan_id:b.dataset.plan,date:b.dataset.date}));
 document.querySelectorAll('[data-edit-plan]').forEach(b=>b.onclick=()=>{editCreationPlan(b.dataset.editPlan)});
 document.querySelectorAll('[data-delete-plan]').forEach(b=>b.onclick=()=>askDelete(b.dataset.deletePlan));bindDeleteControls();buttons();
}
function renderArticleLibrary(){
 const raw=library(),held=raw.filter(a=>a.quality_status==='needs_revision'),all=raw.filter(a=>a.quality_status!=='needs_revision'),term=$('search').value.trim().toLowerCase(),filter=$('outputFilter').value;
 const rows=all.filter(a=>matchesTask(a)&&(!term||a.title.toLowerCase().includes(term))&&(filter==='all'||(filter==='new'?a.job!=='legacy-original':a.job==='legacy-original')));
 $('library').innerHTML=rows.length?rows.map(a=>`<article class="output"><div><h3>${escape(a.title)}</h3><small>${escape(a.date)} · ${escape(a.task_name||a.product.name)} · ${escape(a.category||a.id.split('/')[1])} · ${a.receipt?.delivery_mode==='direct'?'直接输出':a.quality_status==='ready_with_disputes'?'待核对意见已保留，可供审阅':'已通过审稿'}</small>${a.quality_status==='ready_with_disputes'?'':''}<p class="source-line">参考原文：${a.primary_reference?.url?`<a href="${escape(a.primary_reference.url)}" target="_blank" rel="noopener noreferrer">${escape(a.primary_reference.title||a.primary_reference.domain)}</a>`:'历史记录未标注'}<small>${escape(a.primary_reference?.media||'')} · ${escape(a.primary_reference?.domain||'')}</small></p></div><div class="row"><button class="article-view" data-kind="markdown" data-job="${a.job}" data-id="${escape(a.id)}">预览文章</button><button class="article-view" data-kind="info" data-job="${a.job}" data-id="${escape(a.id)}">来源与执行日志</button><a class="button primary" href="${link(a.job,a.id,'package')}">下载文章及溯源</a><a class="button" href="${link(a.job,a.id,'word')}">Word</a></div></article>`).join(''):'<div class="empty">当前筛选暂无成稿。执行完成后会出现在这里。</div>';
 $('totalArticles').textContent=rows.length;$('newArticles').textContent=rows.filter(a=>a.job!=='legacy-original').length;$('legacyCount').textContent=rows.filter(a=>a.job==='legacy-original').length;$('filterSummary').textContent='当前筛选 '+rows.length+' 篇 / 可下载 '+all.length+' 篇，下载包含文章、原文出处与执行日志。'+(held.length?' 另有 '+held.length+' 篇旧稿未通过正文质量复核，已停止下载；原稿和日志保留，修订通过后恢复。':'');
 const dl=$('downloadAll');dl.textContent='打包下载筛选结果（'+rows.length+'篇）';dl.href=link('all-approved','','bundle')+'&'+new URLSearchParams({date:$('dateFilter').value,product:$('productFilter').value,source:filter,search:$('search').value.trim()});if(!rows.length)dl.removeAttribute('href');
 document.querySelectorAll('.article-view').forEach(b=>b.onclick=async()=>{try{$('previewText').textContent='正在读取…';$('preview').showModal();const r=await fetch(link(b.dataset.job,b.dataset.id,b.dataset.kind));if(!r.ok)throw Error('读取失败，请刷新后重试');renderArticlePreview(await r.text(),b.dataset.kind)}catch(e){$('previewText').textContent=e.message}});
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
  status.textContent='下载已开始';
 }catch(e){status.textContent=e.message||'下载失败，请稍后重试'}
 finally{delete anchor.dataset.downloading;anchor.removeAttribute('aria-busy')}
}
document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||!u.pathname.endsWith('/download')||!['bundle','package','word'].includes(u.searchParams.get('kind')))return;e.preventDefault();downloadArticleFile(a)});

// Optional per-task detail and genre targets; loading old tasks preserves their contracts.
const detailControls=document.createElement('details');detailControls.className='hint';
detailControls.innerHTML='<summary>产品介绍与分类篇数（可选）</summary><div class="grid"><label>排行类目标篇数<input id="planRankingTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label><label>测评类目标篇数<input id="planReviewTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label><label>科普类目标篇数<input id="planScienceTarget" type="number" min="0" max="100" placeholder="留空按素材分配"></label></div><label><input id="planRichProduct" type="checkbox"> 增加自有产品信息量</label><div class="grid"><label>排行产品介绍目标汉字<input id="planRankingDetail" type="number" min="200" max="2000" placeholder="例如1000"></label><label>科普产品举例目标汉字<input id="planScienceDetail" type="number" min="200" max="2000" placeholder="例如600"></label></div>';
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

// Independent product library. Uploads remain pending until explicitly reviewed.
let libraryEditId='',libraryEditVersion='',libraryNextTarget='';
function libraryDate(v){return v?dt(v):'未记录'}
function libraryRows(){
 const st=data?.studio||{},records=st.knowledge_library||[],products=st.products||[];
 return [...products.map(k=>({kb:k,record:records.find(r=>r.product_id===k.product_id)})),...records.filter(r=>!r.product_id).map(r=>({record:r}))];
}
function renderKnowledgeLibrary(){
 const target=$('libraryTarget'),selected=target.value,rows=libraryRows();
 target.innerHTML='<option value="">新增产品</option>'+rows.map(({kb,record:r})=>`<option value="${kb?'product:'+kb.product_id:'library:'+r.library_id}">${escape(kb?.product.name||r.name)}${kb?'':'（待分析）'}</option>`).join('');target.value=selected;if(libraryNextTarget){const r=data.studio.knowledge_library.find(r=>r.library_id===libraryNextTarget);target.value=r?.product_id?'product:'+r.product_id:'library:'+libraryNextTarget;libraryNextTarget=''}
 syncImageProductOptions(rows);
 const query=$('librarySearch').value.trim().toLowerCase(),filter=$('libraryState').value;
 const visible=rows.filter(({kb,record:r})=>{const pending=r?.uploads.at(-1)?.status==='pending';return (!filter||(filter==='pending'?pending:!!kb))&&[kb?.product.name,kb?.product.brand,r?.name,...(r?.uploads||[]).map(u=>u.filename)].join(' ').toLowerCase().includes(query)});
 $('libraryTotals').textContent=`可用于创作 ${rows.filter(r=>r.kb).length} 个产品 · 待人工分析 ${rows.filter(r=>r.record?.uploads.at(-1)?.status==='pending').length} 个产品`;
 const open=new Set([...$('knowledgeRows').querySelectorAll('details[open]')].map(e=>e.dataset.history));
 $('knowledgeRows').innerHTML=visible.map(({kb,record:r})=>{
  const latest=r?.uploads.at(-1),pending=latest?.status==='pending',name=kb?.product.name||r.name,key=kb?.product_id||r.library_id;
  const history=r?.uploads|| (kb?.word_source?.filename?[{...kb.word_source,uploaded_at:kb.word_source.at,revision:1,status:'published',product_version:kb.version}]:[]);
  return `<article class="card"><div class="row between"><h3>${escape(name)}</h3><span class="badge">${pending?(kb?'新版待分析 · 当前版可用':'待人工分析'):'可用于创作'}</span></div><small>${kb?`品牌：${escape(kb.product.brand||'未填写')} · ${kb.product.facts.length} 条资料 · 最近保存：${libraryDate(kb.updated_at)}`:'上传已保存，分析完成后可创建任务。'}</small>${latest?`<small>最近上传：${libraryDate(latest.uploaded_at)} · ${escape(latest.filename)} · ${(latest.bytes/1024).toFixed(1)} KB</small>`:''}<div class="row" style="margin-top:12px">${kb?`<button data-library-use="${kb.product_id}">用此产品创建任务</button><button data-library-edit="${kb.product_id}">查看与编辑资料</button>`:''}<button data-image-target="${kb?'product:'+kb.product_id:'library:'+r.library_id}">上传图片</button><button data-library-update="${kb?'product:'+kb.product_id:'library:'+r.library_id}">上传更新</button></div>${productImageGallery(kb?.product_id,r?.library_id)}<details data-history="${key}" ${open.has(key)?'open':''}><summary>上传与版本记录（${history.length}）</summary>${history.length?history.slice().reverse().map(u=>`<div class="hint"><b>上传版本 ${u.revision} · ${u.status==='published'?'已分析入库':'待人工分析'}</b><small>文件：${escape(u.filename)} · ${u.bytes?((u.bytes/1024).toFixed(1)+' KB'):'大小未记录'}</small><small>上传时间：${libraryDate(u.uploaded_at)}（北京时间）</small>${u.analyzed_at?`<small>分析时间：${libraryDate(u.analyzed_at)} · 分析人：${escape(u.reviewer)}</small>`:''}${u.notes?`<p>更新备注：${escape(u.notes)}</p>`:''}<small style="overflow-wrap:anywhere">文件校验：${escape(u.sha256||'未记录')}</small>${u.product_version?`<small>知识库版本：${escape(u.product_version.slice(0,12))}</small>`:''}</div>`).join(''):''}</details></article>`;
 }).join('')||'<div class="empty">没有匹配的产品。可以先上传产品 Word 知识库。</div>';
 document.querySelectorAll('[data-library-use]').forEach(b=>b.onclick=()=>{newCreationTask();selectKnowledge(b.dataset.libraryUse);confirmSelectedKnowledge()});
 document.querySelectorAll('[data-image-target]').forEach(b=>b.onclick=()=>{$('productImageTarget').value=b.dataset.imageTarget;buttons();$('productImageBox').scrollIntoView({block:'start'});$('productImageFile').focus({preventScroll:true})});
 document.querySelectorAll('[data-library-edit]').forEach(b=>b.onclick=()=>editLibrary(b.dataset.libraryEdit));
 document.querySelectorAll('[data-library-update]').forEach(b=>b.onclick=()=>{target.value=b.dataset.libraryUpdate;$('libraryUploadBox').scrollIntoView({block:'start'});$('libraryWord').focus({preventScroll:true})});
}
function renderSelectedKnowledge(){
 const k=data?.studio?.products.find(p=>p.product_id===kbId);
 $('selectedKnowledge').textContent=k?`${k.product.name} · ${k.product.brand||'品牌未填写'} · ${k.product.facts.length} 条产品资料 · 更新于 ${libraryDate(k.updated_at)}。创建任务后将保留此版本。`:'请选择已经建好的产品知识库；待分析的产品会在分析完成后出现在这里。';
}
function confirmSelectedKnowledge(){
 if(!kbId||!data.studio.products.some(p=>p.product_id===kbId)){message('请先选择已建好的产品知识库。',true);return}
 confirmedKnowledge=knowledgeSignature();$('planProduct').value=kbId;showStep(2);
}
function editLibrary(id){
 const kb=data.studio.products.find(k=>k.product_id===id);if(!kb)return;
 libraryEditId=id;libraryEditVersion=kb.version;
 $('libraryEditName').value=kb.product.name;$('libraryEditBrand').value=kb.product.brand||'';$('libraryEditAudience').value=kb.product.audience||'';$('libraryEditFacts').value=kb.product.facts.map(f=>f.text).join('\n');
 $('libraryEditor').hidden=false;$('libraryEditor').scrollIntoView({block:'start'});
}
$('libraryWord').onchange=buttons;
$('libraryUpload').onclick=()=>{
 const file=$('libraryWord').files[0];if(!file)return;
 if(!file.name.toLowerCase().endsWith('.docx')||file.size>5*1024*1024){message('请选择 5MB 以内的 .docx 文件。',true);return}
 const [kind,id]=$('libraryTarget').value.split(':'),meta={name:$('libraryName').value,notes:$('libraryNotes').value,...(id?{[kind==='product'?'product_id':'library_id']:id}:{})};
 act('kb_upload',()=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({...meta,filename:file.name,content_base64:String(reader.result).split(',')[1]});reader.onerror=()=>reject(Error('文件读取失败，请重新选择。'));reader.readAsDataURL(file)}));
};
$('libraryEditSave').onclick=()=>act('kb_edit',{product_id:libraryEditId,expected_version:libraryEditVersion,name:$('libraryEditName').value,brand:$('libraryEditBrand').value,audience:$('libraryEditAudience').value,facts:$('libraryEditFacts').value.split('\n').map(s=>s.trim()).filter(Boolean)});

// Uploads have their own lightweight session and per-file durable operation IDs.
let imageBatchQueue=[],imageBatchActive=false,imageBatchTarget='',uploadRefreshPromise=null,uploadCsrf='',knowledgeUploading=false;
const uploadBusyStates=new Set(['reading','uploading','saving','retrying']);
const uploadLabels={waiting:'等待上传',reading:'读取图片',uploading:'上传中',saving:'服务器保存中',retrying:'连接中断，自动核对',done:'上传成功',failed:'上传失败',uncertain:'结果待核对',skipped:'已跳过'};
const uploadID=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');
const uploadSleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let uploadDBPromise;
function uploadDB(){return uploadDBPromise ||= new Promise((resolve,reject)=>{const r=indexedDB.open('geo-product-uploads',1);r.onupgradeneeded=()=>r.result.createObjectStore('queue',{keyPath:'id'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
async function saveUpload(item,remove=false){
 try{const db=await uploadDB();await new Promise((resolve,reject)=>{const tx=db.transaction('queue','readwrite');const store=tx.objectStore('queue');if(remove)store.delete(item.id);else{const {preview,xhr,...saved}=item;store.put(saved)}tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)})}
 catch{if(!remove)imageUploadFeedback('浏览器暂时无法保存待传队列，请保留此页面直到上传结束。',true)}
}
async function restoreUploads(){
 try{const db=await uploadDB();const rows=await new Promise((resolve,reject)=>{const r=db.transaction('queue').objectStore('queue').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
  for(const row of rows){if(imageBatchQueue.some(i=>i.id===row.id))continue;row.status=uploadBusyStates.has(row.status)?'uncertain':row.status;row.preview=row.file?URL.createObjectURL(row.file):'';imageBatchQueue.push(row)}
  if(rows.length){imageUploadFeedback('已恢复 '+rows.length+' 张待处理图片。点击“上传 / 重试”继续，已保存的图片不会重复创建。');renderImageBatch();buttons()}
 }catch{}
}
async function refreshUploads(){
 if(uploadRefreshPromise)return uploadRefreshPromise;
 uploadRefreshPromise=(async()=>{
  const response=await fetch(API+'uploads',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(90000)});
  if(!response.ok)throw Error(response.status===401||response.status===403?'登录已失效，请重新登录后继续。':'图片服务暂时无法连接，请点击重试。');
  const result=await response.json();if(!result.csrf||!result.studio)throw Error('图片服务响应异常');
  uploadCsrf=result.csrf;csrf=result.csrf;
  if(!data)data={jobs:[],legacy_articles:[],settings:{},studio:{}};
  data.studio={...data.studio,...result.studio};renderKnowledgeLibrary();renderSavedImages();syncUploadControls();return result;
 })();
 try{return await uploadRefreshPromise}finally{uploadRefreshPromise=null;syncUploadControls()}
}
function imageMatches(image,target){
 const [kind,id]=(target||'').split(':');
 if(kind==='library')return image.library_id===id;
 return image.product_id===id||(data?.studio?.knowledge_library||[]).some(r=>r.product_id===id&&r.library_id===image.library_id);
}
function imageCard(image){
 const url=API+'product_image?id='+encodeURIComponent(image.image_id);
 return `<figure class="upload-image-card saved"><a href="${url}" target="_blank" rel="noopener"><img loading="lazy" src="${url}&thumbnail=1" alt="${escape(image.filename)}"></a><figcaption><strong title="${escape(image.filename)}">${escape(image.filename)}</strong><small>${image.width} × ${image.height} · ${(image.bytes/1024).toFixed(1)} KB</small><span class="upload-state done">已保存</span></figcaption></figure>`;
}
function productImageGallery(pid,lid){
 const rows=(data?.studio?.product_images||[]).filter(i=>(pid&&imageMatches(i,'product:'+pid))||(lid&&i.library_id===lid));
 return rows.length?`<details class="saved-image-details"><summary>查看已保存图片（${rows.length} 张）</summary><div class="upload-image-grid">${rows.map(imageCard).join('')}</div></details>`:'';
}
function renderSavedImages(){
 const box=$('savedProductImages');if(!box)return;
 const target=$('productImageTarget').value,rows=(data?.studio?.product_images||[]).filter(i=>imageMatches(i,target));
 $('savedImageCount').textContent=target?'此产品已保存 '+rows.length+' 张图片':'选择产品后查看已保存图片';
 box.innerHTML=rows.length?rows.map(imageCard).join(''):`<p class="muted">${target?'此产品还没有图片，选择图片后点击上传。':'请先选择图片关联产品。'}</p>`;
}
function imageUploadFeedback(text,error=false){const box=$('productImageFeedback');box.textContent=text;box.dataset.state=error?'error':'success';box.hidden=false}
function selectImageBatch(files,source){
 const target=$('productImageTarget').value;
 if(!target){imageUploadFeedback('请先选择图片关联产品，再选择图片或文件夹。',true);$('productImageTarget').focus();return false}
 let added=0;
 for(const file of Array.from(files)){
  const path=file.webkitRelativePath||file.name;
  if(imageBatchQueue.some(i=>i.target===target&&i.path===path&&i.file?.size===file.size&&i.file?.lastModified===file.lastModified&&i.status!=='skipped'))continue;
  const supported=/\.(jpe?g|png|webp)$/i.test(file.name)||['image/jpeg','image/png','image/webp'].includes(file.type);
  const reason=!supported?(/\.zip$/i.test(file.name)?'请解压ZIP后选择文件夹':'仅支持 JPG、PNG、WebP'):file.size>5*1024*1024?'超过5MB':!file.size?'文件为空':'';
  const item={id:uploadID(),file,path,target,targetName:$('productImageTarget').selectedOptions[0]?.textContent||'',status:reason?'skipped':'waiting',reason,progress:0,preview:supported?URL.createObjectURL(file):''};
  imageBatchQueue.push(item);if(!reason)saveUpload(item);added++;
 }
 $('imageBatchSelection').textContent=source+'：新增 '+added+' 个文件；下方可逐张预览和查看结果。';
 renderImageBatch();syncUploadControls();return true;
}
function renderImageBatch(){
 const box=$('imageBatchProgress');box.hidden=!imageBatchQueue.length;
 const count=state=>imageBatchQueue.filter(i=>i.status===state).length;
 $('imageBatchSummary').textContent=`本次 ${imageBatchQueue.length} 张 · 成功 ${count('done')} · 处理中 ${imageBatchQueue.filter(i=>uploadBusyStates.has(i.status)).length} · 待传 ${count('waiting')} · 失败/待核对 ${count('failed')+count('uncertain')} · 跳过 ${count('skipped')}`;
 const grid=$('imageQueueGrid');
 for(const item of imageBatchQueue){
  let card=document.getElementById('upload-'+item.id);
  if(!card){card=document.createElement('figure');card.id='upload-'+item.id;card.className='upload-image-card';
   card.innerHTML=`${item.preview?`<a target="_blank" rel="noopener"><img alt=""></a>`:'<div class="upload-no-preview">无预览</div>'}<figcaption><strong></strong><small class="upload-target"></small><progress max="100" value="0"></progress><span class="upload-state"></span><small class="upload-reason"></small><div class="row"><button type="button" class="upload-retry">重试此图</button><button type="button" class="upload-remove">移出队列</button></div></figcaption>`;
   if(item.preview){card.querySelector('img').src=item.preview;card.querySelector('img').alt=item.path;card.querySelector('a').href=item.preview}
   card.querySelector('strong').textContent=item.path;card.querySelector('strong').title=item.path;
   card.querySelector('.upload-target').textContent=item.targetName+' · '+(item.file.size/1024).toFixed(1)+' KB';grid.append(card);
   card.querySelector('.upload-retry').onclick=()=>uploadImageBatch(item.id);
   card.querySelector('.upload-remove').onclick=()=>{if(uploadBusyStates.has(item.status))return;saveUpload(item,true);if(item.preview)URL.revokeObjectURL(item.preview);imageBatchQueue=imageBatchQueue.filter(i=>i.id!==item.id);card.remove();renderImageBatch()};
  }
  card.dataset.state=item.status;const progress=card.querySelector('progress');progress.value=item.status==='done'?100:item.progress||0;
  progress.hidden=['failed','skipped','uncertain'].includes(item.status);
  const label=card.querySelector('.upload-state');label.className='upload-state '+item.status;label.textContent=(item.reused?'已存在，复用原图':uploadLabels[item.status])+(item.status==='uploading'?' '+(item.progress||0)+'%':'');
  card.querySelector('.upload-reason').textContent=item.reason||'';
  const retry=card.querySelector('.upload-retry');retry.hidden=!['failed','uncertain'].includes(item.status);retry.disabled=imageBatchActive;
  card.querySelector('.upload-remove').disabled=uploadBusyStates.has(item.status);
 }
 syncUploadControls();
}
function readBatchImage(item){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=()=>reject(Error('文件读取失败，请重新选择'));r.onabort=()=>reject(Error('文件读取已取消'));r.readAsDataURL(item.file)})}
function uploadRequest(action,payload,key,onProgress){
 return new Promise((resolve,reject)=>{
  const xhr=new XMLHttpRequest();xhr.open('POST',API+'control/'+action);xhr.timeout=600000;
  xhr.setRequestHeader('Content-Type','application/json');xhr.setRequestHeader('X-CSRF-Token',uploadCsrf);xhr.setRequestHeader('X-Action-Id',key);
  xhr.upload.onprogress=e=>{if(e.lengthComputable)onProgress?.(Math.round(e.loaded/e.total*100))};
  const fail=(message,status=0)=>reject(Object.assign(Error(message),{status}));
  xhr.onerror=()=>fail('网络中断，保留原编号核对后重试');xhr.ontimeout=()=>fail('等待保存结果超时，保留原编号核对后重试');
  xhr.onload=()=>{let response;try{response=JSON.parse(xhr.responseText)}catch{}
   if(xhr.status>=200&&xhr.status<300&&response?.ok){resolve(response);return}
   fail(xhr.status===413?'上传入口拒绝文件大小，请联系管理员检查上传限制':xhr.status===401||xhr.status===403?'登录或上传会话已过期':response?.message||'服务器未返回明确结果（HTTP '+xhr.status+'）',xhr.status);
  };xhr.send(JSON.stringify(payload));
 });
}
function addUploadedImage(result){
 if(!result.image)return;
 const rows=data.studio.product_images||[];data.studio.product_images=[result.image,...rows.filter(i=>i.image_id!==result.image.image_id)];renderSavedImages();
}
async function uploadOne(item){
 item.status='reading';item.reason='';renderImageBatch();await saveUpload(item);
 try{
  const [kind,id]=item.target.split(':'),payload={[kind==='product'?'product_id':'library_id']:id,filename:item.file.name,content_base64:await readBatchImage(item)};
  for(let attempt=0;attempt<3;attempt++){
   try{
    if(!uploadCsrf)await refreshUploads();item.status='uploading';item.progress=0;renderImageBatch();
    const r=await uploadRequest('product_image_upload',payload,item.id,n=>{item.progress=n;item.status=n===100?'saving':'uploading';renderImageBatch()});
    item.status='done';item.progress=100;item.reused=!!r.result.reused;item.reason=r.result.message;addUploadedImage(r.result);await saveUpload(item,true);return;
   }catch(error){
    if(error.status===401||error.status===403){uploadCsrf='';try{await refreshUploads()}catch{} }
    const retryable=!error.status||error.status>=500||[401,403,408,429].includes(error.status);
    if(!retryable||attempt===2){item.status=retryable?'uncertain':'failed';item.reason=error.message+(retryable?'；可点击重试此图，其他图片继续处理。':'');await saveUpload(item);return}
    item.status='retrying';item.reason='第 '+(attempt+1)+' 次核对重试，使用原操作编号';renderImageBatch();await uploadSleep(800*(attempt+1));
   }
  }
 }catch(e){item.status='failed';item.reason=e.message;await saveUpload(item)}
 finally{renderImageBatch()}
}
async function uploadImageBatch(onlyId){
 if(imageBatchActive)return;
 const queue=imageBatchQueue.filter(i=>['waiting','failed','uncertain'].includes(i.status)&&(!onlyId||i.id===onlyId));
 if(!queue.length){imageUploadFeedback('请先选择图片或文件夹。',true);return}
 imageBatchActive=true;renderImageBatch();imageUploadFeedback('正在上传，可在每张图片下查看进度；完成后立即显示在已保存图片中。');
 try{await refreshUploads();let index=0;await Promise.all(Array.from({length:Math.min(3,queue.length)},async()=>{while(index<queue.length)await uploadOne(queue[index++])}));
  const failed=queue.filter(i=>i.status!=='done').length;imageUploadFeedback(failed?`${queue.length-failed} 张完成，${failed} 张需处理。请查看各图片下的原因并单独重试。`:`本批 ${queue.length} 张已全部处理完成。`,!!failed);
 }catch(e){imageUploadFeedback(e.message,true)}finally{imageBatchActive=false;renderImageBatch();refreshUploads().catch(()=>{});}
}
function syncImageProductOptions(rows){
 const field=$('productImageTarget'),old=field.value;
 field.innerHTML='<option value="">请选择图片所属产品</option>'+rows.map(({kb,record:r})=>`<option value="${kb?'product:'+kb.product_id:'library:'+r.library_id}">${escape(kb?.product.name||r.name)}${kb?'':'（待分析）'}</option>`).join('');
 field.value=old||$('libraryTarget').value;renderSavedImages();
}
function renderImageUploadHint(){syncUploadControls()}
function syncUploadControls(){
 const selected=!!$('productImageTarget').value;
 $('productImageTarget').disabled=false;
 for(const id of ['productImageFile','productImageFolder'])$(id).disabled=!selected;
 $('productImageUpload').disabled=imageBatchActive||!imageBatchQueue.some(i=>['waiting','failed','uncertain'].includes(i.status));
 $('productImageUpload').textContent=imageBatchActive?'正在上传…':'上传 / 重试待处理图片';
 $('imageBatchRetry').hidden=true;
 $('refreshProductImages').disabled=!!uploadRefreshPromise;
 $('imageUploadHint').textContent=selected?'图片会关联到当前所选产品。支持多选、文件夹和拖放，可一次查看全部图片。':'请先选择图片关联产品。';
 $('libraryUpload').disabled=knowledgeUploading||!$('libraryWord').files.length;
 for(const id of ['libraryWord','libraryTarget','libraryName','libraryNotes'])$(id).disabled=knowledgeUploading;
 $('libraryUpload').textContent=knowledgeUploading?'正在上传知识库…':'上传并保存，等待人工分析';
 document.querySelectorAll('.upload-retry').forEach(b=>b.disabled=imageBatchActive);
}
$('productImageFile').onchange=()=>{selectImageBatch($('productImageFile').files,'所选图片');$('productImageFile').value=''};
$('productImageFolder').onchange=()=>{selectImageBatch($('productImageFolder').files,'所选文件夹');$('productImageFolder').value=''};
$('productImageUpload').onclick=()=>uploadImageBatch();
$('productImageTarget').onchange=()=>{renderSavedImages();syncUploadControls()};
$('refreshProductImages').onclick=()=>refreshUploads().catch(e=>imageUploadFeedback(e.message,true));
const imageDrop=$('imageDropZone');
imageDrop.ondragover=e=>{e.preventDefault();imageDrop.classList.add('dragging')};imageDrop.ondragleave=()=>imageDrop.classList.remove('dragging');imageDrop.ondrop=e=>{e.preventDefault();imageDrop.classList.remove('dragging');selectImageBatch(e.dataTransfer.files,'拖入图片')};
$('libraryUpload').onclick=async()=>{
 if(knowledgeUploading)return;const file=$('libraryWord').files[0];if(!file)return;
 const feedback=$('libraryFeedback');feedback.hidden=false;
 if(!file.name.toLowerCase().endsWith('.docx')||file.size>5*1024*1024){feedback.textContent='请选择5MB以内的.docx文件';feedback.dataset.state='error';return}
 const [kind,id]=$('libraryTarget').value.split(':'),meta={name:$('libraryName').value,notes:$('libraryNotes').value,...(id?{[kind==='product'?'product_id':'library_id']:id}:{})};
 knowledgeUploading=true;syncUploadControls();feedback.textContent='正在读取知识库…';feedback.dataset.state='working';
 try{await refreshUploads();const payload={...meta,filename:file.name,content_base64:await readBatchImage({file})},key=uploadID();let result;
  for(let attempt=0;attempt<3;attempt++)try{result=await uploadRequest('kb_upload',payload,key,n=>{feedback.textContent=n===100?'文件已传送，正在保存知识库…':'知识库上传 '+n+'%'});break}catch(e){if(e.status&&e.status<500&&![401,403,408,429].includes(e.status)||attempt===2)throw e;await refreshUploads();await uploadSleep(800)}
  libraryNextTarget=result.result.library_id;feedback.textContent=result.result.message;feedback.dataset.state='success';$('libraryWord').value='';await refreshUploads();
 }catch(e){feedback.textContent=e.message+'；原文件选择已保留。';feedback.dataset.state='error'}finally{knowledgeUploading=false;syncUploadControls()}
};
// Adopt a pending image left by the old UI without letting it block unrelated work.
if(pendingAction?.path==='control/product_image_upload'){
 try{const p=JSON.parse(pendingAction.payload),bytes=Uint8Array.from(atob(p.content_base64),c=>c.charCodeAt(0));const file=new File([bytes],p.filename,{type:'image/*'});
  const item={id:pendingAction.key,file,path:p.filename,target:p.product_id?'product:'+p.product_id:'library:'+p.library_id,targetName:'之前选择的产品',status:'uncertain',progress:0,reason:'上次上传结果待核对',preview:URL.createObjectURL(file)};imageBatchQueue.push(item);saveUpload(item).then(()=>{pendingAction=null;sessionStorage.removeItem('geo.creation.pending');buttons()});
 }catch{}
}
restoreUploads();
setTimeout(()=>refreshUploads().catch(e=>imageUploadFeedback(e.message,true)),0);
setInterval(()=>{if(activeView==='knowledge'&&!imageBatchActive)refreshUploads().catch(()=>{})},12000);

