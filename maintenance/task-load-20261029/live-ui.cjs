const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),assert=require('assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[],samples=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('/api/geo-creation/'))requests.push(new URL(r.url()).pathname.split('/').pop())});
  for(let i=0;i<3;i++){
   const start=Date.now();await page.goto('http://192.168.31.106:3000/api/geo-creation/ui',{waitUntil:'domcontentloaded'});
   await page.waitForSelector('#planQueue [data-task-status]',{timeout:30000});
   await page.waitForFunction(()=>document.querySelector('#taskLiveNotice')?.dataset.stale==='false');
   samples.push((Date.now()-start)/1000);
  }
  assert.ok(!requests.includes('panel')&&!requests.includes('uploads')&&!requests.includes('catalog'),JSON.stringify(requests));
  const cards=await page.locator('#planQueue .queue-item').count();assert.ok(cards>0);assert.equal(cards,await page.locator('#planQueue [data-task-status]').count());
  const previous=await page.locator('#taskLiveNotice').textContent();
  await page.waitForFunction(old=>document.querySelector('#taskLiveNotice').textContent!==old,previous,{timeout:15000});
  await page.screenshot({path:'maintenance/task-load-20261029/live-desktop.png',fullPage:true});
  await page.locator('#planQueue [data-edit-plan]').first().click();
  await page.waitForSelector('[data-workspace="editor"]:visible',{timeout:30000});
  await page.waitForFunction(()=>document.querySelector('#kbFacts').value.length>0);
  const editorFacts=(await page.locator('#kbFacts').inputValue()).length;assert.ok(editorFacts>10);
  await page.evaluate(()=>showView('outputs',false));
  await page.waitForSelector('#library .output',{timeout:45000});const articles=await page.locator('#library .output').count();assert.ok(articles>0);
  await page.evaluate(()=>showView('knowledge',false));await page.waitForSelector('#knowledgeRows .card',{timeout:20000});
  const knowledge=await page.locator('#knowledgeRows .card').count();assert.ok(knowledge>0);
  assert.deepEqual(errors,[]);
  const result={ok:true,task_first_render_seconds:samples,cards,automatic_refresh:true,lazy_editor_facts_length:editorFacts,articles,knowledge,errors};
  fs.writeFileSync('maintenance/task-load-20261029/live-ui.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
