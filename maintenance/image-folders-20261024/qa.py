import asyncio,io,json,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
from playwright.async_api import async_playwright,expect
D=Path('/tmp/image-folders-20261024');C=D/'candidate';sys.path[:0]=[str(C),'/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials,knowledge_library as lib,product_images
async def main():
 errors=[];calls=[];fault={'lost':False};gate=asyncio.Event();gate.set()
 with tempfile.TemporaryDirectory() as tmp:
  T=Path(tmp)
  with patch.object(runtime,'BASE',T/'runtime'),patch.object(runtime,'SHARED',T/'shared'),patch.object(studio,'ROOT',T/'studio'),patch.object(materials,'ROOT',T/'materials'),patch.object(materials,'GEO',T/'geo'):
   runtime.atomic_json(materials.GEO/'daily_plan.json',{'time':'05:00'})
   old=studio.save_product({'name':'原有产品','facts':['规格100ml']})
   buf=io.BytesIO()
   with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>测试产品，规格200ml。</w:t></w:r></w:p></w:body></w:document>')
   async with async_playwright() as pw:
    browser=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
    page=await browser.new_page(viewport={'width':1366,'height':950});page.on('pageerror',lambda e:errors.append(str(e)))
    async def route(r):
     path=r.request.url.split('library.test',1)[1].split('?',1)[0]
     if path=='/':return await r.fulfill(content_type='text/html',body=(C/'creation/panel.html').read_text())
     if path=='/api/product_image':
      from urllib.parse import parse_qs,urlsplit
      body,mime=product_images.read(parse_qs(urlsplit(r.request.url).query)['id'][0]);return await r.fulfill(content_type=mime,body=body)
     if path=='/api/panel':value={**runtime.status(),'csrf':'a'*64}
     elif path=='/api/catalog':value={'dedicated':{'dates':[],'questions':[],'channels':[]},'product':{},'geo':{'dates':[],'questions':[],'channels':[]}}
     elif path.startswith('/api/control/'):
      calls.append(path);await gate.wait()
      try:value={'ok':True,'result':runtime.action(path.rsplit('/',1)[1],r.request.post_data_json,r.request.headers['x-action-id'])}
      except ValueError as e:return await r.fulfill(status=400,json={'ok':False,'message':str(e)})
      if fault['lost'] and path.endswith('product_image_upload'):
       fault['lost']=False;return await r.abort('failed')
     else:return await r.abort()
     await r.fulfill(json=value)
    await page.route('http://library.test/**',route);await page.goto('http://library.test/');await expect(page.locator('#connection')).to_contain_text('已连接')
    await page.locator('[data-view="knowledge"]').click();await expect(page.locator('#libraryUpload')).to_be_disabled()
    from PIL import Image
    imagebuf=io.BytesIO();Image.new('RGB',(64,80),'green').save(imagebuf,format='PNG')
    await page.locator('#libraryTarget').select_option('product:'+old['product_id'])
    await page.locator('#productImageFile').set_input_files({'name':'产品图.png','mimeType':'image/png','buffer':imagebuf.getvalue()})
    gate.clear();await page.locator('#productImageUpload').click();await expect(page.locator('#productImageUpload')).to_be_disabled();await expect(page.locator('#productImageFeedback')).to_contain_text('上传');gate.set()
    await expect(page.locator('#productImageFeedback')).to_contain_text('已上传');await expect(page.locator('.product-image-list img')).to_be_visible()
    assert await page.locator('.product-image-list img').evaluate('(i)=>i.complete&&i.naturalWidth===64')
    assert product_images.read(product_images.images()[0]['image_id'])[0]==imagebuf.getvalue()
    await page.reload();await expect(page.locator('#connection')).to_contain_text('已连接');await page.locator('[data-view="knowledge"]').click();await expect(page.locator('.product-image-list img')).to_be_visible()
    await page.screenshot(path=str(D/'images-desktop.png'),full_page=True)
    await page.locator('#libraryTarget').select_option('')
    await page.locator('#libraryName').fill('新测试产品');await page.locator('#libraryNotes').fill('首次上传')
    await page.locator('#libraryWord').set_input_files({'name':'产品资料.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()})
    gate.clear();await page.locator('#libraryUpload').click();await expect(page.locator('#libraryUpload')).to_be_disabled();await expect(page.locator('#libraryFeedback')).to_contain_text('保存原文件')
    gate.set();await expect(page.locator('#libraryFeedback')).to_contain_text('等待人工分析');await expect(page.locator('#knowledgeRows')).to_contain_text('新测试产品')
    assert len(studio.products())==1 and len(lib.records())==1
    await page.reload();await expect(page.locator('#connection')).to_contain_text('已连接');await page.locator('[data-view="knowledge"]').click();await expect(page.locator('#knowledgeRows')).to_contain_text('待人工分析')
    r=lib.records()[0];u=r['uploads'][0]
    result=lib.publish({'library_id':r['library_id'],'import_id':u['import_id'],'reviewer':'验收人工分析','product':{'name':'新测试产品','brand':'测试品牌','facts':['规格200ml']}})
    await page.evaluate('refresh()');await expect(page.locator('[data-library-use="'+result['product_id']+'"]')).to_be_visible()
    await page.locator('[data-library-use="'+result['product_id']+'"] ').click();await expect(page.locator('#dailyPlan')).to_be_visible();assert await page.locator('#planProduct').input_value()==result['product_id']
    assert not any('kb_save' in c for c in calls)
    await page.locator('[data-view="knowledge"]').click();await page.locator('[data-library-update="product:'+result['product_id']+'"]').click()
    await page.locator('#libraryWord').set_input_files({'name':'产品新版.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':buf.getvalue()});await page.locator('#libraryUpload').click()
    await expect(page.locator('#knowledgeRows')).to_contain_text('新版待分析');assert studio.product(result['product_id'])['version']==result['version']
    await page.locator('[data-library-edit="'+result['product_id']+'"]').click();await page.locator('#libraryEditFacts').fill('规格250ml');await page.locator('#libraryEditSave').click();await expect(page.locator('#libraryEditor')).to_be_hidden()
    assert studio.product(result['product_id'])['product']['facts'][0]['text']=='规格250ml'
    await page.locator('#librarySearch').fill('新测试产品');await page.locator('#knowledgeRows details').first.evaluate('(e)=>e.open=true');await page.screenshot(path=str(D/'library-desktop.png'),full_page=True)
    await page.set_viewport_size({'width':390,'height':844});await page.screenshot(path=str(D/'library-mobile.png'),full_page=True)
    await page.locator('[data-library-use="'+result['product_id']+'"]').click();await page.get_by_role('button',name='上一步',exact=True).first.click();await expect(page.locator('#selectedKnowledge')).to_contain_text('新测试产品');await expect(page.locator('#kbWord')).to_be_hidden();await page.screenshot(path=str(D/'task-select.png'),full_page=True)
    await page.locator('[data-view="knowledge"]').click();await page.locator('#libraryTarget').select_option('product:'+old['product_id'])
    folder=T/'照片文件夹';(folder/'子目录').mkdir(parents=True)
    (folder/'A.png').write_bytes(imagebuf.getvalue());(folder/'子目录/B.png').write_bytes(imagebuf.getvalue());(folder/'损坏.jpg').write_bytes(b'not an image');(folder/'说明.txt').write_text('skip me');(folder/'过大.jpg').write_bytes(b'x'*(6*1024*1024))
    await page.locator('#productImageFolder').set_input_files(str(folder));await expect(page.locator('#imageBatchSelection')).to_contain_text('3 张可上传图片，跳过 2')
    fault['lost']=True;await page.locator('#productImageUpload').click();await expect(page.locator('#imageBatchRetry')).to_be_visible();await expect(page.locator('#imageBatchProgress')).to_contain_text('结果待核对');assert len(product_images.images())==2
    await page.locator('#imageBatchRetry').click();await expect(page.locator('#productImageFeedback')).to_contain_text('2 张图片，1 张失败');await expect(page.locator('#imageBatchProgress')).to_contain_text('子目录/B.png');assert len(product_images.images())==3
    await page.locator('#productImageUpload').click();await expect(page.locator('#productImageFeedback')).to_contain_text('2 张图片，1 张失败');assert len(product_images.images())==3
    await page.screenshot(path=str(D/'folder-result.png'),full_page=True)
    assert not errors,errors;report={'success':True,'checks':['upload pending without analysis','reload retains uploads','manual publish makes product selectable','selection skips upload and save','update retains current version','manual edits persist','desktop and mobile','no browser errors'],'calls':calls}
    (D/'qa.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));await browser.close()
asyncio.run(main())
