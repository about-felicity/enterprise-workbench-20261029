"""Local human skeleton inspection and confirmation; no API calls."""
import argparse
import json
from pathlib import Path

from ..runtime import process_lock
from ..staged_editorial import read
from .common import cache_root
from .structure_parser import approve
from .integration import sync_approvals


def main():
    parser = argparse.ArgumentParser(description="Inspect/approve V2 semantic skeletons without model calls")
    parser.add_argument("command", choices=["pending", "approve"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--key")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--reviewer")
    parser.add_argument("--edited-skeleton", type=Path)
    args = parser.parse_args()
    cache = cache_root(args.root)
    if args.command == "pending":
        result = [read(p) for p in (cache / "skeleton").glob("*.json") if not read(p).get("approval")]
    else:
        if not all((args.key, args.expected_sha256, args.reviewer)):
            parser.error("approve requires --key, --expected-sha256 and --reviewer")
        result = approve(cache, args.key, args.expected_sha256, args.reviewer,
                         skeleton=read(args.edited_skeleton) if args.edited_skeleton else None)
        with process_lock(args.root / "coordinator.lock", blocking=True):
            sync_approvals(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
