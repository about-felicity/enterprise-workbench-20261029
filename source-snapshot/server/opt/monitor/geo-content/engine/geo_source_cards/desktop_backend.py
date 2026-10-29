"""Filesystem and SSH adapter for the Qt desktop panel; no UI automation."""

import hashlib
import importlib.util
import json
import shlex
import subprocess
import time
from pathlib import Path

from .desktop_status import load
from .runtime import atomic_json


def articles(root):
    root = Path(root).resolve()
    result = []
    for receipt in (root / "articles").glob("*/*/*/receipt.json"):
        data = load(receipt)
        if not data or data.get("status") != "accepted_for_user_review":
            continue
        withdrawal = load(receipt.parent / "withdrawal.json")
        if withdrawal and withdrawal.get("word_sha256") == data.get("word_sha256"):
            continue
        word = receipt.parent / "article.docx"
        draft = receipt.parent / "draft.md"
        if not word.is_file() or not draft.is_file():
            continue
        hashes = data.get("files", {})
        valid = (
            bool(hashes)
            and all(
                Path(name).name == name
                and (receipt.parent / name).is_file()
                and hashlib.sha256((receipt.parent / name).read_bytes()).hexdigest()
                == digest
                for name, digest in hashes.items()
            )
            and hashes.get("article.docx") == data.get("word_sha256")
        )
        text = draft.read_text(encoding="utf-8-sig")
        heading = next(
            (
                line.lstrip("#").strip()
                for line in text.splitlines()
                if line.startswith("# ")
            ),
            "未命名文章",
        )
        result.append(
            {
                **data,
                "integrity": "verified" if valid else "changed",
                "title": heading,
                "folder": str(receipt.parent),
                "word": str(word),
                "draft": str(draft),
                "text": text,
                "sources": (load(receipt.parent / "category.json") or {}).get("source_urls", []),
                "provenance": load(receipt.parent / "provenance.json") or {},
                "user_review": load(root / "user_reviews" / (data.get("word_sha256", "unknown") + ".json")) or {},
            }
        )
    return sorted(
        result,
        key=lambda item: (item["date"], item["category"], item["number"]),
        reverse=True,
    )


def review_article(root, folder, decision, reason=""):
    """Local human acceptance is version-specific, separate from machine checks."""
    root, folder = Path(root).resolve(), Path(folder).resolve()
    if not folder.is_relative_to(root / "articles"):
        raise ValueError("文章目录不在归档范围")
    if decision not in {"approved", "rejected"} or (decision == "rejected" and not reason.strip()):
        raise ValueError("退回修改必须填写原因")
    receipt = load(folder / "receipt.json") or {}
    digest = hashlib.sha256((folder / "article.docx").read_bytes()).hexdigest()
    if digest != receipt.get("word_sha256"):
        raise ValueError("Word 文件已变更，请同步后重新验收")
    record = {"decision": decision, "reason": reason.strip(), "checked_epoch": time.time(), "word_sha256": digest, "date": receipt["date"], "category": receipt["category"], "number": receipt["number"], "scope": "local_user_review"}
    destination = root / "user_reviews"
    destination.mkdir(parents=True, exist_ok=True)
    atomic_json(destination / (digest + ".json"), record)
    history = destination / "history"
    history.mkdir(exist_ok=True)
    atomic_json(history / (str(time.time_ns()) + ".json"), record)
    return record


def server_snapshot(config):
    helper = Path(config["ssh_helper"]).resolve()
    spec = importlib.util.spec_from_file_location("geo_desktop_ssh", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ssh, _ = module.connect()
    try:
        command = " ".join(
            shlex.quote(str(value))
            for value in (
                config["remote_python"],
                "-m",
                "geo_source_cards.desktop_status",
                "--root",
                config["remote_root"],
            )
        )
        _, stdout, _ = ssh.exec_command(command, timeout=25)
        raw = stdout.read().decode("utf8")
        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError("远端状态接口不可用")
        return json.loads(raw)
    finally:
        ssh.close()


def refresh(config_path):
    config = json.loads(Path(config_path).read_text(encoding="utf8"))
    root = Path(config["local_root"]).resolve()
    result = {
        "checked_epoch": time.time(),
        "root": str(root),
        "relay": load(root / "archive_health.json"),
        "active": None,
        "articles": articles(root),
        "revocation_pending": load(root / "revocation_pending.json"),
        "executor": None,
    }
    try:
        result["server"] = server_snapshot(config)
        result["connection"] = "connected"
        atomic_json(root / "desktop_server_cache.json", result["server"])
    except Exception as error:  # noqa: BLE001 -- transport boundary retains cache without claiming connectivity
        result["connection"] = "unverified"
        result["connection_error"] = type(error).__name__
        result["server"] = load(root / "desktop_server_cache.json")
    return result


def synchronize(config_path):
    from .archive_sync import ArchiveClient

    bridge = ArchiveClient(config_path)
    try:
        bridge.sync()
    finally:
        bridge.close()
    return refresh(config_path)


def pipeline_control(config_path, request):
    config = json.loads(Path(config_path).read_text("utf8"))
    if request.get("action") not in {"pause", "recheck", "resume", "settings"}:
        raise ValueError("Unknown panel action")
    helper = Path(config["ssh_helper"]).resolve()
    spec = importlib.util.spec_from_file_location("geo_panel_control", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ssh, _ = module.connect()
    try:
        arguments = [
            config["remote_python"],
            "-m",
            "geo_source_cards.pipeline_control",
            "--root",
            config["remote_root"],
            request["action"],
            "--json",
            json.dumps(request.get("settings", {}), ensure_ascii=False),
        ]
        _, stdout, _ = ssh.exec_command(
            " ".join(shlex.quote(str(v)) for v in arguments), timeout=180
        )
        operation = json.loads(stdout.read().decode("utf8"))
        if stdout.channel.recv_exit_status():
            raise RuntimeError("Server control failed")
    finally:
        ssh.close()
    result = refresh(config_path)
    result["operation"] = operation
    return result


def relay_control(config_path, start):
    # This fixed task is the project's own file relay, never the business services.
    command = (
        "Start" if start else "Stop"
    ) + "-ScheduledTask -TaskName GeoEditorialArchiveSync"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-Command",
            command,
        ],
        capture_output=True,
        check=False,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise RuntimeError("文件交接计划任务操作失败")
    return refresh(config_path)
