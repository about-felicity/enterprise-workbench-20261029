# Claude Plugin 双轨兼容实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `claude-runtime/` 单一事实源，并同时生成 `.claude/` 兼容层与 `plugins/writing-agent/` 插件目录，保证 clone 与 plugin 两种用户路径都可用。

**Architecture:** 运行时资产统一迁入 `claude-runtime/`。仓库内 `.claude/` 和插件目录不再作为长期人工维护入口，而是由同步脚本生成。路径解析统一区分“插件静态资源根”和“用户工作区根”，避免插件模式把产物写回缓存目录。

**Tech Stack:** Python 3.11、unittest、JSON、Markdown、Claude Code plugin manifest

---

### Task 1: 为工作区路径解耦补测试

**Files:**
- Modify: `tests/test_auto_clean_hook.py`
- Modify: `tests/test_run_manifest.py`
- Modify: `tests/test_validate_workflow.py`
- Create: `tests/test_claude_runtime_sync.py`

- [ ] **Step 1: 写失败测试，覆盖显式工作区与运行时根**

```python
def test_update_run_manifest_supports_workspace_root(self) -> None:
    manifest = update_run_manifest(
        project_dir=self.project_dir,
        body_file="draft_v1.md",
        workspace_root=self.root,
    )
    self.assertEqual("draft_v1.md", manifest["latest_body_file"])

def test_validate_repo_supports_runtime_root(self) -> None:
    report = validate_repo(self.root, "active", runtime_root=self.root / "claude-runtime")
    self.assertFalse(report["errors"])
```

- [ ] **Step 2: 跑 Python 单测，确认这些新断言先失败**

Run: `python -m unittest tests.test_run_manifest tests.test_auto_clean_hook tests.test_validate_workflow -v`  
Expected: 至少出现参数不存在或路径解析错误导致的 FAIL/ERROR

- [ ] **Step 3: 给同步/校验脚本预留测试文件**

```python
class ClaudeRuntimeSyncTests(unittest.TestCase):
    def test_sync_copies_runtime_assets_to_both_targets(self) -> None:
        ...

    def test_check_reports_drift_when_consumer_differs(self) -> None:
        ...
```

- [ ] **Step 4: 运行新测试文件，确认同步逻辑目前尚未实现**

Run: `python -m unittest tests.test_claude_runtime_sync -v`  
Expected: 由于模块不存在或函数不存在而失败

### Task 2: 引入共享路径解析工具

**Files:**
- Create: `scripts/claude_runtime_paths.py`
- Modify: `scripts/auto_clean_hook.py`
- Modify: `scripts/update_run_manifest.py`
- Modify: `scripts/verify_required_files.py`
- Modify: `scripts/validate_workflow.py`

- [ ] **Step 1: 写最小路径工具实现**

```python
from pathlib import Path

def resolve_workspace_root(workspace_root: str | Path | None = None) -> Path:
    if workspace_root:
        return Path(workspace_root).resolve()
    return Path.cwd().resolve()

def resolve_runtime_root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root:
        return Path(runtime_root).resolve()
    script_root = Path(__file__).resolve().parent.parent
    runtime_dir = script_root / "claude-runtime"
    if runtime_dir.exists():
        return runtime_dir
    return script_root / ".claude"
```

- [ ] **Step 2: 让 `update_run_manifest.py` 接收 `--workspace-root`**

```python
parser.add_argument("--workspace-root", help="工作区根目录，默认当前目录")
project_dir = resolve_workspace_root(args.workspace_root) / "articles" / args.project
```

- [ ] **Step 3: 让 `verify_required_files.py` 和 `auto_clean_hook.py` 基于工作区根定位 `articles/`**

```python
workspace_root = resolve_workspace_root(args.workspace_root)
articles_dir = workspace_root / "articles"
```

- [ ] **Step 4: 让 `validate_workflow.py` 接收显式 `runtime_root`，优先校验 `claude-runtime/`，兼容 `.claude/`**

```python
def validate_repo(root: Path, targets: str = "active", runtime_root: Path | None = None) -> dict:
    runtime_root = runtime_root or (root / "claude-runtime")
```

- [ ] **Step 5: 运行相关单测，确认路径解耦通过**

Run: `python -m unittest tests.test_auto_clean_hook tests.test_run_manifest tests.test_validate_workflow -v`  
Expected: PASS

### Task 3: 建立 `claude-runtime/` 单一事实源

**Files:**
- Create: `claude-runtime/agents/`
- Create: `claude-runtime/skills/`
- Create: `claude-runtime/styles/`
- Create: `claude-runtime/workflows/`
- Create: `claude-runtime/hooks/hooks.json`
- Create: `claude-runtime/scripts/`

- [ ] **Step 1: 复制现有运行时资产到 `claude-runtime/`**

```text
.claude/agents      -> claude-runtime/agents
.claude/skills      -> claude-runtime/skills
.claude/styles      -> claude-runtime/styles
.claude/workflows   -> claude-runtime/workflows
scripts/*runtime*   -> claude-runtime/scripts
.claude/settings.json 中 hooks -> claude-runtime/hooks/hooks.json
```

- [ ] **Step 2: 保持 `git clone` 所需文件名不变**

```text
collab_v2.json
writing-executor.md
工作流导演/SKILL.md
```

- [ ] **Step 3: 运行工作流契约测试，确认事实源内容完整**

Run: `python -m unittest tests.test_validate_workflow -v`  
Expected: PASS

### Task 4: 生成 `.claude/` 兼容层和 plugin 目录

**Files:**
- Create: `scripts/sync_claude_runtime.py`
- Create: `scripts/check_claude_runtime_sync.py`
- Create: `plugins/writing-agent/.claude-plugin/plugin.json`
- Create: `plugins/writing-agent/hooks/hooks.json`
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: 实现同步脚本，把事实源复制到两个消费端**

```python
SYNC_MAP = {
    "agents": ["claude-runtime/agents", ".claude/agents", "plugins/writing-agent/agents"],
    "skills": ["claude-runtime/skills", ".claude/skills", "plugins/writing-agent/skills"],
}
```

- [ ] **Step 2: 让同步脚本额外写出消费端专属文件**

```python
write_plugin_manifest(...)
write_marketplace_manifest(...)
write_project_settings(...)
```

- [ ] **Step 3: 实现校验脚本，对比事实源与消费端文件摘要**

```python
def collect_hashes(root: Path) -> dict[str, str]:
    ...
```

- [ ] **Step 4: 运行同步脚本并检查新目录存在**

Run: `python scripts/sync_claude_runtime.py`  
Expected: 输出已同步的目标目录，生成 `.claude/` 与 `plugins/writing-agent/`

- [ ] **Step 5: 运行校验脚本确认无漂移**

Run: `python scripts/check_claude_runtime_sync.py`  
Expected: PASS

### Task 5: 为 plugin 用户补工作区初始化

**Files:**
- Create: `claude-runtime/templates/`
- Create: `claude-runtime/scripts/init_workspace.py`
- Modify: `plugins/writing-agent/.claude-plugin/plugin.json`
- Modify: `README.md`

- [ ] **Step 1: 写最小工作区初始化脚本**

```python
def init_workspace(workspace_root: Path) -> None:
    (workspace_root / "articles").mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: 在插件说明中写明初始化与使用方式**

```json
{
  "name": "writing-agent",
  "version": "0.8.0",
  "skills": "./skills",
  "hooks": "./hooks/hooks.json"
}
```

- [ ] **Step 3: 在 README 增加“plugin 用户如何初始化工作区”说明**

```text
1. 安装插件
2. 在目标目录启动 claude
3. 运行初始化命令或让工作流首次执行时自动补齐最小目录
```

- [ ] **Step 4: 在临时目录验证初始化结果**

Run: `python claude-runtime/scripts/init_workspace.py --workspace-root temp/plugin-workspace`  
Expected: `temp/plugin-workspace/articles/` 存在

### Task 6: 跑全量回归并人工检查关键产物

**Files:**
- Modify: `package.json`
- Modify: `README.md`

- [ ] **Step 1: 增加同步与校验命令**

```json
{
  "scripts": {
    "sync:claude-runtime": "python scripts/sync_claude_runtime.py",
    "check:claude-runtime": "python scripts/check_claude_runtime_sync.py"
  }
}
```

- [ ] **Step 2: 跑 Python 单测**

Run: `python -m unittest discover -s tests -p "test_*.py"`  
Expected: PASS

- [ ] **Step 3: 跑脚本语法校验**

Run: `python -m py_compile scripts/*.py claude-runtime/scripts/*.py`  
Expected: PASS

- [ ] **Step 4: 跑同步与漂移校验**

Run: `python scripts/sync_claude_runtime.py && python scripts/check_claude_runtime_sync.py`  
Expected: PASS

- [ ] **Step 5: 核查关键目录**

```text
.claude/agents
.claude/skills
plugins/writing-agent/.claude-plugin/plugin.json
plugins/writing-agent/hooks/hooks.json
.claude-plugin/marketplace.json
```

- [ ] **Step 6: 更新版本说明**

```text
说明 clone 模式继续可用；plugin 模式可初始化最小工作区；后续运行时改动需先改 claude-runtime
```
