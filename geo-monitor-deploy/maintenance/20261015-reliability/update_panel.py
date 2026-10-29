from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'geo-monitor-deploy/panel.html'
s=p.read_text('utf-8-sig')
s=s.replace('<div class="current-settings" id="currentSettings"></div>', '<div class="current-settings" id="currentSettings"></div><div id="progressDetail" class="hint" role="status"></div>')
s=s.replace('<div class="notice" id="notice" role="status"></div>', '<div class="notice" id="notice" role="status"></div><button id="retryAction" hidden onclick="retryAction()">核对并重试未确认操作</button>')
s=s.replace("draftCache={};", "draftCache={},connected=false;\nlet pendingAction=JSON.parse(sessionStorage.getItem('geo.capture.pending')||'null');")
s=s.replace("running_with_errors:'采集中 · 有异常'", "running_delivery_backoff:'等待完整回执',running_with_errors:'采集中 · 有异常'")
s=s.replace("function buttons(){for", "function buttons(){let locked=working||!connected||!!pendingAction;for")
s=s.replace("e.disabled=working;let m=current()", "e.disabled=working;let m=current()")
start=s.index('function buttons()');end=s.index('\nfunction render()',start)
part=s[start:end].replace('disabled=working||','disabled=locked||')
part=part.replace(" $('loginBtn')", " $('retryAction').hidden=!pendingAction;$('retryAction').disabled=working||!connected;\n $('loginBtn')")
s=s[:start]+part+s[end:]
needle=" $('captured').textContent=c.captured;"
replacement=""" const phaseNames={starting:'准备启动',preparing:'检查新会话',sending_once:'提交本题一次',awaiting_ack:'等待原请求确认',generating:'模型正在生成',awaiting_complete_snapshot:'复核正文、全部信源与引用',verifying_complete_snapshot:'复核两次完成快照',rate_wait:'等待发送间隔',read_backoff:'原会话读取退避',delivery:'等待 GEO processed 回执',collecting:'网页采集／间隔等待'};
 const p=c.progress||{},diags=c.diagnostics||[];let detail=[phaseNames[p.phase]||labels[p.phase]||''];if(p.ordinal)detail.push('第 '+p.ordinal+' 题');if(p.next_at&&p.next_at>Date.now()/1000)detail.push('预计 '+time(p.next_at)+' 再检查');if(c.pending_delivery)detail.push(c.pending_delivery+' 条完整结果等待回执，暂不开始下一题');if(p.deadline_at&&['awaiting_ack','generating','awaiting_complete_snapshot'].includes(p.phase))detail.push('原请求限时复核至 '+time(p.deadline_at));
 const reasons={receiver_auth_required:'回传鉴权需处理；完整结果已保留',receiver_request_rejected:'回传参数被拒绝，需核对配置',receiver_rate_limited:'接收服务限流，按退避时间重试',receiver_unavailable:'接收服务暂不可用，自动退避',receiver_network_error:'回传网络异常，自动退避',receiver_processing_error:'接收端处理异常，保留原请求等待复核',result_or_receipt_invalid:'完整性或回执校验未通过，保留证据',awaiting_processed:'已排队，等待入库回执'};
 for(const d of diags){detail.push(reasons[d.code]||'回传状态待复核');if(d.next_at>Date.now()/1000)detail.push('下次检查 '+time(d.next_at))}if(c.updated_at)detail.push('心跳 '+time(c.updated_at));$('progressDetail').textContent=detail.filter(Boolean).join(' · ');
 $('captured').textContent=c.captured;"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace("models=data.models;csrf=data.csrf;", "models=data.models;csrf=data.csrf;connected=true;")
s=s.replace("catch(e){$('live').textContent='连接中断 · 保留上次数据';notify(e.message,true)}finally{refreshing=false}","catch(e){connected=false;$('live').textContent='连接中断 · 保留上次数据';notify('连接中断，操作已禁用；恢复后将重新核对状态。',true);buttons()}finally{refreshing=false}")
start=s.index('async function request(action,body={})');end=s.index('\nasync function perform(',start)
s=s[:start]+"""async function request(action,body={}){
 const payload=JSON.stringify(body);if(pendingAction&&(pendingAction.model!==selected||pendingAction.action!==action||pendingAction.payload!==payload))throw Error('上次操作尚未确认，请先核对并重试该操作');
 const item=pendingAction||{model:selected,action,payload,key:Array.from(crypto.getRandomValues(new Uint8Array(16))).map(x=>x.toString(16).padStart(2,'0')).join('')};
 pendingAction=item;sessionStorage.setItem('geo.capture.pending',JSON.stringify(item));buttons();
 try{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);let r;try{r=await fetch('/api/control/'+item.model+'/'+item.action,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Action-Id':item.key},body:item.payload,signal:controller.signal})}finally{clearTimeout(timer)}
 const result=await r.json();if(r.status>=500)throw Error('操作结果未确认');pendingAction=null;sessionStorage.removeItem('geo.capture.pending');if(!r.ok||!result.ok)throw Error(result.message||'操作未完成，请查看当前状态');return result;
 }catch(e){if(pendingAction)throw Error('操作结果未确认，已保存操作编号。请点击“核对并重试未确认操作”；不会创建重复任务。');throw e}
}
async function retryAction(){if(working||!connected||!pendingAction)return;working=true;buttons();try{const p=pendingAction;selected=p.model;await request(p.action,JSON.parse(p.payload));if(p.action==='settings'){delete draftCache[p.model];dirty=false}notify('已核对原操作结果');await refresh()}catch(e){notify(e.message,true)}finally{working=false;buttons()}}
"""+s[end:]
p.write_text(s,encoding='utf-8')

p=ROOT/'geo-monitor-deploy/creation/panel.html';s=p.read_text('utf-8-sig')
s=s.replace('<div id="limits"></div>', '<div id="limits"></div><small id="connection" role="status">正在连接</small><button id="retryAction" hidden>核对并重试未确认操作</button>')
s=s.replace("csrf='',busy=false;", "csrf='',busy=false,connected=false;let pendingAction=JSON.parse(sessionStorage.getItem('geo.creation.pending')||'null');")
start=s.index('async function request(path,body)');end=s.index('\nasync function act(',start)
s=s[:start]+"""function buttons(){document.querySelectorAll('button').forEach(x=>x.disabled=busy||!connected||!!pendingAction);$('retryAction').hidden=!pendingAction;$('retryAction').disabled=busy||!connected}
async function request(path,body){const headers={};let item;if(body){const payload=JSON.stringify(body);if(pendingAction&&(pendingAction.path!==path||pendingAction.payload!==payload))throw Error('上次操作尚未确认，请先核对');item=pendingAction||{path,payload,key:[...crypto.getRandomValues(new Uint8Array(16))].map(x=>x.toString(16).padStart(2,'0')).join('')};pendingAction=item;sessionStorage.setItem('geo.creation.pending',JSON.stringify(item));headers['Content-Type']='application/json';headers['X-CSRF-Token']=csrf;headers['X-Action-Id']=item.key}
const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);try{const r=await fetch(API+path,{method:body?'POST':'GET',headers,body:item?.payload,signal:controller.signal,cache:'no-store'});const data=await r.json();if(body&&r.status>=500)throw Error('操作结果未确认');if(body){pendingAction=null;sessionStorage.removeItem('geo.creation.pending')}if(!r.ok||data.ok===false)throw Error(data.message||'请求失败');return data}catch(e){if(body&&pendingAction)throw Error('操作结果未确认，已保存原操作编号；点击核对重试即可，避免重复创建或执行。');throw e}finally{clearTimeout(timer)}}
"""+s[end:]
s=s.replace("document.querySelectorAll('button').forEach(x=>x.disabled=false)","buttons()")
s=s.replace("async function refresh(){const d=await request('panel');csrf=d.csrf;", "async function refresh(){let d;try{d=await request('panel');connected=true;$('connection').textContent='已连接 · '+new Date().toLocaleTimeString()}catch(e){connected=false;$('connection').textContent='连接中断，保留上次数据；操作暂时禁用';buttons();throw e}csrf=d.csrf;")
s=s.replace("data-job=\"${j.job_id}\">校验并继续", "data-job=\"${j.job_id}\" ${j.day.status==='complete'?'disabled':''}>校验并继续")
s=s.replace("document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action,{job_id:b.dataset.job}));}","document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action,{job_id:b.dataset.job}));buttons();}")
s=s.replace("$('new').onclick=", "$ ('retryAction').onclick=()=>{if(pendingAction)act(pendingAction.path.replace('control/',''),JSON.parse(pendingAction.payload))};\n$('new').onclick=")
p.write_text(s,encoding='utf-8')
