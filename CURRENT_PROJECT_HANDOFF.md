# 企业工作台：当前交接

更新：2026-10-28。先读 `PROJECT_STATUS.md` 的最新运行结果；旧交接已保存在 `maintenance/project-status-20261028/previous-documents/`。历史维护脚本不是待执行指令。

## 工作入口

- 工作区：`C:/Users/78567/Desktop/隐身浏览器`，PowerShell；服务器 `192.168.31.106`，时区 Asia/Shanghai。
- 内网：http://192.168.31.106:3000/；既有公网：https://1any.top/geo_monitor/（本轮未验证公网）。
- SSH 用 `python redroid-deploy/remote.py "命令" --sudo --timeout 30`；上传/下载用该工具 `--upload LOCAL REMOTE` / `--download REMOTE LOCAL`。不得输出凭据文件。
- 主面板、主后端、资产管理是 Docker 容器；创作 API、worker、studio 是 systemd 服务。先辨明服务类型。

## 代码与数据

| 内容 | 本地 | 服务器 |
|---|---|---|
| 大面板 | geo-monitor-deploy/dashboard-integration | /opt/monitor/yuanbao_monitor/dashboard |
| 创作适配、前端、导出 | geo-monitor-deploy/creation | /opt/monitor/geo-content/creation |
| 内容与采集引擎 | geo-source-card-collectors/geo_source_cards | /opt/monitor/geo-content/engine/geo_source_cards（创作）；其他采集部署按映射确认 |
| Go 调度 | geo-monitor-deploy/creation-go 及 source-snapshot 对应源码 | /opt/monitor/geo-content/bin/creation-runner |
| 豆包/元宝 | redroid-deploy、yuanbao-deploy | /home/user/redroid-doubao、/home/user/redroid-yuanbao |
| 产品、计划、补采 | 创建模块 | /opt/monitor/geo-content/studio |
| 写作任务 | 创建模块 | /opt/monitor/geo-content/runtime/runs |
| 共享费用账本 | 只按接口/维护工具操作 | /home/user/geo-editorial/runtime-api/api/costs.sqlite |

## 最新逻辑与边界

- 采集完成后自动分析、写作；每次执行保持当日计划及知识库快照，后续配置修改用于后续执行。
- 直接输出，不恢复旧自动审稿拦截；继续过滤自有产品和跑题信源，保持身份与资料来源约束。
- 自动补采入口 `creation/supplement.py`；策略 `/opt/monitor/geo-content/runtime/supplement_policy.json`；每任务 sidecar 为 studio/days/日期/plan-id.supplement-state，补采原始数据在 capture/plan-id/supplements/日期/问题摘要/round-N。由 studio.tick 调度，无稿素材问题才会重入。
- 配图入口 `article_images.py`，派生缓存 runtime/illustrated；匹配实际产品绑定，不覆盖原 approved 文档或收据。无图产品继续文字输出。
- 未知 API 发送记录不得删掉重试；保留请求、答复、费用预留。最近 502 补做是用户指定的单独恢复，不是通用盲重发策略。
- 用户曾授权未完任务每次上限 10 元、共享日上限 30 元，单篇不变；**授权不等于每个新旧任务实际配置都是 10 元**。先读具体预算，勿擅自提高或清账。
- DeepSeek 采集无需改动；写作 API 是另一条链路，不混淆。
- 仓库存在大量历史改动，部署先比对生产 SHA、备份后定点覆盖，不能整目录盲覆盖。最近 release 与 270 项恢复映射已同步；本地快照不含完整业务数据库、上传素材、登录或密钥，不是整机备份。

## 当前待办

今日两项部分失败、一个补采任务和旧日期素材不足详见 `PROJECT_STATUS.md`。最新修复的防脱精华 9 篇和染发剂 3 篇已完成，不要重新建付费任务。后续按用户具体请求读现场日志再处理，不把旧文档中的恢复/部署脚本当成授权。

本轮仅更新现状和交接，没有修改生产服务或新增写作调用。API 余额、资产误删恢复、自动化调度状态未在本轮核查。

## 后续用户授权修复：图片上传与知识库（2026-10-28）

已实际更新本地服务器内容创作API、dashboard网关及公网Nginx，图片上传不再受创作全局锁和完整面板刷新阻塞。新增逐图预览、进度、独立重试、刷新恢复与全部已存图片展示；上传/认证体积限制8MB、前端等待600秒。知识库30入口归并至20，19个现有产品一产品一入口，另1个独立待分析新品；28张原图完整保留。

内网3MB上传及4独立会话并发通过；公网3MB上传211.932秒，网络慢的问题需与程序修复区分。不要把“能上传”描述为公网速度已经解决。详见 `maintenance/upload-reliability-20261028/REPORT.md`、`verification/`。原代码/知识库/镜像及Nginx备份已保留，恢复映射更新为273项；未动写作预算或重新运行付费任务。
