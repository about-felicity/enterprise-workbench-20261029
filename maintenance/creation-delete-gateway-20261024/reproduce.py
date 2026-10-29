import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
D=Path('/tmp/creation-delete-gateway-20261024');D.mkdir(exist_ok=True)
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1366,'height':950})
 page.goto('http://127.0.0.1:3000/#creation')
 f=page.frame_locator('iframe[title="GEO 内容创作控制台"]')
 expect(f.locator('#connection')).to_contain_text('已连接',timeout=30000)
 f.locator('[data-delete-plan]').last.click()
 box=f.locator('#deleteDialog').bounding_box()
 page.screenshot(path=str(D/'before.png'))
 # Invalid ID: route reachability only, never deletes a task.
 response=page.request.post('http://127.0.0.1:3000/api/geo-creation/control/plan_delete',data={'plan_id':'nonexistent-diagnostic'},headers={'Origin':'http://127.0.0.1:3000','Content-Type':'application/json','X-CSRF-Token':'a'*64,'X-Action-Id':'b'*32})
 result={'dialog_bounds':box,'viewport_height':950,'dialog_outside_visible_viewport':box['y']+box['height']<0 or box['y']>950,'delete_http_status':response.status,'delete_response':response.json()}
 (D/'before.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
 b.close()
