# 豆包工具与历史证据

2026-10-15已清理早期Android NDK镜像下载tar及重复OCI blobs，保留镜像原始manifest、固定digest和清理前SHA256；对应旧镜像仍安装在服务器。生产使用Android13/Houdini14，不依赖本地下载缓存。

| 内容 | 用途 |
|---|---|
| `platform-tools/`、`scrcpy/` | 本地临时登录、ADB诊断所需工具，保留 |
| `doubao.apk` | 官方APK备份，保留 |
| `houdini-hpe14.tar.gz`及Houdini元数据 | 兼容修复和重建资料，保留 |
| `frida-server.xz`、`frida-server16.xz` | 不同版本诊断工具；与xz完全相同的裸`frida-server`已去重，可按需解压 |
| `headless-*`、`verified-*`、截图、XML、JSON、原始崩溃日志 | 采集与故障证据，保留 |
| `tunnel-error.log`、`tunnel-15558-error.log` | 原位置保留最后64KiB；完整历史日志另有已校验压缩副本 |

完整隧道日志位于`../../geo-monitor-deploy/maintenance/20261015/*.log.gz`。历史错误日志清理前分别约1.37GB和333MB，完整内容未丢失。

旧镜像缓存的身份、清理记录和恢复方法见[清理报告](../../geo-monitor-deploy/maintenance/20261015/CLEANUP_REPORT.md)。`fetch_image.py`可重新下载；需要原版本时应按记录的digest或服务器保留镜像导出，不依赖可变化的tag。
