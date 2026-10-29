# Claude Plugin 双轨兼容设计

**日期**：2026-04-20  
**状态**：已确认，进入实现  
**目标**：同时支持两种使用方式，且尽量避免后续维护漂移。

---

## 目标

本次改造需要同时满足两个约束：

1. `git clone` 用户继续在项目根目录启动 `claude`，现有 `.claude/` 使用方式保持可用。
2. `plugin` 用户安装后，可以在任意正常工作目录启动 `claude` 并使用写作工作流，不依赖先 clone 本仓库。

这里的“任意目录”有两个前提：

- 当前目录可读写
- 本机依赖满足运行条件，例如 Python、Node、Claude Code 本体、模型配置等

---

## 不做的事

- 不把仓库整体重构成“只剩插件”的模式
- 不要求现有 `git clone` 用户改用插件命名空间入口
- 不把所有文档、demo、桌面应用代码都塞进插件运行时目录
- 不尝试在本次改造里解决所有发布流程自动化问题

---

## 核心方案

采用“单一事实源 + 双端生成”的结构，而不是长期双写维护。

### 单一事实源

新增 `claude-runtime/` 目录，作为 Claude 运行时资产的唯一来源。包含：

- `skills/`
- `agents/`
- `hooks/`
- `workflows/`
- `styles/`
- `scripts/`
- `templates/`

后续所有运行时相关改动，优先在 `claude-runtime/` 下完成。

### 两个消费端

从 `claude-runtime/` 生成两个面向用户的目录：

1. 项目兼容层：`.claude/`
2. 插件发布目录：`plugins/writing-agent/`

这两个目录不再视为长期人工编辑入口。允许保留少量只属于该消费端的元数据文件，例如：

- `.claude/settings.json`
- `plugins/writing-agent/.claude-plugin/plugin.json`
- `plugins/writing-agent/hooks/hooks.json`

---

## 目录结构

目标结构如下：

```text
claude-runtime/
  agents/
  hooks/
    hooks.json
  scripts/
  skills/
  styles/
  templates/
  workflows/

.claude/
  agents/
  skills/
  styles/
  workflows/
  settings.json

plugins/
  writing-agent/
    .claude-plugin/
      plugin.json
    agents/
    hooks/
      hooks.json
    scripts/
    skills/
    styles/
    templates/
    workflows/
```

---

## 运行时路径原则

当前仓库里有多处脚本默认使用“脚本所在目录的上一级”作为项目根。这在仓库模式下成立，但在插件安装后会错误指向插件缓存目录。

改造后的路径原则：

### 插件静态资源

用于读取：

- 风格文件
- 工作流文件
- 插件模板
- 插件内脚本

读取路径以“运行时根目录”解析。运行时根目录可以来自：

1. 显式参数
2. 环境变量
3. 脚本相对目录推导

### 用户工作区

用于写入：

- `articles/`
- `run_manifest.json`
- `_clean.txt`
- `.html`
- 文章草稿和备注

写入路径以“工作区根目录”解析。优先级：

1. 显式 `--workspace-root`
2. 当前工作目录 `cwd`

原则上，插件模式下任何动态产物都不得写回插件目录。

---

## git clone 用户兼容策略

`git clone` 用户的体验目标是不变：

- 继续在项目根目录启动 `claude`
- 继续使用项目内 `.claude/`
- 继续沿用 README 中的主要说明路径

实现方式不是保留旧内容原封不动，而是让 `.claude/` 由同步脚本生成。用户看见的入口不变，但维护来源变成 `claude-runtime/`。

---

## plugin 用户策略

plugin 用户不 clone 仓库时，需要插件补齐最小工作区能力。

本次改造采用“显式初始化命令 + 运行时按需检查”的组合：

1. 插件提供工作区初始化脚本
2. 用户可在任意工作目录初始化最小结构
3. 工作流执行前做最小工作区检查

初始化内容只包含运行所需最小骨架，例如：

- `articles/`
- 可选模板文件
- 必要说明或占位目录

不会把整份仓库内容复制到用户目录。

---

## 同步与防漂移

为了避免后续出现“clone 用户是新逻辑，plugin 用户还是旧逻辑”，增加两个脚本：

1. `scripts/sync_claude_runtime.py`
   - 从 `claude-runtime/` 同步到 `.claude/` 和 `plugins/writing-agent/`

2. `scripts/check_claude_runtime_sync.py`
   - 校验 `claude-runtime/`、`.claude/`、`plugins/writing-agent/` 是否一致
   - 检测到漂移时返回非 0 并输出差异

维护规则：

- 改运行时资产时，优先改 `claude-runtime/`
- 同步后再发布 plugin
- 涉及插件运行时变更时，更新插件版本号

---

## 插件元数据

插件目录需要补齐：

- `plugins/writing-agent/.claude-plugin/plugin.json`
- 仓库根 `.claude-plugin/marketplace.json`

插件元数据的职责：

- 让插件可以被本地 `--plugin-dir` 加载
- 让后续 marketplace 安装具备清晰来源
- 提供展示信息、分类、安装策略和默认入口

---

## 测试与验证

本次改造至少覆盖以下验证：

### 单元测试

- 路径解析是否区分“运行时根目录”和“工作区根目录”
- `auto_clean_hook` 是否在指定工作区内寻找正文来源
- `update_run_manifest` 和 `verify_required_files` 是否支持显式工作区
- 工作流校验是否支持新的运行时根
- 同步脚本是否能把事实源复制到两个消费端
- 校验脚本是否能检测消费端漂移

### 集成级验证

- 在仓库根目录运行原有测试命令，确认 clone 模式不退化
- 生成 `.claude/` 兼容目录后，结构完整
- 生成插件目录后，manifest、hooks、skills、agents、scripts 存在
- 在一个临时空目录中执行插件初始化，确认最小工作区可建立

---

## 风险

### 入口重名

如果同一能力同时通过项目 `.claude/` 和已启用 plugin 暴露，可能出现重名或重复发现。这个行为需要实际验证，不能假设 Claude Code 一定会自动去重。

### 路径遗漏

只要还有脚本残留“脚本上一级就是项目根”的假设，plugin 模式就可能把产物写错地方。

### 人工绕过事实源

如果后续有人直接改 `.claude/` 或 `plugins/writing-agent/`，会重新引入漂移风险。需要靠校验脚本和文档约束这个问题。

---

## 成功标准

满足以下条件即可认为本次改造达标：

1. `git clone` 用户原有主路径仍可用
2. `plugin` 用户不需要先 clone 仓库即可初始化工作区
3. 动态产物全部写入用户工作区
4. 运行时资产存在单一事实源
5. 可以通过脚本发现双端漂移
6. 插件具备发布到 marketplace 的基础目录结构
