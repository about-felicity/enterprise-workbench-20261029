# 运维手册

以下命令在已有部署的Linux主机执行。本文不包含登录凭据；不要将密钥、App数据库、备份数据卷或完整聊天导出提交Git。

## 1. 只读检查

```bash
cd /home/user/redroid-doubao
sudo systemctl status redroid-doubao-hpe14-worker.service --no-pager
sudo journalctl -u redroid-doubao-hpe14-worker.service -n 80 --no-pager
sudo cat hpe14-acceptance/health.json
sudo python3 hpe14_report.py
sudo cat soak1h/status.json
sudo cat soak1h/sequence.json
sudo cat soak24h/status.json
```

判读顺序：先看状态更新时间，再看任务错误，最后区分服务退出与Android原生故障。health.json在worker停止后不会继续更新；旧的idle不能代表现在健康。只看systemd active也不能证明所有题目成功。

当前待处理错误为`Required sources are missing`。应保留App回答与队列事件，确认是不是模型没给引用。不要把require_sources改掉后宣称原测试通过。

## 2. 提交新批次

先确认当前needs_attention已经经过人工处理。普通新批次命令不能解除既有熔断。

在项目目录准备`my-questions.json`，格式为UTF-8字符串数组：

```json
["问题一", "问题二"]
```

```bash
sudo /home/user/redroid-doubao/worker-venv/bin/python \
  /home/user/redroid-doubao/unattended_worker.py \
  --state-dir /home/user/redroid-doubao/hpe14-acceptance \
  enqueue --batch my-unique-batch --questions /home/user/redroid-doubao/my-questions.json \
  --require-sources
```

正常情况下常驻worker顺序消费。来源非必需的业务可为新批次省略require-sources，但必须明确其验收不同，不能用于替代原长测结果。

状态／导出CLI子命令应先运行`--help`核对现有版本；输出目录与服务的state-dir保持一致。

## 3. 暂停和恢复

```bash
sudo systemctl stop redroid-doubao-hpe14-worker.service
# 完成人工核对、登录或维护后，在获得操作授权时执行：
sudo systemctl start redroid-doubao-hpe14-worker.service
```

重启不等于清除业务故障。needs_attention存在时，worker仍会以退出码2停止。不能通过删tasks.sqlite、删事件、改pending或删除点击意图来“修复”。

对prepared状态先查同一任务的App请求和点击意图。新协议只有明确没有尝试点击才允许续行；已有点击意图而结果未知必须保守核对。

## 4. 故障定位表

| 现象 | 先查 | 禁止的捷径 |
|---|---|---|
| worker failed / code2 | needs_attention及任务错误 | 反复restart或修改状态掩盖错误 |
| 正文无来源 | require_sources、App结构化答案 | 把正文里的任意网址当有效引用补齐 |
| App打不开 | 预检查、版本、冷启动日志、原生日志 | 去掉版本和哈希校验 |
| 没找到请求 | wire_question、协议事件、数据库集合 | 立即重新点击发送 |
| 多个候选答案 | 同会话索引、重新生成／重复请求 | 猜测取最后一个 |
| SQLite schema变化 | 当前APK与字段／块类型 | 默默忽略未知块 |
| 看门狗重启 | 阶段耗时、系统资源、基础设施错误 | 无限提高重启次数 |
| 长测failed | 阶段status和首次错误 | 删除报告后沿用旧已观测时长 |

## 5. 数据与备份

完成结果：`hpe14-acceptance/answers.json`；队列：`tasks.sqlite`；事件：SQLite的events表；健康：`health.json`；原生日志：`native-runtime.log`；截图／XML：状态目录内按任务编号命名。

迁移需同时保存：已验证镜像、Android数据卷、队列一致性快照、源码／服务文件、组件哈希清单。登录数据和聊天内容不放公开仓库。恢复到新机后先验证单题、重启恢复、再重新计时长测。

## 6. 维护边界

只操作本项目命名服务和容器，不影响原有业务容器，不修改主机网络看门狗。当前文档仓库与后来的文章生产系统无依赖；不要运行其scheduler或费用脚本来处理本项目。

新会话接手时先读README的快照时间，然后重新核对状态；不要直接相信旧文档“仍在长测”的叙述。
