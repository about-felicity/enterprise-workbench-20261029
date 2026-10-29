const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('assert/strict'),path=require('path'),fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const context=await browser.newContext({viewport:{width:1360,height:1000}}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://192.168.31.106:3000/api/geo-creation/ui');
  await page.locator('[data-view="knowledge"]').click();
  await page.waitForFunction(()=>data?.studio?.knowledge_library?.length===20);
  await page.selectOption('#productImageTarget','product-8aef16cc9c3d4e68a94b81911b14a47c'.replace('product-','product:product-'));
  await page.waitForFunction(()=>document.querySelectorAll('#savedProductImages img').length===8&&[...document.querySelectorAll('#savedProductImages img')].every(i=>i.complete&&i.naturalWidth>0));
  assert.equal(await page.locator('#knowledgeRows>article').count(),20);
  await page.locator('#refreshProductImages').click();await page.waitForFunction(()=>!uploadRefreshPromise);
  await page.locator('#productImageBox').screenshot({path:path.join(__dirname,'production-desktop.png')});
  await page.setViewportSize({width:390,height:844});await page.locator('#productImageBox').screenshot({path:path.join(__dirname,'production-mobile.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  assert.deepEqual(errors,[]);
  const result={ok:true,knowledge_cards:20,selected_product_images:8,all_images_loaded:true,desktop_mobile_verified:true,errors};
  fs.writeFileSync(path.join(__dirname,'production-ui.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
