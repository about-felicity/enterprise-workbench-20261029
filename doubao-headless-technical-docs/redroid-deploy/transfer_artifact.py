"""Transfer one large deployment artifact over parallel SSH channels and verify its hash."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import shlex
import sys
import threading
import time

from remote import connect

sys.stdout.reconfigure(encoding="utf-8")
parser = argparse.ArgumentParser()
parser.add_argument("local", type=Path)
parser.add_argument("remote")
args = parser.parse_args()
if not args.remote.startswith("/home/user/redroid-doubao/"):
    raise ValueError("Destination must be within this deployment directory")
source = args.local.resolve()
size = source.stat().st_size
chunk_size = 64 * 1024 * 1024
ranges = [(start, min(chunk_size, size - start)) for start in range(0, size, chunk_size)]
thread_state = threading.local()
clients = []
clients_lock = threading.Lock()
started = time.monotonic()


def put_part(bounds):
    start, count = bounds
    if not hasattr(thread_state, "client"):
        thread_state.client, _ = connect()
        with clients_lock:
            clients.append(thread_state.client)
    client = thread_state.client
    target = args.remote + f".part-{start}"
    with client.open_sftp() as sftp:
        try:
            if sftp.stat(target).st_size == count:
                return target
        except FileNotFoundError:
            pass
    channel = client.get_transport().open_session()
    channel.exec_command("nice -n 10 cat > " + shlex.quote(target))
    with source.open("rb") as file:
        file.seek(start)
        remaining = count
        while remaining:
            data = file.read(min(256 * 1024, remaining))
            if not data:
                raise IOError("Source ended early")
            channel.sendall(data)
            remaining -= len(data)
    channel.shutdown_write()
    if channel.recv_exit_status() != 0:
        raise IOError("Remote write failed")
    channel.close()
    print(f"Transferred segment {start // chunk_size + 1}/{len(ranges)}", flush=True)
    return target


try:
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(put_part, ranges))
    digest = hashlib.sha256()
    with source.open("rb") as file:
        while data := file.read(1024 * 1024):
            digest.update(data)
    code = "\n".join([
        "from pathlib import Path", "import hashlib",
        f"parts = {parts!r}", f"destination = Path({args.remote!r})",
        "digest = hashlib.sha256()",
        "with destination.open('wb') as output:",
        "    for name in parts:",
        "        with Path(name).open('rb') as source:",
        "            while data := source.read(1048576):",
        "                output.write(data)", "                digest.update(data)",
        f"assert digest.hexdigest() == {digest.hexdigest()!r}, 'Archive digest mismatch'",
        "for name in parts: Path(name).unlink()",
        "print('Archive SHA256 verified:', digest.hexdigest())",
    ])
    client, _ = connect()
    try:
        _, output, error = client.exec_command("python3 -c " + shlex.quote(code), timeout=300)
        print(output.read().decode("utf-8"), end="", flush=True)
        errors = error.read().decode("utf-8")
        status = output.channel.recv_exit_status()
        if status:
            raise IOError(errors)
    finally:
        client.close()
    elapsed = time.monotonic() - started
    print(f"Complete: {size / 1048576:.1f} MiB, {elapsed:.1f}s, {size / 1048576 / elapsed:.2f} MiB/s", flush=True)
finally:
    for client in clients:
        client.close()
