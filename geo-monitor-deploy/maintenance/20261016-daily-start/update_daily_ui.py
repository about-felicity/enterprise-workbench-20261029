"""One-time source edit for the daily task interface."""
from pathlib import Path
p=Path('geo-monitor-deploy/panel.html');s=p.read_text('utf-8-sig')
def replace(old,new):
    global s
    assert old in s,old[:100]
    s=s.replace(old,new)
replace('</style>','''
.daily-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.daily-date{display:flex;align-items:center;gap:9px}.daily-date input{padding:8px;border:1px solid var(--line);border-radius:8px;background:white;min-width:145px}.daily-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.daily-model{text-align:left;min-width:0;padding:15px;font-weight:400}.daily-model.selected{border-color:var(--green);background:#edf7f2}.daily-model strong{display:block}.daily-model .daily-numbers{font-size:20px;color:var(--green);margin:8px 0}.daily-model small{display:block;color:var(--muted)}.daily-model .pill{float:right;font-size:11px}.question-progress{margin-top:18px;max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:10px}.question-progress th{position:sticky;top:0;background:#eff5f2}.question-progress td:first-child{min-width:180px;white-space:normal}.question-progress td:not(:first-child){text-align:center}.daily-note{margin:12px 0 0;color:var(--muted)}.daily-warning{color:var(--amber);margin-top:10px}.daily-section{margin-bottom:20px}.history-config{font-size:11px;white-space:normal;overflow-wrap:anywhere;max-width:430px}.history-config pre{white-space:pre-wrap;font:inherit}.date-readonly{color:var(--amber)}
@media(max-width:900px){.daily-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.daily-grid{grid-template-columns:1fr}.daily-heading{align-items:flex-start}.daily-date{flex-wrap:wrap}.question-progress{max-height:280px}}
</style>''')
replace('<div class="workspace">','''<section class="card daily-section"><div class="daily-heading"><div><h2 style="margin:0">每日采集任务</h2><div class="subtle" id="dailyScheduleInfo">北京时间 05:00 · 百度采完后启动文心</div></div><div class="daily-date"><label for="taskDate">任务日期</label><input id="taskDate" type="date" onchange="changeDate(this.value)"><button id="todayBtn" onclick="changeDate(serverToday)">今天</button></div></div><div class="daily-grid" id="dailyModels"></div><div class="daily-note" id="dailyDescription"></div><div class="daily-warning" id="dailyError" role="status"></div><div class="question-progress"><table><thead><tr><th>问题</th><th>目标轮数</th><th>已入库</th><th>还需采集</th></tr></thead><tbody id="dailyQuestions"></tbody></table></div></section><div class="workspace">''')
replace('<h2>下次任务设置</h2>','<h2 id="settingsTitle">任务配置</h2>')
replace('设置保存后用于新任务，当前任务的问题和轮数保持锁定。','保存后立即更新今天的剩余任务，同时更新每天的默认配置。当前题先完成回传；手动暂停的任务保持暂停。')
replace('>保存设置</button>','>保存并立即生效</button>')
replace('<span class="small-label">新任务计划</span>','<span class="small-label">每日目标</span>')
replace('id="newBtn" class="primary" style="width:100%;margin-top:15px"','id="newBtn" class="primary" hidden style="width:100%;margin-top:15px"')
replace('id="stopBtn" class="danger"','id="stopBtn" class="danger" hidden')
replace('>继续任务</button>','>继续今天的任务</button>')
replace('暂停和停止会等待当前题完成并确认回传。停止后保留历史记录，开始新一批请使用右侧设置。','手动暂停后不会自动恢复。点击继续将执行今天剩余的采集，已完成数据保留。')
replace("connected=false;","connected=false,viewDate='',serverToday='';")
replace("const labels={","const labels={scheduled:'待定时启动',queued:'等待启动',applying:'正在应用新配置',waiting_for_baidu:'等待百度采完',recovering:'正在补读原任务',incomplete:'未完成',")
replace("function markDirty(){","function markDirty(){if(!current()?.daily?.editable)return;")
replace("有未保存的修改；保存后才能开始新任务","有未保存的修改；点击保存后立即应用")
replace("function buttons(){","function buttons(){")
replace("let c=m.current,busy=active(c.service_state),complete=", "let c=m.current,d=m.daily||{},historical=!d.editable,busy=active(c.service_state),complete=")
replace("$('pauseBtn').disabled=locked||!busy||['pausing','stopping'].includes(c.state);", "$('pauseBtn').disabled=locked||historical||d.status==='complete'||d.desired==='paused';")
replace("$('resumeBtn').disabled=locked||busy||complete||c.stop_requested||loginBusy||c.needs_review>0||!fresh||!gate.can_resume;", "$('resumeBtn').disabled=locked||historical||!!d.error||!d.remaining||busy||loginBusy||(m.id==='deepseek'&&(!fresh||!(gate.can_resume||gate.can_start)));")
replace("$('saveBtn').disabled=locked||!dirty;", "$('saveBtn').disabled=locked||historical||!dirty;")
replace("$('retryAction').hidden=!pendingAction;", "for(let e of document.querySelectorAll('#questions,#rounds,#interval,#resetBtn'))e.disabled=working||historical;$('taskDate').disabled=working;$('todayBtn').disabled=working;$('newHint').textContent=historical?'所选日期只供查看；切换到今天后可以修改配置。':'保存后立即生效；后台按今天已入库数量补足目标，不会重跑已完成的数据。';$('retryAction').hidden=!pendingAction;")
replace("function render(){let m=current();if(!m)return;let c=m.current;", "function render(){let m=current();if(!m)return;let c=m.current;renderDaily();")
replace("m.name+' · 当前任务'", "m.name+' · 执行批次'")
replace("let switched=editingModel!==selected,cache=draftCache[selected];", "let switched=editingModel!==selected,cache=m.daily.editable?draftCache[selected]:null,config=m.daily.config;dirty=!!cache;")
replace("m.settings.questions.join('\\n')", "config.questions.join('\\n')")
replace("cache?cache.rounds:m.settings.rounds", "cache?cache.rounds:config.rounds")
replace("cache?cache.interval:m.settings.interval", "cache?cache.interval:config.interval")
replace("同一问题下，相同正文与完整信源只回传一次；每轮观测均保留。", "每轮独立入库，百度卡片按当天正文去重统计；真实采集轮数保留。")
replace("let data=await r.json();models=data.models;", "let data=await r.json();models=data.models;viewDate=data.date;serverToday=data.today;$('taskDate').value=viewDate;")
replace("fetch('/api/panel',{", "fetch('/api/panel'+(viewDate?'?date='+encodeURIComponent(viewDate):''),{")
replace("let result=await request(action);", "let result=await request(action,['pause','resume'].includes(action)?{scope:'daily',day:viewDate}:{});")
replace("revision:draftCache[selected]?draftCache[selected].revision:current().revision}", "revision:draftCache[selected]?draftCache[selected].revision:current().revision,apply_now:true,day:viewDate}")
replace("$('revision').textContent='v'+m.revision;", "$('settingsTitle').textContent=m.daily.editable?'任务配置 · 保存即生效':'任务配置 · '+viewDate+'（只读）';$('revision').textContent='v'+m.revision;")
replace("$('historyRows').append(tr)", "let detail=node('details',undefined,'history-config'),summary=node('summary','查看配置');detail.append(summary,node('pre',(h.config?.questions||[]).join('\\n')+'\\n每题 '+(h.config?.rounds||0)+' 轮 · 间隔 '+(h.config?.interval||0)+' 秒'));id.append(detail);$('historyRows').append(tr)")
replace("$('analysisLink').href=", '''function changeDate(day){if(working||!day)return;viewDate=day;editingModel='';dirty=false;void refresh()}
function renderDaily(){const d=current().daily;$('dailyModels').replaceChildren();for(const m of models){const v=m.daily,b=node('button',undefined,'daily-model'+(m.id===selected?' selected':''));b.onclick=()=>select(m.id);b.append(node('span',labels[v.status]||v.status,'pill'),node('strong',m.name),node('div',v.error?'进度暂不可用':v.credited+' / '+v.target,'daily-numbers'),node('small',v.config.questions.length+' 个问题 × '+v.config.rounds+' 轮 · 间隔 ≥ '+v.config.interval+' 秒'),node('small',v.error?'正在重新核对':('已入库 '+v.completed+' 次 · 剩余 '+v.remaining+' 次')));$('dailyModels').append(b)}$('dailyDescription').textContent=current().name+' · '+viewDate+' · 每日目标 '+d.target+' 次，已入库 '+d.completed+' 次；超出目标的历史观测仍保留。'+(d.editable?'':' 所选日期只读。');$('dailyError').textContent=d.error||'';$('dailyQuestions').replaceChildren();for(const q of d.questions){const tr=node('tr');tr.append(node('td',q.question),node('td',q.target),node('td',d.error?'—':q.completed),node('td',d.error?'—':q.remaining));$('dailyQuestions').append(tr)}}
$('analysisLink').href=' esplit'''.replace("=' esplit","="))
p.write_text(s,encoding='utf8')
