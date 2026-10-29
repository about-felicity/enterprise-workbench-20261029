const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const file of ['wizard.js','panel.html']){
 const source=fs.readFileSync('geo-monitor-deploy/creation/'+file,'utf8');
 const fn=source.slice(source.indexOf('function taskListItem('),source.indexOf('function renderDailyTasks()',source.indexOf('function taskListItem(')));
 const ctx={escape:String,isTerminal:()=>false,dayActions:()=>[],studioStates:{},deleteTarget:null,data:{settings:{daily_budget_cny:30}}};
 vm.createContext(ctx);vm.runInContext(fn,ctx);
 for(const articles of [0,7]){
  const p={plan_id:'a',frequency:'daily',enabled:true,product:{name:'产品'},questions:['问题'],channels:[],capture_time:'10:00'};
  const html=ctx.taskListItem(p,{today:'2026-10-27',daily_tasks:[{plan_id:'a',date:'2026-10-27',articles,status:'creating'}]});
  assert(!html.includes('<progress'));assert(html.includes(articles+' 篇'));assert(html.includes('已生成文章'));assert(!html.includes('个问题完成'));
 }
}
console.log('Rendered task cards: zero/nonzero article counts and no progress bars passed');
