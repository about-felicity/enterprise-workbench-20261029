let productPreviewURL='',imageBatchQueue=[],imageBatchActive=false,imageBatchTarget='';
$('libraryTarget').addEventListener('change',buttons);
function selectImageBatch(files,source){
 if(busy||imageBatchActive||pendingAction)return;
 if(productPreviewURL)URL.revokeObjectURL(productPreviewURL);
 imageBatchTarget='';
 imageBatchQueue=Array.from(files).map(file=>{
  const supported=/\.(jpe?g|png|webp)$/i.test(file.name)||['image/jpeg','image/png','image/webp'].includes(file.type);
  const reason=!supported?'非支持图片，已跳过':file.size>5*1024*1024?'超过5MB，已跳过':file.size===0?'空文件，已跳过':'';
  return {file,path:file.webkitRelativePath||file.name,status:reason?'skipped':'waiting',reason};
 });
 const count=imageBatchQueue.filter(i=>i.status==='waiting').length;
 $('imageBatchSelection').textContent=`${source}：找到 ${count} 张可上传图片，跳过 ${imageBatchQueue.length-count} 个文件。`;
 const first=imageBatchQueue.find(i=>i.status==='waiting');$('productImagePreview').hidden=!first;
 if(first){productPreviewURL=URL.createObjectURL(first.file);$('productImagePreview').src=productPreviewURL}
 $('productImageFeedback').hidden=true;renderImageBatch();buttons();
}
function renderImageBatch(){
 const box=$('imageBatchProgress');box.hidden=!imageBatchQueue.length;box.replaceChildren();
 const counts={done:0,failed:0,skipped:0,waiting:0,uploading:0,uncertain:0};for(const i of imageBatchQueue)counts[i.status]++;
 const note=document.createElement('p');note.textContent=`已上传 ${counts.done} 张 · 待上传 ${counts.waiting} 张 · 失败 ${counts.failed} 张 · 跳过 ${counts.skipped} 个${counts.uncertain?' · 1 张结果待核对':''}`;box.append(note);
 const list=document.createElement('div');list.style.cssText='max-height:220px;overflow:auto';
 const labels={done:'上传成功',waiting:'等待上传',uploading:'正在上传',failed:'上传失败，可重试',skipped:'已跳过',uncertain:'结果待核对，已暂停后续上传'};
 for(const item of imageBatchQueue){const row=document.createElement('small');row.textContent=`${item.path}：${labels[item.status]}${item.reason?'（'+item.reason+'）':''}`;list.append(row)}box.append(list);
}
function readBatchImage(item){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=()=>reject(Error('文件读取失败，请重新选择'));r.readAsDataURL(item.file)})}
async function uploadImageBatch(resumePending=false){
 if(busy||imageBatchActive||!connected||(!resumePending&&pendingAction))return;
 const target=imageBatchTarget||$('libraryTarget').value,[kind,id]=target.split(':');if(!id)return;
 imageBatchTarget=target;imageBatchActive=true;buttons();
 try{
  for(const item of imageBatchQueue){
   if(!['waiting','failed','uncertain'].includes(item.status))continue;
   item.status='uploading';item.reason='';renderImageBatch();
   try{
    item.payload ||= {[kind==='product'?'product_id':'library_id']:id,filename:item.file.name,content_base64:await readBatchImage(item)};
    const result=await act('product_image_upload',item.payload);
    if(result){item.status='done';delete item.payload}
    else{item.status=pendingAction?'uncertain':'failed';item.reason=$('productImageFeedback').textContent}
   }catch(e){item.status='failed';item.reason=e.message}
   renderImageBatch();if(pendingAction)break;
  }
  const done=imageBatchQueue.filter(i=>i.status==='done').length,failed=imageBatchQueue.filter(i=>i.status==='failed').length;
  message(pendingAction?`已上传 ${done} 张，有一张结果待核对。点击“核对并继续上传”，会沿用原操作编号。`:`已上传 ${done} 张图片${failed?'，'+failed+' 张失败，可点击上传按钮重试失败项。':'，批量上传已完成。'}`,!!pendingAction||!!failed);
 }finally{imageBatchActive=false;buttons();renderImageBatch()}
}
$('productImageFile').onchange=()=>{selectImageBatch($('productImageFile').files,'所选图片');$('productImageFolder').value=''};
$('productImageFolder').onchange=()=>{selectImageBatch($('productImageFolder').files,'所选文件夹');$('productImageFile').value=''};
$('productImageUpload').onclick=()=>uploadImageBatch();
const priorImageRetry=$('retryAction').onclick;
$('retryAction').onclick=()=>pendingAction?.path==='control/product_image_upload'&&imageBatchQueue.some(i=>i.status==='uncertain')?uploadImageBatch(true):priorImageRetry();
$('imageBatchRetry').onclick=()=>uploadImageBatch(true);
