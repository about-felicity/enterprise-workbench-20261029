#!/usr/bin/env bash
set -euo pipefail
cd /home/user/redroid-doubao
image=erstt/redroid:15.0.0_ndk_AVD
if [ "$(ps -p 45104 -o args= 2>/dev/null || true)" = "docker pull $image" ]; then
  kill 45104
fi
nice -n 10 ionice -c 2 -n 7 docker load -i artifacts/redroid-15.0.0_ndk_AVD.tar
docker image inspect "$image" --format '{{json .RepoDigests}}'
docker compose -f compose.android15.yaml config --quiet
docker compose -f compose.android15.yaml up -d --pull never
for ((attempt=0; attempt<120; attempt++)); do
  boot=$(docker compose -f compose.android15.yaml exec -T redroid /system/bin/getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
  if [ "$boot" = 1 ]; then
    docker compose -f compose.android15.yaml exec -T redroid /system/bin/getprop ro.build.version.release
    docker compose -f compose.android15.yaml exec -T redroid /system/bin/getprop ro.product.cpu.abilist
    docker compose -f compose.android15.yaml cp doubao.apk redroid:/data/local/tmp/doubao.apk
    docker compose -f compose.android15.yaml exec -T redroid /system/bin/pm install -r /data/local/tmp/doubao.apk
    echo ANDROID15_INSTALLED
    exit 0
  fi
  sleep 2
done
docker compose -f compose.android15.yaml logs --tail 100
exit 1
