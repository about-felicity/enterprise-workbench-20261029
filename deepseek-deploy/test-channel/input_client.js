// input-queue start
let inputEvents=[],inputBusy=false,inputTimer=null,inputPaused=false;
function input(value){
 if(finished||!csrf||!waiting||inputPaused)return;
 const last=inputEvents[inputEvents.length-1];
 if(value.type==='touch'&&value.action===2&&last?.type==='touch'&&last.action===2)inputEvents[inputEvents.length-1]=value;
 else if(value.type==='text'&&last?.type==='text'&&last.text.length+value.text.length<=4096)last.text+=value.text;
 else if(value.type==='scroll'&&last?.type==='scroll')last.delta=Math.max(-1000,Math.min(1000,last.delta+value.delta));
 else inputEvents.push(value);
 if(inputEvents.length>128){inputEvents=[];inputPaused=true;message.textContent='输入积压，请重连画面后继续；未发送的输入已清除。';return}
 if(!inputBusy&&!inputTimer)inputTimer=setTimeout(flushInput,value.type==='text'?20:0);
}
async function flushInput(){
 inputTimer=null;if(inputBusy||inputPaused||!inputEvents.length)return;
 if(finished||!waiting){inputEvents=[];return}
 let events=[],bytes=0;
 while(inputEvents.length&&events.length<16){const size=new TextEncoder().encode(JSON.stringify(inputEvents[0])).length;if(events.length&&bytes+size>18000)break;events.push(inputEvents.shift());bytes+=size}
 const currentFlow=flow;inputBusy=true;
 try{
  const value=events.length===1?events[0]:{type:'batch',events};
  const r=await fetch(prefix+'input',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Action-Id':key()},body:JSON.stringify({...value,flow:currentFlow}),signal:AbortSignal.timeout(12000)});
  if(!r.ok)throw Error('输入结果未确认，请重连画面后再操作；不会自动重复发送');
  if(currentFlow!==flow)throw Error('投屏会话已变化，请重连画面后继续');
 }catch(e){inputEvents=[];inputPaused=true;message.textContent=e.message}
 finally{inputBusy=false;if(inputEvents.length&&!inputPaused)inputTimer=setTimeout(flushInput,0)}
}
// input-queue end
let gesture=null,holdTimer=null;
function point(e){const r=screen.getBoundingClientRect();return{x:Math.max(0,Math.min(719,(e.clientX-r.left)*720/r.width)),y:Math.max(0,Math.min(1279,(e.clientY-r.top)*1280/r.height))}}
function startGesture(){if(!gesture||gesture.started)return;gesture.started=true;input({type:'touch',action:0,...gesture.start})}
screen.addEventListener('pointerdown',e=>{if(!waiting||inputPaused)return;e.preventDefault();screen.focus();screen.setPointerCapture(e.pointerId);gesture={start:point(e),started:false};holdTimer=setTimeout(startGesture,70)});
screen.addEventListener('pointermove',e=>{if(!gesture)return;e.preventDefault();const p=point(e);if(Math.hypot(p.x-gesture.start.x,p.y-gesture.start.y)<4&&!gesture.started)return;clearTimeout(holdTimer);startGesture();input({type:'touch',action:2,...p})});
for(const name of ['pointerup','pointercancel'])screen.addEventListener(name,e=>{if(!gesture)return;clearTimeout(holdTimer);const p=point(e);if(gesture.started)input({type:'touch',action:1,...p});else if(name==='pointerup')input({type:'click',...p});gesture=null});
