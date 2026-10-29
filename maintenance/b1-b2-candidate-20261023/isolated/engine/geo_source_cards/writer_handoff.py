"""Validate a Feishu local-file completion marker without resending work."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

from .editorial_pipeline import finish
from .runtime import atomic_json, process_lock


def word_matches_draft(word_path, draft):
    from zipfile import ZipFile

    with ZipFile(word_path) as document:
        tree = ET.fromstring(document.read("word/document.xml"))
    plain = (
        "".join(tree.itertext())
        if not tree.tag.endswith("document")
        else "".join(
            node.text or ""
            for node in tree.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
            )
        )
    )
    expected = re.sub(r"[\W_]+", "", draft).casefold()
    actual = re.sub(r"[\W_]+", "", plain).casefold()
    ratio = SequenceMatcher(None, expected, actual, autojunk=False).ratio()
    if len(actual) < len(expected) * 0.85 or ratio < 0.90:
        raise ValueError(
            "Word text is missing or differs from the complete Markdown draft"
        )
    return {
        "normalized_text_similarity": round(ratio, 4),
        "markdown_characters": len(expected),
        "word_characters": len(actual),
    }


def verify_delivery(root):
    root = Path(root)
    job = json.loads((root / "writing_job.json").read_text(encoding="utf8"))
    marker = root / "writer_done.json"
    if not marker.exists():
        return None
    done = json.loads(marker.read_text(encoding="utf-8-sig"))
    expected = {
        "job_id": job["job_id"],
        "prompt_sha256": job["prompt_sha256"],
        "status": "completed",
        "draft_file": "draft.md",
        "word_file": "article.docx",
    }
    if any(done.get(key) != value for key, value in expected.items()):
        raise ValueError("Writer completion marker does not match this job")
    prompt = (root / "writing_prompt.md").read_text(encoding="utf8")
    if hashlib.sha256(prompt.encode()).hexdigest() != job["prompt_sha256"]:
        raise ValueError("Writer prompt has changed")
    for name in ("draft.md", "article.docx"):
        file = root / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size < 20:
            raise ValueError("Writer delivery is missing, empty or symlinked: " + name)
    from zipfile import ZipFile

    with ZipFile(root / "article.docx") as document:
        if "word/document.xml" not in document.namelist():
            raise ValueError("Delivered Word is not a valid DOCX")
    word_matches_draft(
        root / "article.docx",
        (root / "draft.md").read_text(encoding="utf-8-sig"),
    )
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Wait for Feishu file delivery, check draft and export canonical Word; never submit a task"
    )
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--timeout", default=1800, type=int)
    parser.add_argument("--interval", default=5, type=int)
    parser.add_argument("--no-word", action="store_true")
    args = parser.parse_args(argv)
    if args.interval < 1 or args.timeout < args.interval:
        parser.error("Invalid polling interval/timeout")
    with process_lock(args.job_dir / "writer_watch.lock"):
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            done = verify_delivery(args.job_dir)
            if done:
                # The marker must be written last; also observe the same file bytes twice.
                paths = [
                    args.job_dir / name
                    for name in ("draft.md", "article.docx", "writer_done.json")
                ]
                before = [hashlib.sha256(p.read_bytes()).digest() for p in paths]
                time.sleep(args.interval)
                verify_delivery(args.job_dir)
                if before != [hashlib.sha256(p.read_bytes()).digest() for p in paths]:
                    continue
                job = finish(
                    args.job_dir,
                    args.job_dir / "draft.md",
                    export_word=not args.no_word,
                )
                atomic_json(
                    args.job_dir / "writer_watch.json",
                    {"status": job["status"], "job_id": job["job_id"]},
                )
                print(json.dumps(job, ensure_ascii=False, indent=2))
                return 0 if job["status"] == "ready_for_editorial_review" else 2
            time.sleep(args.interval)
        atomic_json(
            args.job_dir / "writer_watch.json",
            {"status": "timed_out_unknown_delivery", "resubmitted": False},
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
