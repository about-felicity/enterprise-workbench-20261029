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
