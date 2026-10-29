import asyncio,io,json,shutil,sys,uuid
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright,expect
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,product_images
D=Path('/tmp/product-images-20261024')
async def main():
 name='图片入口验收-'+uuid.uuid4().hex+'.png';ident=None;errors=[]
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox']);p=await b.new_page(viewport={'width':1366,'height':950});p.on('pageerror',lambda e:errors.append(str(e)))
  try:
   await p.goto('http://127.0.0.1:3000/#creation');f=p.frame_locator('iframe[title="GEO 内容创作控制台"]');await expect(f.locator('#connection')).to_contain_text('已连接',timeout=30000);await f.locator('[data-view="knowledge"]').click()
   await f.locator('#libraryTarget').select_option('product:'+studio.products()[0]['product_id'])
   buf=io.BytesIO();Image.new('RGB',(64,80),'green').save(buf,format='PNG')
   await f.locator('#productImageFile').set_input_files({'name':name,'mimeType':'image/png','buffer':buf.getvalue()});await expect(f.locator('#productImagePreview')).to_be_visible();await f.locator('#productImageUpload').click()
   await expect(f.locator('#productImageFeedback')).to_contain_text('已上传',timeout=20000)
   meta=next(i for i in product_images.images() if i['filename']==name);ident=meta['image_id'];image=f.locator('img[src$="'+ident+'"]');await expect(image).to_be_visible();assert await image.evaluate('(e)=>e.complete&&e.naturalWidth===64')
   response=await p.request.get('http://127.0.0.1:3000/api/geo-creation/product_image?id='+ident);assert response.ok and await response.body()==buf.getvalue()
   await p.reload();await expect(f.locator('#connection')).to_contain_text('已连接');await f.locator('[data-view="knowledge"]').click();await expect(image).to_have_count(1)
   await f.locator('#productImageBox').scroll_into_view_if_needed();await p.screenshot(path=str(D/'live-desktop.png'))
   await p.set_viewport_size({'width':390,'height':844});await f.locator('#productImageBox').scroll_into_view_if_needed();await p.screenshot(path=str(D/'live-mobile.png'))
   assert not errors,errors
   report={'success':True,'actual_gateway_upload':True,'exact_image_bytes':True,'reload_persistence':True,'metadata':{'width':meta['width'],'height':meta['height'],'uploaded_at':meta['uploaded_at']},'browser_errors':errors,'test_image_removed':True}
  finally:
   if ident:
    studio.identity(ident,'image');folder=studio.ROOT/'images'/ident;assert json.loads((folder/'metadata.json').read_text())['filename']==name;shutil.rmtree(folder)
   await b.close()
  (D/'live-result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
asyncio.run(main())
