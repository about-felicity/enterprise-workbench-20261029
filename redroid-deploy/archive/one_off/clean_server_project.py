"""Archive explicitly reviewed obsolete files without restarting any service."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import datetime, json, os, pathlib, subprocess, tarfile, pwd

root=pathlib.Path('/home/user/redroid-doubao').resolve()
assert root==pathlib.Path('/home/user/redroid-doubao') and root.is_dir()
source_files=['.gitignore','README.md','HPE14_FIX.md','UNATTENDED.md','PROJECT_TREE.md',
 'requirements.txt','compose.hpe14.yaml','runtime_preflight.py','unattended_core.py',
 'unattended_worker.py','test_unattended.py','soak_monitor.py','hpe14_report.py',
 'package_hpe14_results.py','backup_hpe14_release.py','backup_android13_volume.py',
 'redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service',
 'redroid-doubao-soak24h.service','hpe14-questions.json','hpe14-soak-questions.json']
keep=set(source_files+['backups','hpe14-acceptance','hpe14-export','linux-tools',
 'worker-venv','soak24h','soak-smoke','__pycache__'])
obsolete='''acceptance-audit acceptance-live acceptance_snapshot.py apk-download.log apk-speed-test.bin
artifacts audit_messages.py build_hpe14_13.py build_hpe14_test.py chat-store-snapshot check-host.sh
check_image_backup.py compose.android15.yaml compose.houdini13.yaml compose.ndk.yaml compose.yaml
deploy.log deploy.sh device-lock-smoke doubao.apk export_chat_store.py fetch_image.py
fix_hpe_namespace.py get-pip.py houdini-anr.log houdini-hpe14.tar.gz houdini-logcat.log
hpe13-app-before-migration hpe14-13-screen.xml hpe14-build hpe14-startup.json image-sources.json
image-speed-test.bin inspect_chat_store.py inspect_prepared.py install_worker_runtime.py
loop-questions.json migrate_test_app.py offline-download.log platform-tools-linux.zip
probe_hpe14_13.py probe_hpe14.py PROJECT_GUIDE.md pull-android15.log README.before-hpe14.md
read_send_faults.py redroid-doubao-worker.service services-before.txt store-results.json
test-android15.sh test_phase_recovery_live.py test_questions.json test-report.md
transfer-test-0.bin transfer-test-1.bin transfer-test-2.bin transfer-test-3.bin transfer-test.bin
transfer-tuned-test.bin unattended-acceptance.json UNATTENDED.before-hpe14.md watchdog_smoke.py'''.split()
unknown={p.name for p in root.iterdir()}-keep-set(obsolete)
assert not unknown, f'Unreviewed entries: {sorted(unknown)}'
assert all((root/name).is_file() for name in source_files if name!='PROJECT_TREE.md')
units=['redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service','redroid-doubao-soak24h.service']
def state():
 return subprocess.check_output(['systemctl','show',*units,'-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
before=state()
assert before.count('ActiveState=active')==3
archive=pathlib.Path('/home/user/redroid-doubao-archive')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-utc')
archive.mkdir(parents=True,mode=0o700)
archive.parent.chmod(0o700)
plan=[name for name in obsolete if (root/name).exists()]
manifest={'project':str(root),'archive':str(archive),'moved_entries':plan,'services_before':before}
(archive/'cleanup-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(archive/'cleanup-manifest.json').chmod(0o600)
for name in plan:
 path=root/name
 assert path.parent.resolve()==root and not path.is_symlink()
 destination=archive/name
 assert destination.parent.resolve()==archive.resolve() and not destination.exists()
 os.rename(path,destination)
after=state()
manifest['services_after']=after
manifest['same_service_pids']=before==after
(archive/'cleanup-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
assert before==after, 'Service state changed during cleanup; examine manifest'
tree='\n'.join(('└── ' if i==len(source_files)-1 else '├── ')+name for i,name in enumerate(source_files))
runtime='\n'.join('├── '+name+'/' for name in ['hpe14-acceptance','hpe14-export','soak24h','soak-smoke','backups','linux-tools','worker-venv','__pycache__'])
doc=f'''# 当前项目完整源码文件树

整理日期：2026-10-07。源码、配置和文档文件完整列出如下；不包含运行数据或第三方依赖。

```text
redroid-doubao/
{tree}
```

服务器上还保留以下必需运行目录，纯净源码包不包含它们：

```text
{root}/
{runtime}
```

`hpe14-acceptance` 是当前队列、结果、故障日志及截图；`soak24h` 是正在运行的长测；
`soak-smoke` 保留重启后验证证据；`backups` 保存镜像、登录数据和一致性队列备份。
`linux-tools` 和 `worker-venv` 是 ADB 与 Python 依赖；`__pycache__` 是 Python 自动生成的缓存。
Android 实时登录数据位于 Docker 卷 `doubao-hpe14-android13-data`，不在项目源码中。

历史实验、诊断与下载中间产物已归档到 `{archive}`，移动清单是该目录的 `cleanup-manifest.json`。
此次整理未重启模拟器、worker、日志或长测服务。归档是可恢复的移动，不释放磁盘空间。

纯净源码包：`/home/user/redroid-doubao-source.tar.gz`。
恢复到新服务器还需要安装依赖、加载已验证镜像、恢复数据卷并按 HPE14_FIX.md 配置服务。
'''
(root/'PROJECT_TREE.md').write_text(doc,encoding='utf8')
bundle=pathlib.Path('/home/user/redroid-doubao-source.tar.gz')
with tarfile.open(bundle,'w:gz') as tar:
 for name in source_files:tar.add(root/name,arcname='redroid-doubao/'+name,recursive=False)
user=pwd.getpwnam('user')
os.chown(bundle,user.pw_uid,user.pw_gid);bundle.chmod(0o600)
print(json.dumps({'archive':str(archive),'archived_entries':len(plan),'source_files':len(source_files),'same_service_pids':before==after,'bundle':str(bundle)},ensure_ascii=False))
