"""SSH helper; reads local_server.txt without putting credentials in command arguments."""
import argparse
from pathlib import Path
import re
import sys
import time
import socket

import paramiko

ROOT = Path(__file__).resolve().parent


def connect():
    config = (ROOT.parent / "local_server.txt").read_text(encoding="utf-8-sig")
    target = re.search(r"ssh\s+([\w.-]+)@([\w.-]+)", config)
    secret = re.search(r"password\s*:\s*(.+)", config)
    if not target or not secret:
        raise ValueError("Expected ssh USER@HOST and password: in local_server.txt")
    password = secret.group(1).strip()
    client = paramiko.SSHClient()
    hosts = ROOT / "server_known_hosts"
    if hosts.exists():
        client.load_host_keys(str(hosts))
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(target.group(2), username=target.group(1), password=password,
                   timeout=15, auth_timeout=15, banner_timeout=15,
                   look_for_keys=False, allow_agent=False)
    transport_socket = client.get_transport().sock
    transport_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    transport_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    transport_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    client.save_host_keys(str(hosts))
    return client, password


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?")
    parser.add_argument("--sudo", action="store_true")
    parser.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"))
    parser.add_argument("--download", nargs=2, metavar=("REMOTE", "LOCAL"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    client, password = connect()
    try:
        if args.upload or args.download:
            with client.open_sftp() as sftp:
                if args.upload:
                    sftp.put(*args.upload)
                else:
                    sftp.get(*args.download)
            print("Transfer complete")
            return
        if not args.command:
            parser.error("command or transfer required")
        command = args.command
        if args.sudo:
            import shlex
            command = "sudo -S -p '' -- bash -lc " + shlex.quote(command)
        stdin, stdout, stderr = client.exec_command(command, timeout=args.timeout)
        if args.sudo:
            stdin.write(password + "\n")
            stdin.flush()
        stdin.channel.shutdown_write()
        channel = stdout.channel
        deadline = time.monotonic() + args.timeout
        while True:
            if channel.recv_ready():
                print(channel.recv(65536).decode("utf-8", "replace"), end="", flush=True)
            if channel.recv_stderr_ready():
                print(channel.recv_stderr(65536).decode("utf-8", "replace"), end="", flush=True)
            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                break
            if time.monotonic() > deadline:
                channel.close()
                raise TimeoutError("Remote command timed out")
            time.sleep(0.1)
        raise SystemExit(channel.recv_exit_status())
    finally:
        client.close()


if __name__ == "__main__":
    main()
