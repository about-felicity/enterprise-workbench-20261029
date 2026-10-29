import assert from 'node:assert/strict';
import test, { afterEach } from 'node:test';
import { GET, POST } from '../app/api/geo-capture/[...path]/route.ts';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const origin = 'http://192.168.31.106:3001';
const token = 'a'.repeat(64);
const actionId = 'b'.repeat(32);
const request = (path, options = {}) => new Request(origin+'/api/geo-capture/'+path, options);
const write = (extra = {}, body = '{}') => ({ method:'POST', headers:{ Origin:origin, 'Content-Type':'application/json', 'X-CSRF-Token':token, 'X-Action-Id':actionId, Cookie:`geo_dashboard_capture=${token}; geo_control=${'c'.repeat(64)}`, ...extra }, body });

test('daily schedule uses fixed authenticated control route', async () => {
  const body=JSON.stringify({enabled:true,time:'06:35',revision:2});
  globalThis.fetch=async (url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/control/schedule');
    assert.equal(init.headers.Cookie,'geo_control='+token);
    assert.equal(init.headers['X-CSRF-Token'],token);
    assert.equal(init.body,body);return Response.json({ok:true});
  };
  assert.equal((await POST(request('control/schedule',write({},body)))).status,200);
});

test('panel uses fixed local upstream and a separate HttpOnly cookie', async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, 'http://127.0.0.1:8803/api/panel');
    assert.equal(init.headers.Cookie, 'geo_control='+token);
    assert.equal(init.headers.Authorization, undefined);
    return Response.json({ csrf:token, models:[] }, { headers:{ 'Set-Cookie':`geo_control=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=21600` } });
  };
  const response = await GET(request('panel', {headers:{Cookie:`geo_dashboard_capture=${token}`}}));
  assert.equal(response.status,200);
  assert.match(response.headers.get('Set-Cookie'), /geo_dashboard_capture=.*HttpOnly; SameSite=Strict; Path=\/api\/geo-capture/);
  assert.equal(response.headers.get('Cache-Control'),'no-store');
});

test('allowed commands preserve body and idempotency identity', async () => {
  const body=JSON.stringify({revision:5});
  globalThis.fetch=async (url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/control/doubao1/new');
    assert.equal(init.headers.Origin,'http://127.0.0.1:8803');
    assert.equal(init.headers.Cookie,'geo_control='+token);
    assert.equal(init.headers['X-Action-Id'],actionId);
    assert.equal(init.body,body);
    return Response.json({ok:true});
  };
  assert.equal((await POST(request('control/doubao1/new',write({},body)))).status,200);
});

test('Yuanbao uses the same authenticated fixed control gateway', async () => {
  globalThis.fetch=async (url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/control/yuanbao/pause');
    assert.equal(init.headers['X-Action-Id'],actionId);
    assert.equal(init.headers.Cookie,'geo_control='+token);
    return Response.json({ok:true});
  };
  assert.equal((await POST(request('control/yuanbao/pause',write()))).status,200);
});

test('cross-origin writes are rejected before contacting controller', async () => {
  globalThis.fetch=()=>{throw Error('must not call upstream')};
  assert.equal((await POST(request('control/doubao1/stop',write({Origin:'http://foreign.example'})))).status,403);
  assert.equal((await POST(request('control/doubao1/stop',write({'Sec-Fetch-Site':'cross-site'})))).status,403);
});

test('no arbitrary proxy paths, receiver receipts or foreign hosts', async () => {
  globalThis.fetch=()=>{throw Error('must not call upstream')};
  assert.equal((await GET(request('receipts/deepseek/'+token))).status,404);
  assert.equal((await POST(request('control/unknown/start',write()))).status,404);
  assert.equal((await GET(new Request('http://foreign.example/api/geo-capture/panel'))).status,403);
});

test('bad action identity and oversized input are rejected', async () => {
  globalThis.fetch=()=>{throw Error('must not call upstream')};
  assert.equal((await POST(request('control/doubao1/new',write({'X-Action-Id':'invalid'})))).status,400);
  assert.equal((await POST(request('control/doubao1/settings',write({},'x'.repeat(1_100_001))))).status,413);
});

test('embedded UI uses same-origin commands and is only framed by itself', async () => {
  globalThis.fetch=async()=>new Response("<html><head></head><body><script>fetch('/api/panel');fetch('/api/control/'+selected+'/pause')</script></body></html>",{headers:{'Content-Type':'text/html; charset=utf-8','X-Frame-Options':'DENY'}});
  const response=await GET(request('ui'));const html=await response.text();
  assert.match(html,/fetch\('\/api\/geo-capture\/panel'\)/);
  assert.match(html,/\/api\/geo-capture\/control\//);
  assert.match(html,/geo-capture:layout/);
  assert.equal(response.headers.get('X-Frame-Options'),'SAMEORIGIN');
  assert.equal(response.headers.get('Content-Security-Policy'),"frame-ancestors 'self'");
});

test('upstream failure does not imply stopping capture or expose details', async () => {
  globalThis.fetch=async()=>{throw Error('private connection details')};
  const response=await GET(request('panel'));const body=await response.text();
  assert.equal(response.status,503);assert.doesNotMatch(body,/private connection details/);
});

test('manual login JPEG stays byte-identical and never exposes a browser port', async () => {
  const bytes=new Uint8Array([255,216,0,128,255,217]);
  globalThis.fetch=async(url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/login/frame');
    assert.equal(init.headers.Cookie,'geo_control='+token);
    return new Response(bytes,{headers:{'Content-Type':'image/jpeg'}});
  };
  const response=await GET(request('login/frame',{headers:{Cookie:`geo_dashboard_capture=${token}`}}));
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);
  assert.equal(response.headers.get('Cache-Control'),'no-store');
});

test('manual login accepts only same-origin bounded relay routes', async () => {
  const body=JSON.stringify({flow:'fixture-flow',type:'click',x:1,y:2});
  globalThis.fetch=async(url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/login/input');
    assert.equal(init.body,body);
    assert.equal(init.headers['X-CSRF-Token'],token);
    return Response.json({ok:true});
  };
  assert.equal((await POST(request('login/input',write({},body)))).status,200);
  globalThis.fetch=()=>{throw Error('must not call upstream')};
  assert.equal((await POST(request('login/input',write({Origin:'https://foreign.example'},body)))).status,403);
  assert.equal((await POST(request('login/evaluate',write({},body)))).status,404);
});

test('manual login HTML rewrites popup API calls under the public mount', async () => {
  globalThis.fetch=async()=>new Response("const prefix='/api/login/';fetch('/api/panel')",{headers:{'Content-Type':'text/html'}});
  const response=await GET(new Request('http://1any.top/api/geo-capture/login/ui',{
    headers:{'X-Forwarded-Prefix':'/geo_monitor','X-Forwarded-Proto':'https'}}));
  const html=await response.text();
  assert.match(html,/prefix='\/geo_monitor\/api\/geo-capture\/login\//);
  assert.match(html,/fetch\('\/geo_monitor\/api\/geo-capture\/panel'\)/);
});

const forwarded = { 'X-Forwarded-Prefix':'/geo_monitor', 'X-Forwarded-Proto':'https' };
test('both DeepSeek login controls retain exact channel identity',async()=>{
 for(const model of ['deepseek','deepseek2']){
  globalThis.fetch=async(url,init)=>{assert.equal(url,`http://127.0.0.1:8803/api/control/${model}/login_open`);assert.equal(init.headers.Cookie,'geo_control='+token);return Response.json({ok:true});};
  assert.equal((await POST(request(`control/${model}/login_open`,write()))).status,200);
 }
});
test('scrcpy stream is passed through without buffering with scoped flow',async()=>{
 const flow='d'.repeat(32);const input=new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('--scrcpy\r\n'));c.close();}});
 globalThis.fetch=async(url,init)=>{assert.equal(url,`http://127.0.0.1:8803/api/login/deepseek2/stream?flow=${flow}`);assert.equal(init.headers.Cookie,'geo_control='+token);return new Response(input,{headers:{'Content-Type':'multipart/x-mixed-replace; boundary=scrcpy'}});};
 const response=await GET(request(`login/deepseek2/stream?flow=${flow}`,{headers:{Cookie:`geo_dashboard_capture=${token}`}}));
 assert.equal(response.body,input);assert.equal(response.headers.get('X-Accel-Buffering'),'no');assert.equal(await response.text(),'--scrcpy\r\n');
});
test('invalid scrcpy flow and foreign channel are refused',async()=>{
 globalThis.fetch=()=>{throw Error('must not reach upstream')};
 assert.equal((await GET(request('login/deepseek/stream?flow=bad'))).status,400);
 assert.equal((await GET(request('login/other/stream?flow='+'a'.repeat(32)))).status,404);
});
test('public mobile input stays under authenticated same-origin API',async()=>{
 globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8803/api/login/deepseek2/input');assert.equal(init.headers['X-CSRF-Token'],token);return Response.json({ok:true});};
 assert.equal((await POST(new Request('http://1any.top/api/geo-capture/login/deepseek2/input',write({...forwarded,Origin:'https://1any.top'},JSON.stringify({flow:'d'.repeat(32),type:'text',text:'123'}))))).status,200);
});
test('daily date filtering preserves the selected date through the fixed gateway',async()=>{
  globalThis.fetch=async(url)=>{assert.equal(url,'http://127.0.0.1:8803/api/panel?date=2026-10-15');return Response.json({models:[]});};
  assert.equal((await GET(request('panel?date=2026-10-15&upstream=https://foreign.example'))).status,200);
});
test('live save and daily pause preserve the exact scoped request',async()=>{
  const body=JSON.stringify({questions:['推荐一款护发精油'],rounds:8,interval:60,revision:9,apply_now:true,day:'2026-10-16'});
  globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8803/api/control/yuanbao/settings');assert.equal(init.body,body);return Response.json({ok:true});};
  assert.equal((await POST(request('control/yuanbao/settings',write({},body)))).status,200);
});
test('VPS HTTPS writes preserve CSRF through a stripped path prefix', async () => {
  globalThis.fetch=async(url,init)=>{
    assert.equal(url,'http://127.0.0.1:8803/api/control/doubao1/settings');
    assert.equal(init.headers['X-Action-Id'],actionId);
    return Response.json({ok:true});
  };
  const options=write({...forwarded,Origin:'https://1any.top'});
  assert.equal((await POST(new Request('http://1any.top/api/geo-capture/control/doubao1/settings',options))).status,200);
});

test('public control cookie is Secure and scoped to mounted API', async () => {
  globalThis.fetch=async()=>Response.json({csrf:token},{headers:{'Set-Cookie':`geo_control=${token}; Path=/; HttpOnly`}});
  const response=await GET(new Request('http://1any.top/api/geo-capture/panel',{headers:forwarded}));
  assert.equal(response.status,200);
  assert.match(response.headers.get('Set-Cookie'),/Path=\/geo_monitor\/api\/geo-capture;/);
  assert.match(response.headers.get('Set-Cookie'),/; Secure$/);
});

test('public embedded HTML calls only the prefixed same-origin API', async () => {
  globalThis.fetch=async()=>new Response("<html><head></head><body><script>fetch('/api/panel');fetch('/api/control/'+selected+'/pause')</script></body></html>",{headers:{'Content-Type':'text/html'}});
  const response=await GET(new Request('http://1any.top/api/geo-capture/ui',{headers:forwarded}));
  const html=await response.text();
  assert.match(html,/fetch\('\/geo_monitor\/api\/geo-capture\/panel'\)/);
  assert.match(html,/\/geo_monitor\/api\/geo-capture\/control\//);
});

test('public forwarding requires fixed mount, HTTPS and matching Origin', async () => {
  globalThis.fetch=()=>{throw Error('must not call upstream')};
  assert.equal((await GET(new Request('http://1any.top/api/geo-capture/panel'))).status,403);
  assert.equal((await GET(new Request('http://1any.top/api/geo-capture/panel',{headers:{...forwarded,'X-Forwarded-Prefix':'/elsewhere'}}))).status,403);
  assert.equal((await POST(new Request('http://1any.top/api/geo-capture/control/doubao1/pause',write({...forwarded,Origin:'https://foreign.example'})))).status,403);
});
