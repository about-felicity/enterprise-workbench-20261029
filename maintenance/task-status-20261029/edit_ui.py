from pathlib import Path
w=Path(__file__).resolve().parents[2];p=w/'geo-monitor-deploy/creation/panel.html';s=p.read_text('utf8')
helper='''function taskStateBadge(t){
 const state=t?.status||'not_enabled',extra=t?.supplement||{};
 const labels={capturing:'补采中',waiting:'等待补采',checking_materials:'补采素材检查中',waiting_verification:'补采需验证'};
 const label=(['supplementing','waiting_login'].includes(state)&&labels[extra.status])||(state==='supplementing'?'补采中':studioStates[state]||state);
 const tone=state==='complete'||state==='capture_only_complete'?'done':['needs_attention','waiting_login','complete_with_failures','insufficient_materials'].includes(state)?'attention':state==='supplementing'?'supplement':['collecting','creating','capture_retrying'].includes(state)?'running':'waiting';
 const detail=extra.status?[(extra.attempt?'第 '+extra.attempt+' 轮':''),extra.question||'',extra.status==='waiting'&&extra.next_at?'下次检查：'+dt(extra.next_at):''].filter(Boolean).join(' · '):'';
 return `<span class="task-live-status"><span class="badge state-${tone}" data-task-status="${escape(state)}">${escape(label)}</span>${detail?`<small>${escape(detail)}</small>`:''}</span>`;
}
function taskRefreshHint(ok){for(const id of ['taskLiveNotice','dailyLiveNotice']){let el=$(id);if(!el){el=document.createElement('p');el.id=id;el.className='task-live-notice';el.setAttribute('role','status');$(id==='taskLiveNotice'?'planQueue':'dailyCards').before(el)}el.textContent=ok?'状态已更新：'+dt(data.at)+'（北京时间） · 每 5 秒自动检查':'状态更新失败，以下为上次结果；正在重连';el.dataset.stale=String(!ok)}}
'''
assert 'function taskStateBadge' not in s;s=s.replace('function taskListItem(p,st){',helper+'function taskListItem(p,st){',1)
s=s.replace("||days.slice().sort((a,b)=>b.date.localeCompare(a.date))[0]",'')
s=s.replace('<span class="badge">${escape(status)}</span>','${taskStateBadge(t||{status:state})}')
s=s.replace('<span class="badge">${escape(studioStates[t.status]||t.status)}</span>','${taskStateBadge(t)}')
s=s.replace("['collecting','creating'].includes(t.status)","['collecting','creating','supplementing','capture_retrying'].includes(t.status)")
s=s.replace('renderStudio();buttons();return true','renderStudio();taskRefreshHint(true);buttons();return true',1)
s=s.replace("connected=false;$('connection').textContent=", "connected=false;taskRefreshHint(false);$('connection').textContent=",1)
s=s.replace('setInterval(refresh,10000);',"setInterval(()=>{if(!document.hidden)refresh()},5000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});")
s=s.replace(' activeView=view;',' activeView=view;\n if(data&&[\'tasks\',\'progress\'].includes(view))refresh();',1)
s=s.replace('</style>','''
.task-live-status{display:inline-flex;flex-direction:column;align-items:flex-end;gap:5px;max-width:320px}.task-live-status small{font-size:12px;text-align:right;overflow-wrap:anywhere}.badge.state-supplement{background:#fff1d6;color:#8a4900;border:1px solid #e8af40}.badge.state-running{background:#e7f0ff;color:#1548a0}.badge.state-done{background:#e4f6ec;color:#146b3c}.badge.state-attention{background:#ffebe9;color:#a12721}.badge.state-waiting{background:#eef0f4;color:#505866}.task-live-notice{font-size:12px;color:#526172}.task-live-notice[data-stale="true"]{color:#a12721}
</style>''',1)
p.write_text(s,encoding='utf8')
print('Task badges and refresh status updated')
