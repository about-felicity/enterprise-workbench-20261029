"""Add GEO browser collectors and grouping without restarting existing services."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

BASE = Path("/opt/monitor/geo-capture")
SOURCE = Path("/home/user/geo-editorial")
PACKAGE = Path(__file__).parent
STAMP = str(int(time.time()))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf8")


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def main():
    if BASE.exists():
        raise SystemExit("Deployment root exists; inspect it before changing a live installation")
    for port in (9514, 8803):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Dedicated port occupied: " + str(port))
    BASE.mkdir(mode=0o750)
    (BASE / "backups" / STAMP).mkdir(parents=True, mode=0o700)
    backup = BASE / "backups" / STAMP
    containers = ["monitor-dashboard", "monitor-dashboard-api", "monitor-result-receiver", "monitor-doubao-receiver",
                  "monitor-product-worker", "monitor-content-worker", "monitor-postgres", "monitor-redis",
                  "doubao-hpe14-13-test", "doubao-hpe14-account2"]
    write(backup / "docker-before.json", run("docker", "inspect", *containers, "--format",
          '{{json .Name}} {{json .State.StartedAt}}'))
    write(backup / "editorial-before.txt", run("systemctl", "show", "geo-editorial-scheduler.service",
          "geo-editorial-api-worker.service", "geo-editorial-coordinator.service", "geo-editorial-session-watch.service",
          "-p", "Id", "-p", "MainPID", "-p", "ExecMainStartTimestamp"))
    run("cp", "-a", "--reflink=auto", str(SOURCE / "venv"), str(BASE / "venv"))
    site = next((BASE / "venv/lib").glob("python*/site-packages"))
    original = site / "geo_source_cards/cli.py"
    shutil.copy2(original, backup / "cli.py")
    shutil.copy2(PACKAGE / "cli.py", original)
    for file in ("capture_bridge.py", "fleet_status.py", "completion_guard.py"):
        shutil.copy2(PACKAGE / file, BASE / file)
    questions = json.loads((PACKAGE / "geo_questions.json").read_text("utf-8-sig"))
    assert len(questions) == len(set(questions)) == 21
    lanes = []
    for model, rounds, name in (("deepseek", 3, "DeepSeek"), ("wenxin_card", 6, "文心卡片"), ("baidu_ai", 5, "百度卡片")):
        batch = f"geo-{model}-21x{rounds}-20261015"
        config = {"model": model, "rounds": rounds, "questions": questions, "batch": batch, "device": "geo-headless-" + model}
        config_path = BASE / "config" / (model + ".json")
        write(config_path, json.dumps(config, ensure_ascii=False, indent=2))
        (BASE / "batches" / batch / "collector").mkdir(parents=True)
        service = "geo-capture-" + model.replace("_", "-") + ".service"
        write(Path("/etc/systemd/system") / service, f'''[Unit]
Description=GEO {name} independent capture and processed delivery
After=network-online.target docker.service geo-monitor-status.service
Wants=network-online.target geo-monitor-status.service
PartOf=geo-monitor.target

[Service]
Type=simple
User=user
WorkingDirectory={BASE}
Environment=PYTHONUNBUFFERED=1
ExecStart={BASE}/venv/bin/python -u {BASE}/capture_bridge.py --config {config_path}
Restart=on-failure
RestartPreventExitStatus=2
RestartSec=30
TimeoutStopSec=35
KillMode=mixed
MemoryHigh=1400M
MemoryMax=2200M
TasksMax=512
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths={BASE}
PrivateTmp=true

[Install]
WantedBy=geo-monitor.target
''')
        lanes.append({"name": name, "service": service, "planned": 21 * rounds,
                      "health": str(BASE / "batches" / batch / "bridge_health.json")})
    for index, batch, service in (
        (1, "geo-products-21x5-account1-20261014", "redroid-geo-products.service"),
        (2, "geo-products-21x5-account2-relogin-20261013", "redroid-geo-products-account2.service")):
        health = Path("/home/user/redroid-doubao/batches") / batch / "bridge_health.json"
        state = json.loads(health.read_text())
        assert state["status"] == "complete" and state["geo_processed"] == 105
        shutil.copy2(health, backup / ("doubao" + str(index) + "-health.json"))
        run("cp", "-a", "/etc/systemd/system/" + service, str(backup / service))
        dropin = Path("/etc/systemd/system") / (service + ".d/geo-group.conf")
        if dropin.exists():
            raise SystemExit("Unexpected pre-existing grouping drop-in")
        write(dropin, f'''[Unit]
PartOf=geo-monitor.target

[Service]
ExecCondition={BASE}/venv/bin/python {BASE}/completion_guard.py {health}
''')
        lanes.insert(index - 1, {"name": "豆包 " + str(index), "service": service, "planned": 105, "health": str(health)})
    write(BASE / "fleet.json", json.dumps({"project": "GEO", "containers": containers, "collectors": lanes}, ensure_ascii=False, indent=2))
    write(Path("/etc/systemd/system/geo-monitor.target"), """[Unit]
Description=GEO dashboard analysis and capture fleet
After=docker.service network-online.target
Wants=geo-monitor-status.service geo-capture-deepseek.service geo-capture-wenxin-card.service geo-capture-baidu-ai.service redroid-geo-products.service redroid-geo-products-account2.service

[Install]
WantedBy=multi-user.target
""")
    write(Path("/etc/systemd/system/geo-monitor-status.service"), f'''[Unit]
Description=GEO unified capture status
After=docker.service
PartOf=geo-monitor.target
[Service]
ExecStart={BASE}/venv/bin/python {BASE}/fleet_status.py
Restart=on-failure
RestartSec=15
MemoryMax=128M
UMask=0022
[Install]
WantedBy=geo-monitor.target
''')
    run("chown", "-R", "user:user", str(BASE))
    # Take a stopped, locked source profile snapshot. Never copy a profile
    # while a source collector or its session watcher has Chrome open.
    sys.path.insert(0, str(site))
    from geo_source_cards.runtime import process_lock
    source_runtime = SOURCE / "runtime-api/collectors/deepseek"
    with process_lock(source_runtime / "collector.lock"):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 9414)) == 0:
                raise SystemExit("Source browser still active: deployment prepared, seed at idle before starting")
        destination = BASE / "batches/geo-deepseek-21x3-20261015/collector/web_profiles/deepseek"
        shutil.copytree(source_runtime / "web_profiles/deepseek", destination,
                        ignore=shutil.ignore_patterns("Singleton*", "Cache", "Code Cache", "GPUCache", "Crashpad"))
        for item in destination.rglob("*"):
            if not item.is_symlink():
                os.chown(item, 1000, 1000)
        os.chown(destination, 1000, 1000)
    write(BASE / "deployment.json", json.dumps({"created_at": time.time(), "source": str(SOURCE),
          "source_profile_snapshot_at": time.time(), "backup": str(backup),
          "bridge_sha256": hashlib.sha256((BASE / "capture_bridge.py").read_bytes()).hexdigest()}, indent=2))
    run("chown", "-R", "user:user", str(BASE))
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "geo-monitor.target")
    print(json.dumps({"status": "prepared", "root": str(BASE), "backup": str(backup), "collectors": lanes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
