"""Install only this project's coordinator and session watcher (run with sudo)."""

import argparse
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--user", required=True)
    parser.add_argument("--enable-capture", action="store_true")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--key-file", type=Path)
    args = parser.parse_args()
    base = args.base.resolve()
    runtime = (args.runtime or base / "runtime").resolve()
    if not runtime.is_relative_to(base):
        raise ValueError("Runtime must be inside the project base")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", args.user):
        raise ValueError("Invalid service user")
    python = base / "venv/bin/python"
    if not python.is_file() or not (runtime / "product.json").is_file():
        raise ValueError("Prepare the runtime and virtual environment first")
    command = lambda value: " ".join(json.dumps(str(item)) for item in value)
    modules = {
        "geo-editorial-coordinator": (
            [
                "-m",
                "geo_source_cards.daily_editorial",
                "--root",
                runtime,
                "serve",
            ],
            "256M",
        ),
        "geo-editorial-session-watch": (
            [
                "-m",
                "geo_source_cards.session_watch",
                "--runtime-dir",
                runtime / "collectors/deepseek",
                "--interval",
                "180",
                "--no-desktop",
            ],
            "1500M",
        ),
    }
    if args.key_file:
        if not args.key_file.is_file():
            raise ValueError("Prepare the API key file first")
        modules["geo-editorial-api-worker"] = (
            [
                "-m",
                "geo_source_cards.api_worker",
                "--root",
                runtime,
                "--key-file",
                args.key_file.resolve(),
            ],
            "768M",
        )
    if args.enable_capture:
        modules["geo-editorial-scheduler"] = (
            [
                "-m",
                "geo_source_cards.scheduler",
                "--root",
                runtime,
            ],
            "3500M",
        )
    for name, (arguments, memory) in modules.items():
        oneshot = False
        text = f"""[Unit]
Description=Media editorial project {name}
After=network-online.target
Wants=network-online.target

[Service]
Type={"oneshot" if oneshot else "simple"}
User={args.user}
WorkingDirectory={base}
Environment=GEO_DEEPSEEK_PORT=9414
Environment=GEO_PIPELINE_ROOT={runtime}
Environment=PYTHONUNBUFFERED=1
ExecStart={command([python, *arguments])}
{"TimeoutStartSec=5h" if oneshot else "Restart=on-failure" + chr(10) + "RestartSec=15"}
MemoryMax={memory}
CPUQuota=150%
TasksMax=512
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths={base}
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
        Path(f"/etc/systemd/system/{name}.service").write_text(text, encoding="utf8")
    if args.enable_capture:
        # Retire the old 01:00 timer before enabling settings-driven scheduling.
        subprocess.run(
            ["systemctl", "disable", "--now", "geo-editorial-capture.timer"],
            check=False,
            capture_output=True,
        )
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    names = ["geo-editorial-coordinator.service", "geo-editorial-session-watch.service"]
    if args.key_file:
        names.append("geo-editorial-api-worker.service")
    if args.enable_capture:
        names.append("geo-editorial-scheduler.service")
    subprocess.run(["systemctl", "enable", "--now", *names], check=True)
    subprocess.run(
        [
            "systemctl",
            "restart",
            "geo-editorial-coordinator.service",
            "geo-editorial-session-watch.service",
        ],
        check=True,
    )
    if args.key_file and args.enable_capture:
        schedule = {
            "status": "enabled",
            "timezone": "Asia/Shanghai",
            "capture_hour": 5,
            "settings_driven": True,
            "hour": 5,
            "max_per_category": 10,
            "mode": "server_deepseek_flash_api",
            "first_05_trigger_verified": False,
        }
        schedule_path = runtime / "schedule_state.json"
        temporary = schedule_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf8"
        )
        temporary.replace(schedule_path)
    print(json.dumps({"enabled": names, "base": str(base)}))


if __name__ == "__main__":
    main()
