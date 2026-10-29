"""Create reviewable non-secret source bundle with explicit deployment mappings."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
workspace=Path.cwd().resolve();release=workspace/'geo-monitor-deploy/releases/20261015/unified-current'
release.mkdir(parents=True,exist_ok=True)
mapping={}
mapping['deepseek-deploy/auth_policy.py']='/home/user/redroid-deepseek/code/auth_policy.py'
mapping['redroid-deploy/artifacts/scrcpy/scrcpy-win64-v5.0/scrcpy-server']='/opt/monitor/geo-capture/vendor/scrcpy-server-v5.0'
mapping['redroid-deploy/artifacts/scrcpy/scrcpy-win64-v5.0/LICENSE.txt']='/opt/monitor/geo-capture/vendor/SCRCPY-LICENSE.txt'
for name in ['scrcpy_stream.py','deepseek_auth_monitor.py','deepseek_test_auth.py']:
    mapping['geo-monitor-deploy/'+name]='/opt/monitor/geo-capture/'+name
for name in ['geo-deepseek-auth-check.service','geo-deepseek-auth-check.timer']:
    mapping['geo-monitor-deploy/systemd/'+name]='/etc/systemd/system/'+name
for name in ['device.py','android.py','reader.py','worker.py','delivery.py','policy.py','private_capture.py']:
    mapping['deepseek-deploy/'+name]='/home/user/redroid-deepseek/code/'+name
for name in ['device.py','worker.py','delivery.py']:
    mapping['deepseek-deploy/account2/'+name]='/home/user/redroid-deepseek-account2/code/'+name
for name in ['question_only_core.py','question_only_adapters.py','question_only_delivery.py','question_only_worker.py','native_readback_guard.py','native_memory_guard.py']:
    mapping['redroid-deploy/'+name]='/home/user/redroid-doubao/geo-batch-code/'+name
mapping['redroid-deploy/unattended_core.py']='/home/user/redroid-doubao/geo-batch-code/unattended_core.py'
mapping['redroid-deploy/geo_batch_bridge.py']='/home/user/redroid-doubao/geo-batch-code/geo_batch_bridge.py'
mapping['yuanbao-deploy/delivery.py']='/home/user/redroid-yuanbao/delivery.py'
mapping['yuanbao-deploy/android_ui.py']='/home/user/redroid-yuanbao/android_ui.py'
for name in ['native_core.py','native_client.py','native_models.js','binding_recovery.py','history_refresh.py']:mapping['yuanbao-deploy/'+name]='/home/user/redroid-yuanbao/'+name
for name in ['test_native_core.py','test_binding_recovery.py','test_history_refresh.py','test_native_client_recovery.py']:mapping['yuanbao-deploy/tests/'+name]='/home/user/redroid-yuanbao/tests/'+name
for name in ['control_panel.py','native_entry.py','panel.html','all_channel_soak.py','capture_bridge.py','runtime_reliability.py','baidu_body_delivery.py','fleet_status.py','manual_login.py','deepseek_login_ui.py','deepseek_android_login.py','deepseek_login.html','login_probe.py','daily_dispatch.py','daily_tasks.py','schedule_control.py']:
    mapping['geo-monitor-deploy/'+name]='/opt/monitor/geo-capture/'+name
mapping['geo-monitor-deploy/server-source/doubao_dashboard_server.py']='/opt/monitor/doubao_dashboard_server.py'
mapping['geo-monitor-deploy/server-source/monitor_core/source_activity_index.py']='/opt/monitor/monitor_core/source_activity_index.py'
for name in ['monitor_core/native_text.py','monitor_core/ingestion.py','monitor_core/owned_products.py','monitor_core/product_analysis.py','monitor_core/analytics.py','save_doubao_refs.py']:
    mapping['geo-monitor-deploy/server-source/'+name]='/opt/monitor/'+name
mapping['geo-monitor-deploy/server-source/model_plugins/doubao/plugin.py']='/opt/monitor/model_plugins/doubao/plugin.py'
for name in ['web_collectors/collector.py','web_collectors/browser.py','web_collectors/session_store.py','wenxin_monitor/controller.py']:
    mapping['geo-source-card-collectors/'+name]='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/'+name
mapping['geo-source-card-collectors/geo_source_cards/journal.py']='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/journal.py'
mapping['geo-source-card-collectors/geo_source_cards/search_recovery.py']='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/search_recovery.py'
for name in ['geo-daily-dispatch.service','geo-daily-dispatch.timer','geo-daily-control.service','geo-creation-materials.service','geo-creation-studio.service','geo-project-observe.service','geo-project-observe.timer']:
    mapping['geo-monitor-deploy/systemd/'+name]='/etc/systemd/system/'+name
mapping['geo-monitor-deploy/systemd/20-unattended.conf']='/etc/systemd/system/geo-web@.service.d/20-unattended.conf'
mapping['geo-monitor-deploy/systemd/30-schedule.conf']='/etc/systemd/system/geo-daily-dispatch.timer.d/30-schedule.conf'
mapping['geo-monitor-deploy/systemd/40-deepseek-android.conf']='/etc/systemd/system/geo-capture-deepseek.service.d/40-deepseek-android.conf'
for name in ['daily_plan.json','unattended_policy.json','deepseek_backend.json','native_memory_policy.json']:
    mapping['geo-monitor-deploy/config/'+name]='/opt/monitor/geo-capture/'+name
mapping['geo-monitor-deploy/config/creation_materials.json']='/opt/monitor/geo-content/materials/settings.json'
mapping['geo-monitor-deploy/config/creation_search_pool.json']='/opt/monitor/geo-content/creation_search_pool.json'
mapping['geo-source-card-collectors/geo_source_cards/cli.py']='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py'
mapping['geo-source-card-collectors/geo_source_cards/reference_design.py']='/opt/monitor/geo-content/engine/geo_source_cards/reference_design.py'
for name in ['api_budget.py','deepseek_api.py','article_logic.py','product_richness.py','product_identity.py','daily_editorial.py','genre_outline.py','genre_length.py','genre_prompts.py','article_allocation.py','article_quality.py','genre_pools.py','source_scope.py','word_export.py','api_worker.py','append_repair.py','auto_repair.py','consumer_voice.py','consumer_prompts.py','api_prompts.py','reference_prompts.py','staged_editorial.py']:
    mapping['geo-source-card-collectors/geo_source_cards/'+name]='/opt/monitor/geo-content/engine/geo_source_cards/'+name
for path in (workspace/'geo-monitor-deploy/creation').iterdir():
    if path.suffix in {'.py','.html','.md','.js'}:mapping[str(path.relative_to(workspace)).replace('\\','/')]=str(Path('/opt/monitor/geo-content/creation')/path.name).replace('\\','/')
for path in (workspace/'geo-monitor-deploy/dashboard-integration/app').rglob('*'):
    if path.is_file():mapping[str(path.relative_to(workspace)).replace('\\','/')]=str(Path('/opt/monitor/yuanbao_monitor/dashboard/app')/path.relative_to(workspace/'geo-monitor-deploy/dashboard-integration/app')).replace('\\','/')
for name in ['browser_backend.py','browser_task_bridge.py']:
    mapping['deepseek-browser-deploy/'+name]='/opt/monitor/geo-capture/'+name
for name in ['browser_test.py','auth_probe.js','login.html']:
    mapping['deepseek-browser-deploy/'+name]='/opt/monitor/geo-deepseek-browser-test/'+name
for path in (workspace/'deepseek-browser-deploy/project/extension').iterdir():
    if path.is_file():mapping[str(path.relative_to(workspace)).replace('\\','/') ]='/opt/monitor/geo-deepseek-browser-test/project/extension/'+path.name
for name in ['local_receiver.py','remote_sync.py']:
    mapping['deepseek-browser-deploy/project/'+name]='/opt/monitor/geo-deepseek-browser-test/project/'+name
manifest=[]
with zipfile.ZipFile(release/'source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for relative,target in mapping.items():
        source=workspace/relative;data=source.read_bytes()
        archive.writestr(relative,data)
        manifest.append({'source':relative,'server':target,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    for name in ['android.py','reader.py','policy.py']:
        shared='deepseek-deploy/'+name;data=(workspace/shared).read_bytes()
        manifest.append({'source':shared,'server':'/home/user/redroid-deepseek-account2/code/'+name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    shared='deepseek-deploy/auth_policy.py';data=(workspace/shared).read_bytes()
    manifest.append({'source':shared,'server':'/home/user/redroid-deepseek-account2/code/auth_policy.py','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    shared='geo-monitor-deploy/runtime_reliability.py';data=(workspace/shared).read_bytes()
    for target in ['/home/user/redroid-doubao/geo-batch-code/runtime_reliability.py','/home/user/redroid-yuanbao/runtime_reliability.py']:
        manifest.append({'source':shared,'server':target,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    shared='geo-monitor-deploy/systemd/20-unattended.conf';data=(workspace/shared).read_bytes()
    manifest.append({'source':shared,'server':'/etc/systemd/system/geo-native@.service.d/20-unattended.conf','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(release/'manifest.json').write_text(json.dumps({'scope':'Current non-secret changed runtime source; not a blind installer. Original creation engine snapshot and protected private configs remain on server.','files':manifest,'zip_sha256':hashlib.sha256((release/'source.zip').read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf8')
(release/'README.md').write_text('# 当前源码恢复映射\n\nsource.zip只包含本轮当前运行模块，不含凭据、数据、队列、登录或旧引擎私有输入。逐文件按manifest.json核对，先备份再针对组件部署并验证；前端须重新构建及预览，不能直接覆盖运行容器。不要运行旧现场恢复脚本，也不要覆盖原完整内容引擎或预算账本。长测期间避免无关重启；修改后记录实际复测窗口。\n',encoding='utf8')
print(json.dumps({'files':len(manifest),'release':str(release),'bytes':(release/'source.zip').stat().st_size}))
