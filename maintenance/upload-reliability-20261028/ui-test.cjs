const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),http=require('http'),assert=require('assert/strict'),path=require('path');
const html=fs.readFileSync(path.resolve('geo-monitor-deploy/creation/panel.html'),'utf8');
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=','base64');
const product={product_id:'product-'+'a'.repeat(32),version:'one',updated_at:1,product:{name:'上传验收产品',brand:'测试',facts:[{text:'测试'}]}};
const images=[],calls=[],attempts=new Map();let active=0,maxActive=0;
const studio=()=>({products:[product],knowledge_library:[],product_images:images,plans:[],daily_tasks:[],today:'2026-10-28'});
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost');
 const send=(value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(value))};
 if(url.pathname==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});return res.end(html)}
 if(url.pathname==='/api/uploads')return send({ok:true,csrf:'a'.repeat(64),studio:studio(),at:Date.now()/1000});
 if(url.pathname==='/api/panel')return send({ok:true,csrf:'a'.repeat(64),studio:studio(),at:Date.now()/1000,jobs:[],legacy_articles:[],settings:{article_budget_cny:1,daily_budget_cny:30},materials:{settings:{questions:[]}}});
 if(url.pathname==='/api/catalog')return send({ok:true,product:{},dates:[],questions:[],channels:[]});
 if(url.pathname==='/api/product_image'){res.writeHead(200,{'Content-Type':'image/png'});return res.end(png)}
 if(url.pathname==='/api/control/product_image_upload'){
  const chunks=[];for await(const c of req)chunks.push(c);const payload=JSON.parse(Buffer.concat(chunks));const key=req.headers['x-action-id'];calls.push({key,name:payload.filename});
  const attempt=(attempts.get(key)||0)+1;attempts.set(key,attempt);active++;maxActive=Math.max(maxActive,active);
  await new Promise(r=>setTimeout(r,150));active--;
  if(payload.filename==='bad.png')return send({ok:false,message:'损坏图片'},400);
  let image=images.find(i=>i.filename===payload.filename);const reused=!!image;
  if(!image){image={image_id:'image-'+String(images.length+1).padStart(32,'0'),product_id:product.product_id,library_id:'',filename:payload.filename,bytes:png.length,width:1,height:1,uploaded_at:1};images.push(image)}
  // Persist succeeds, response vanishes: a retry must retain the original key.
  if(payload.filename==='lost.png'&&attempt===1){res.destroy();return}
  return send({ok:true,result:{image_id:image.image_id,image,reused,message:reused?'复用原图':'图片已保存'}});
 }
 return send({ok:false,message:'missing'},404);
});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const ctx=await browser.newContext({viewport:{width:1360,height:1000}}),page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.locator('[data-view="knowledge"]').click();await page.selectOption('#productImageTarget','product:'+product.product_id);
  await page.locator('#productImageFile').setInputFiles(['one.png','two.png','lost.png','bad.png'].map(name=>({name,mimeType:'image/png',buffer:png})));
  assert.equal(await page.locator('#imageQueueGrid img').count(),4);
  await page.locator('#productImageUpload').click();
  await page.waitForFunction(()=>!imageBatchActive&&imageBatchQueue.filter(i=>i.status==='done').length===3);
  assert.equal(await page.locator('#savedProductImages img').count(),3);assert.equal(await page.locator('#imageQueueGrid [data-state="failed"]').count(),1);
  const lost=calls.filter(c=>c.name==='lost.png');assert.equal(lost.length,2);assert.equal(new Set(lost.map(c=>c.key)).size,1);assert.equal(maxActive,3);
  const before=calls.length;await page.locator('#imageQueueGrid .upload-retry:visible').click();await page.waitForFunction(()=>!imageBatchActive);assert.equal(calls.length,before+1);assert.equal(calls.at(-1).name,'bad.png');
  await page.locator('#productImageFile').setInputFiles({name:'resume.png',mimeType:'image/png',buffer:png});
  await page.waitForFunction(async()=>{const db=await uploadDB();return await new Promise(resolve=>{const r=db.transaction('queue').objectStore('queue').getAll();r.onsuccess=()=>resolve(r.result.some(i=>i.path==='resume.png'))})});
  await page.reload();await page.locator('[data-view="knowledge"]').click();await page.waitForFunction(()=>imageBatchQueue.some(i=>i.path==='resume.png'));
  assert.ok(await page.locator('#imageQueueGrid img').count()>=2);
  await page.selectOption('#productImageTarget','product:'+product.product_id);
  await page.locator('#productImageUpload').click();await page.waitForFunction(()=>!imageBatchActive&&imageBatchQueue.some(i=>i.path==='resume.png'&&i.status==='done'));
  await page.locator('#productImageBox').screenshot({path:path.join(__dirname,'upload-desktop.png')});
  await page.setViewportSize({width:390,height:844});await page.locator('#productImageBox').screenshot({path:path.join(__dirname,'upload-mobile.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['all previews','3 concurrent requests','lost response same ID','individual retry','saved gallery immediate','reload recovery','mobile no horizontal overflow'],maxActive,errors}));
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});
