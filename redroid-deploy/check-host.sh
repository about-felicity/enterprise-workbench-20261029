#!/usr/bin/env bash
set -euo pipefail
printf 'Kernel: '; uname -r
printf 'Architecture: '; uname -m
if [ "$(uname -m)" != x86_64 ]; then
  echo 'This ERSTT image requires an x86_64 server.' >&2
  exit 1
fi
docker info --format 'Docker: {{.ServerVersion}} / {{.KernelVersion}}'
docker compose version
free -h
df -h .
if ! grep -qw binder /proc/filesystems && [ ! -e /dev/binder ]; then
  if [ "$(id -u)" -eq 0 ]; then
    modprobe binder_linux devices=binder,hwbinder,vndbinder
  else
    sudo -n modprobe binder_linux devices=binder,hwbinder,vndbinder
  fi
fi
if ! grep -qw binder /proc/filesystems && [ ! -e /dev/binder ]; then
  echo 'Binder is unavailable. Install matching kernel modules or use a Binder-enabled kernel.' >&2
  exit 1
fi
echo 'Binder available; Android boot still needs a runtime check.'
