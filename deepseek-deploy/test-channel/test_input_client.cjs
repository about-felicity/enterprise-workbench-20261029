const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(process.argv[2],'utf8');
const code=source.slice(source.indexOf('// input-queue start'),source.indexOf("screen.addEventListener('keydown'"));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
function context(fail=false){
 const requests=[],handlers={};const screen={addEventListener:(k,v)=>handlers[k]=v,getBoundingClientRect:()=>({left:0,top:0,width:720,height:1280}),focus(){},setPointerCapture(){}};
 const c=vm.createContext({finished:false,csrf:'a'.repeat(64),waiting:true,flow:'b'.repeat(32),prefix:'/',key:()=> 'c'.repeat(32),message:{},TextEncoder,AbortSignal,setTimeout,clearTimeout,Math,screen,fetch:async(_,o)=>{requests.push(JSON.parse(o.body));await delay(60);return {ok:!fail}}});vm.runInContext(code,c);return {c,requests,handlers};
}
(async()=>{
 const a=context();vm.runInContext("input({type:'text',text:'0'})",a.c);await delay(30);
 for(let i=1;i<101;i++)vm.runInContext(`input({type:'text',text:${JSON.stringify(String(i%10))}})`,a.c);
 await delay(170);const texts=a.requests.flatMap(v=>v.type==='batch'?v.events:[v]).map(v=>v.text).join('');
 assert.equal(texts,'0'+Array.from({length:100},(_,i)=>String((i+1)%10)).join(''));assert(a.requests.length<=2);
 const b=context();const e={clientX:12,clientY:22,pointerId:1,preventDefault(){}};b.handlers.pointerdown(e);b.handlers.pointerup(e);await delay(90);assert.equal(b.requests.length,1);assert.equal(b.requests[0].type,'click');
 const c=context();c.handlers.pointerdown(e);for(let i=30;i<600;i++)c.handlers.pointermove({...e,clientX:i});c.handlers.pointerup({...e,clientX:600});await delay(100);
 assert.equal(c.requests.length,1);assert.deepEqual(c.requests[0].events.map(v=>v.action),[0,2,1]);assert.equal(c.requests[0].events[1].x,599);
 const d=context(true);vm.runInContext("input({type:'text',text:'single'})",d.c);await delay(100);vm.runInContext("input({type:'text',text:'not-replayed'})",d.c);await delay(100);assert.equal(d.requests.length,1);
 console.log(JSON.stringify({passed:true,checks:4,typing_events:101,typing_requests:a.requests.length,drag_events:572,drag_requests:c.requests.length,failed_input_retries:0}));
})().catch(e=>{console.error(e);process.exitCode=1});
