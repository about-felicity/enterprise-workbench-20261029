import assert from 'node:assert/strict';
import test,{afterEach} from 'node:test';
import {GET,POST} from '../app/api/geo-creation/[...path]/route.ts';
const original=globalThis.fetch;afterEach(()=>globalThis.fetch=original);
const origin='http://192.168.31.106:3001',token='a'.repeat(64),id='b'.repeat(32);
const request=(path,options={})=>new Request(origin+'/api/geo-creation/'+path,options);
const write=(extra={})=>({method:'POST',headers:{Origin:origin,'Content-Type':'application/json','X-CSRF-Token':token,'X-Action-Id':id,Cookie:`geo_dashboard_creation=${token}`,...extra},body:'{}'});

test('lightweight upload session forwards cookie without expensive panel query',async()=>{
 globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8804/api/uploads');assert.equal(init.headers.Cookie,'geo_creation='+token);return Response.json({ok:true,csrf:token,studio:{product_images:[]}})};
 assert.equal((await GET(request('uploads',{headers:{Cookie:`geo_dashboard_creation=${token}`}}))).status,200);
});
test('thumbnail option reaches image reader',async()=>{
 globalThis.fetch=async(url)=>{assert.equal(url,'http://127.0.0.1:8804/api/product_image?id=image-test&thumbnail=1');return new Response(new Uint8Array([255,216]),{headers:{'Content-Type':'image/jpeg'}})};
 assert.equal((await GET(request('product_image?id=image-test&thumbnail=1'))).headers.get('Content-Type'),'image/jpeg');
});

test('private material controls stay on isolated authenticated creation upstream',async()=>{
  globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8804/api/control/materials_settings');assert.equal(init.headers.Cookie,'geo_creation='+token);assert.equal(init.headers.Origin,'http://127.0.0.1:8804');return Response.json({ok:true})};
  assert.equal((await POST(request('control/materials_settings',write()))).status,200);
});
test('knowledge import and daily pipeline controls use the same authenticated upstream',async()=>{
  for(const name of ['kb_import','kb_save','kb_upload','kb_edit','product_image_upload','plan_save','plan_delete','day_pause','day_resume']){
    globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8804/api/control/'+name);assert.equal(init.headers.Cookie,'geo_creation='+token);return Response.json({ok:true})};
    assert.equal((await POST(request('control/'+name,write()))).status,200);
  }
});

test('delete forwards its body and action ID from LAN and public mount',async()=>{
  let calls=0;
  globalThis.fetch=async(url,init)=>{calls++;assert.equal(url,'http://127.0.0.1:8804/api/control/plan_delete');assert.equal(init.body,JSON.stringify({plan_id:'plan-test'}));assert.equal(init.headers['X-Action-Id'],id);assert.equal(init.headers['X-CSRF-Token'],token);assert.equal(init.headers.Cookie,'geo_creation='+token);return Response.json({ok:true,result:{plan_id:'plan-test'}})};
  const options={...write(),body:JSON.stringify({plan_id:'plan-test'})};
  assert.equal((await POST(request('control/plan_delete',options))).status,200);
  const publicRequest=new Request('https://1any.top/api/geo-creation/control/plan_delete',{...options,headers:{...options.headers,Origin:'https://1any.top','X-Forwarded-Prefix':'/geo_monitor','X-Forwarded-Proto':'https'}});
  assert.equal((await POST(publicRequest)).status,200);assert.equal(calls,2);
});

test('delete retains origin, CSRF and mount validation',async()=>{
  globalThis.fetch=()=>{throw Error('invalid delete must not reach upstream')};
  assert.equal((await POST(request('control/plan_delete',write({Origin:'https://evil.test'})))).status,403);
  assert.equal((await POST(request('control/plan_delete',write({'X-CSRF-Token':'bad'})))).status,400);
  assert.equal((await POST(request('control/plan_delete',write({'X-Action-Id':'bad'})))).status,400);
  assert.equal((await POST(new Request('https://1any.top/api/geo-creation/control/plan_delete',write()))).status,403);
});

test('Word download remains byte-identical and scoped to fixed upstream',async()=>{
  const bytes=new Uint8Array([80,75,3,4,255,0,129,231]);
  globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8804/api/download?job=j&article=a&kind=word');assert.equal(init.headers.Cookie,'geo_creation='+token);return new Response(bytes,{headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','X-Content-SHA256':'digest'}})};
  const response=await GET(request('download?job=j&article=a&kind=word',{headers:{Cookie:`geo_dashboard_creation=${token}`}}));
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);assert.equal(response.headers.get('X-Content-SHA256'),'digest');
});
test('write preserves idempotency and rejects foreign origin',async()=>{
  let calls=0;globalThis.fetch=async(url,init)=>{calls++;assert.equal(url,'http://127.0.0.1:8804/api/control/new');assert.equal(init.headers['X-Action-Id'],id);assert.equal(init.headers.Origin,'http://127.0.0.1:8804');return Response.json({ok:true})};
  assert.equal((await POST(request('control/new',write()))).status,200);
  assert.equal((await POST(request('control/new',write({Origin:'https://evil.test'})))).status,403);assert.equal(calls,1);
});
test('public prefix and HttpOnly cookie are retained',async()=>{
  globalThis.fetch=async()=>new Response("const API='/api/';",{headers:{'Content-Type':'text/html','Set-Cookie':`geo_creation=${token}; HttpOnly`}});
  const response=await GET(new Request('https://1any.top/api/geo-creation/ui',{headers:{'X-Forwarded-Prefix':'/geo_monitor','X-Forwarded-Proto':'https'}}));
  assert.match(await response.text(),/\/geo_monitor\/api\/geo-creation\//);assert.match(response.headers.get('Set-Cookie'),/Path=\/geo_monitor\/api\/geo-creation.*Secure/);
});
test('arbitrary proxy paths and malformed writes never reach upstream',async()=>{
  globalThis.fetch=()=>{throw Error('must not reach upstream')};
  assert.equal((await GET(request('secrets'))).status,404);
  assert.equal((await POST(request('control/new',write({'X-CSRF-Token':'bad'})))).status,400);
  assert.equal((await GET(new Request('https://1any.top/api/geo-creation/status'))).status,403);
});

 test('manual publication is not exposed as a dashboard write',async()=>{globalThis.fetch=()=>{throw Error('must not forward')};assert.equal((await POST(request('control/kb_publish',write()))).status,404)});

test('knowledge upload accepts Word-sized JSON while edits stay bounded',async()=>{
 let calls=0;globalThis.fetch=async()=>{calls++;return Response.json({ok:true})};
 const options={...write(),body:JSON.stringify({content_base64:'a'.repeat(2_000_000)})};
 assert.equal((await POST(request('control/kb_upload',options))).status,200);
 assert.equal((await POST(request('control/kb_edit',options))).status,413);assert.equal(calls,1);
});

test('product image preview preserves query and exact bytes',async()=>{
 const bytes=new Uint8Array([137,80,78,71,255,0]);globalThis.fetch=async(url,init)=>{assert.equal(url,'http://127.0.0.1:8804/api/product_image?id=image-test');assert.equal(init.headers.Cookie,'geo_creation='+token);return new Response(bytes,{headers:{'Content-Type':'image/png'}})};
 const response=await GET(request('product_image?id=image-test',{headers:{Cookie:`geo_dashboard_creation=${token}`}}));assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);assert.equal(response.headers.get('Content-Type'),'image/png');
});
