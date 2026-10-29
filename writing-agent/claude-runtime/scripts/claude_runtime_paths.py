"""
claude_runtime_paths.py - 统一解析工作区根目录与 Claude 运行时根目录。
"""

from __future__ import annotations

import os
from pathlib import Path


RUNTIME_MARKERS = ("agents", "skills", "styles", "workflows")


def resolve_workspace_root(workspace_root: str | Path | None = None) -> Path:
    if workspace_root:
        return Path(workspace_root).resolve()

    env_workspace = os.environ.get("CLAUDE_WORKSPACE_ROOT")
    if env_workspace:
        return Path(env_workspace).resolve()

    return Path.cwd().resolve()


def workspace_articles_dir(workspace_root: str | Path | None = None) -> Path:
    return resolve_workspace_root(workspace_root) / "articles"


def _looks_like_runtime_root(candidate: Path) -> bool:
    if not candidate.exists():
        return False

    present = _runtime_marker_count(candidate)
    return (candidate / "workflows").exists() and present >= 2


def _runtime_marker_count(candidate: Path) -> int:
    return sum(1 for marker in RUNTIME_MARKERS if (candidate / marker).exists())


def resolve_runtime_root(
    runtime_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    script_file: str | Path | None = None,
) -> Path:
    if runtime_root:
        explicit = Path(runtime_root).resolve()
        if _looks_like_runtime_root(explicit):
            return explicit

    candidates: list[Path] = []

    for env_name in ("CLAUDE_RUNTIME_ROOT", "CLAUDE_PLUGIN_ROOT"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value).resolve())

    workspace = resolve_workspace_root(workspace_root)
    workspace_candidates = [
        workspace / "claude-runtime",
        workspace / ".claude",
    ]
    valid_workspace_candidates = [candidate for candidate in workspace_candidates if _looks_like_runtime_root(candidate)]
    if valid_workspace_candidates:
        valid_workspace_candidates.sort(key=_runtime_marker_count, reverse=True)
        return valid_workspace_candidates[0]

    candidates.extend(workspace_candidates)

    if script_file:
        script_parent = Path(script_file).resolve().parent.parent
        candidates.extend(
            [
                script_parent / "claude-runtime",
                script_parent,
            ]
        )

    valid_candidates = [candidate for candidate in candidates if _looks_like_runtime_root(candidate)]
    if valid_candidates:
        valid_candidates.sort(key=_runtime_marker_count, reverse=True)
        return valid_candidates[0]

    raise FileNotFoundError("无法解析 Claude 运行时根目录")


def runtime_path(
    *parts: str,
    runtime_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
    script_file: str | Path | None = None,
) -> Path:
    return resolve_runtime_root(
        runtime_root=runtime_root,
        workspace_root=workspace_root,
        script_file=script_file,
    ).joinpath(*parts)
