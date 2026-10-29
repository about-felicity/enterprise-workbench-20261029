"""Download validated server articles over SSH; never claim or dispatch tasks."""

import argparse
import importlib.util
import json
import time
from pathlib import Path

from .daily_editorial import IDENTIFIER, file_hash, safe_name
from .relay_health import observation
from .runtime import atomic_json, process_lock
from .staged_editorial import read


class ArchiveClient:
    def __init__(self, config):
        self.config = read(config)
        self.root = Path(self.config["local_root"]).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        identity = self.root / "client.json"
        if not identity.exists():
            import secrets

            atomic_json(identity, {"id": secrets.token_hex(12)})
        self.client_id = read(identity)["id"]
        helper = Path(self.config["ssh_helper"]).resolve()
        specification = importlib.util.spec_from_file_location(
            "editorial_ssh_connection", helper
        )
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        self.ssh, _ = module.connect()
        self.sftp = self.ssh.open_sftp()
        self.sftp.get_channel().settimeout(30)
        self.ssh.get_transport().set_keepalive(30)
        self.remote = self.config["remote_root"].rstrip("/")

    def close(self):
        self.sftp.close()
        self.ssh.close()

    def remote_json(self, path):
        with self.sftp.open(path) as stream:
            return json.loads(stream.read().decode("utf-8-sig"))

    def sync_approved(self):
        self.sync_revocations()
        downloaded = 0
        try:
            dates = self.sftp.listdir(self.remote + "/approved")
        except FileNotFoundError:
            return {"downloaded": 0}
        for date in dates:
            import re

            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                continue
            for category in self.sftp.listdir(self.remote + "/approved/" + date):
                if safe_name(category) != category:
                    raise ValueError("Unsafe category folder")
                for number in self.sftp.listdir(
                    self.remote + "/approved/" + date + "/" + category
                ):
                    if not re.fullmatch(r"(?:0[1-9]|[1-9][0-9]|100)", number):
                        raise ValueError("Unsafe article number")
                    source = (
                        self.remote
                        + "/approved/"
                        + date
                        + "/"
                        + category
                        + "/"
                        + number
                    )
                    destination = self.root / "articles" / date / category / number
                    receipt = self.remote_json(source + "/receipt.json")
                    if (
                        (destination / "receipt.json").exists()
                        and read(destination / "receipt.json")["word_sha256"]
                        == receipt["word_sha256"]
                        and all(
                            (destination / name).is_file()
                            and file_hash(destination / name) == expected
                            for name, expected in receipt.get("files", {}).items()
                        )
                    ):
                        continue
                    destination.mkdir(parents=True, exist_ok=True)
                    names = (
                        "draft.md",
                        "article.docx",
                        "claim_map.json",
                        "knowledge_to_sections.json",
                        "category.json",
                        "semantic_review.json",
                    ) + (("provenance.json",) if "provenance.json" in receipt.get("files", {}) else ())
                    for name in names:
                        self.sftp.get(
                            source + "/" + name, str(destination / (name + ".transfer"))
                        )
                    if (
                        file_hash(destination / "article.docx.transfer")
                        != receipt["word_sha256"]
                    ):
                        raise ValueError("Approved Word hash mismatch")
                    for name, expected in receipt.get("files", {}).items():
                        if (
                            safe_name(name) != name
                            or file_hash(destination / (name + ".transfer")) != expected
                        ):
                            raise ValueError("Approved output hash mismatch: " + name)
                    for path in destination.glob("*.transfer"):
                        path.replace(path.with_suffix(""))
                    atomic_json(destination / "receipt.json", receipt)
                    downloaded += 1
        return {"downloaded": downloaded}

    def sync_revocations(self):
        pending = []
        try:
            names = self.sftp.listdir(self.remote + "/revocations")
        except FileNotFoundError:
            return
        for name in names:
            if not name.endswith(".json") or not IDENTIFIER.fullmatch(name[:-5]):
                continue
            entry = self.remote_json(self.remote + "/revocations/" + name)
            date, category, number = entry["date"], entry["category"], entry["number"]
            if (
                not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}", date)
                or safe_name(category) != category
                or not isinstance(number, int)
                or not 1 <= number <= 100
            ):
                raise ValueError("Unsafe revocation path")
            source = self.root / "articles" / date / category / f"{number:02d}"
            receipt = source / "receipt.json"
            known_hash = (
                read(receipt).get("word_sha256")
                if receipt.exists()
                else file_hash(source / "article.docx")
                if (source / "article.docx").exists()
                else None
            )
            if known_hash != entry["word_sha256"]:
                continue
            destination = (
                self.root / "quarantine" / date / category / f"{number:02d}" / name[:-5]
            )
            if destination.exists():
                destination = destination.with_name(
                    destination.name + "-duplicate-" + str(time.time_ns())
                )
            if not source.resolve().is_relative_to(
                self.root.resolve()
            ) or not destination.resolve().is_relative_to(self.root.resolve()):
                raise ValueError("Revocation path escapes local output root")
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(source / "withdrawal.json", entry)
            try:
                source.rename(destination)
            except PermissionError:
                pending.append(
                    {
                        **entry,
                        "status": "waiting_for_file_release",
                        "file": str(source / "article.docx"),
                    }
                )
        atomic_json(
            self.root / "revocation_pending.json",
            {"checked_epoch": time.time(), "pending": pending},
        )

    def sync(self):
        with process_lock(self.root / "archive_sync.lock"):
            try:
                control = self.remote_json(self.remote + "/control.json")
            except FileNotFoundError:
                control = {}
            previous_control = read(self.root / "server_control.json") if (self.root / "server_control.json").exists() else {}
            if control.get("paused") and control.get("revision") != previous_control.get("revision"):
                from .session_watch import desktop_notify
                desktop_notify("pipeline_paused", control.get("message", "任务暂停，请打开内容工作台"))
            atomic_json(self.root / "server_control.json", control)
            try:
                state = self.remote_json(
                    self.remote + "/collectors/deepseek/deepseek_session.json"
                )
            except FileNotFoundError:
                state = {"status": "unknown"}
            from .session_watch import SessionReporter

            SessionReporter(self.root / "session").publish(state)
            result = self.sync_approved()
            hashes = []
            for path in (self.root / "articles").glob("*/*/*/receipt.json"):
                receipt = read(path)
                if not receipt.get("files"):
                    raise ValueError("Archive receipt has no file hashes")
                for name, digest in receipt["files"].items():
                    if (
                        safe_name(name) != name
                        or file_hash(path.parent / name) != digest
                    ):
                        raise ValueError("Local archive integrity check failed")
                if not (path.parent / "withdrawal.json").exists():
                    hashes.append(receipt["word_sha256"])
            acknowledgement = {
                "client": self.client_id,
                "checked_epoch": time.time(),
                "integrity": "verified",
                "word_hashes": sorted(set(hashes)),
            }
            folder = self.remote + "/local_archive_ack"
            try:
                self.sftp.stat(folder)
            except FileNotFoundError:
                self.sftp.mkdir(folder, mode=0o700)
            target = folder + "/" + self.client_id + ".json"
            with self.sftp.open(target + ".transfer", "w") as stream:
                stream.write(json.dumps(acknowledgement).encode("utf8"))
            self.sftp.posix_rename(target + ".transfer", target)
            atomic_json(self.root / "archive_ack.json", acknowledgement)
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", default=60, type=int)
    args = parser.parse_args()
    root = Path(read(args.config)["local_root"])
    with process_lock(root / "archive_daemon.lock"):
        while True:
            client = None
            health = root / "archive_health.json"
            previous = read(health) if health.exists() else {}
            try:
                client = ArchiveClient(args.config)
                result = client.sync()
                atomic_json(health, observation(previous, result))
            except Exception as error:  # noqa: BLE001 -- transport boundary preserves state
                atomic_json(health, observation(previous, error=error))
                if args.once:
                    return 2
            finally:
                if client:
                    client.close()
            if args.once:
                print(json.dumps(result, ensure_ascii=False))
                return 0
            time.sleep(max(15, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
