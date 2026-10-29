# 无人值守运行与验收

更新：2026-10-07。底层环境已改为 Android13 + Houdini14 com1.3，Linux 常驻服务已启用。
106 题真实 App 采集已通过，得到 1,095 条信源、300 处正文引用；模拟器重启、发送途中重启 worker、不同队列的设备互斥测试已通过。
30 项 Linux 故障测试全部通过。24 小时测试是独立验收，状态在 Linux `soak24h/status.json`。
原每 10 分钟一题长测已按用户要求停止并归档。北京时间 2026-10-07 10:20:22 启动 1 小时短测，每 3 分钟一题，共 20 题；通过后自动执行同频率的 24 小时长测（480 题）。短测状态为 `soak1h/status.json`，阶段状态为 `soak1h/sequence.json`；失败时不启动下一阶段。备份后额外两题冒烟通过，隔夜约 13.5 小时未记录原生崩溃。

当前架构、日常操作、扩展与故障修复见 [HPE14_FIX.md](HPE14_FIX.md)。
旧 NDK 失败验收保留在 `UNATTENDED.before-hpe14.md` 和 `test-results/unattended-acceptance.json`。

## 正确性规则

1. 批次和题号生成稳定唯一编号，实际发送文本附带编号，区分不同轮次的同题。
2. 发送前持久提交发送意图，点击前再记录点击意图；重启核对 App 请求，仅能证明未尝试点击时续行原发送操作。
3. 只匹配用户请求角色；答案必须同会话、位于请求之后与下一条用户消息之前。多个候选拒绝猜测。
4. 正文非空、全部块完成标记为 true 才成功；未知 schema 或内容块显式失败。
5. 要求来源的任务必须有有效 HTTP(S) 来源，正文引用要能关联提取文档；重复来源保留原编号。
6. SQLite 事务提交成功后才导出；文件使用 fsync 和原子替换。截图只是辅助证据。
7. 队列目录锁和设备锁共同限制单 worker 操作一个模拟器，包括不同状态目录。

规则检查采集归属和完整性，不独立审核模型事实或逐条验证网页可访问性。

## 状态与恢复

```text
pending → prepared → completed
pending → 三次就绪失败 → needs_attention
prepared → 超时 / 消息歧义 / 数据异常 → needs_attention
```

`prepared` 表示发送意图已落盘，不代表已收到服务端确认。UI 操作与远端接收不能做成同一原子事务。
恢复先按唯一标记对照数据库。新协议可证明未尝试点击时安全续行；记录过点击意图或旧协议缺少证据时不自动再点。
`needs_attention` 导致退出码 2 熔断，systemd 不反复重启。

SQLite 使用 WAL 和 synchronous=FULL。异常进程退出后 systemd 重启，恢复原状态。
看门狗 120 秒；初始化、就绪、发送和截图均有独立墙钟期限，长操作之间报心跳。
冷启动首次界面等待 35 秒，单次就绪期限 70 秒，最多三次尝试。

启动前检查镜像 ID、Android SDK、Houdini 库 SHA256 和豆包 versionCode。
组件或 APK 更新后须重新验收。Houdini 上游记录有效期到 2028-07-01；2028-06-01 起拒绝旧组件。

## 操作与故障查看

```bash
sudo systemctl status redroid-doubao-hpe14-worker.service --no-pager
sudo journalctl -u redroid-doubao-hpe14-worker.service -n 50 --no-pager
sudo cat /home/user/redroid-doubao/hpe14-acceptance/health.json
sudo python3 /home/user/redroid-doubao/hpe14_report.py
sudo /home/user/redroid-doubao/worker-venv/bin/python /home/user/redroid-doubao/unattended_worker.py status
```

`answers.json` 保存完成结果；`tasks.sqlite` 保存队列和事件；截图与 XML 位于同目录。
停止本项目 worker 后再手动处理登录或 UI，避免争用。不要清理 Android 数据，也不要把发送状态未知的任务直接改回 pending。

## 验收范围

Linux 故障测试新增发送阶段恢复、并发导出和输入控件短暂消失等用例后共 30 项通过；另外验证了同设备互斥及真实重启恢复。
真实批次应检查全部任务完成、请求编号唯一、正文非空、来源满足要求、无 App 原生崩溃/ANR、无 OOM、无重启风暴，并且业务容器保持运行。

100 题通过只证明该批次和已观测时长。未经实际测试，不能宣称 24 小时长测、主机断电或登录过期恢复已通过。
主机未重启或断电，以免影响现有业务。验证码或外部服务不可用时可能需要人工；系统会保留状态并停止输出未经校验的结果。
