#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
bash check-host.sh
docker compose config --quiet
image=$(docker compose config --images | head -n 1)
if ! docker image inspect "$image" >/dev/null 2>&1; then
  docker compose pull
fi
docker compose up -d
for ((attempt=0; attempt<120; attempt++)); do
  cid=$(docker compose ps -a -q redroid)
  state=$(docker inspect --format '{{.State.Status}}' "$cid")
  if [ "$state" != running ]; then
    docker compose logs --tail 100 redroid
    echo "Android container state: $state" >&2
    exit 1
  fi
  boot=$(docker compose exec -T redroid /system/bin/getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
  if [ "$boot" = 1 ]; then
    docker compose exec -T redroid /system/bin/getprop ro.product.cpu.abilist
    echo 'Android boot completed. Next: verify ADB, install the official APK, and test login.'
    exit 0
  fi
  sleep 2
done
docker compose logs --tail 100 redroid
echo 'Android did not finish booting within 240 seconds.' >&2
exit 1
