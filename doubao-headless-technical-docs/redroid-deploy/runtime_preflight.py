"""Verify the tested runtime before allowing unattended UI submission."""
import argparse
import datetime
import json
import re
import subprocess
import time

IMAGE_ID = 'sha256:18244ad4ab1c36047438bb9c524d8f8d6f848ee8d7537a98483a26c5dda7601f'
BRIDGE_SHA = '5ef64035ec89bca3d5e33b9f3b6556f98f6c11d11957387d403ae4a4d7cc40ec'

def verify(container):
    def android(*args):
        return subprocess.check_output(['docker', 'exec', container, *args],
                                       text=True, timeout=15).strip()
    info = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=15))[0]
    if info['Image'] != IMAGE_ID:
        raise RuntimeError('Image differs from the tested Android13/Houdini14 runtime')
    if not info['State']['Running']:
        subprocess.run(['docker', 'start', container], check=True, timeout=30)
    for _ in range(60):
        if android('/system/bin/getprop', 'sys.boot_completed') == '1':
            break
        time.sleep(2)
    else:
        raise RuntimeError('Android did not finish booting within 120 seconds')
    if android('/system/bin/getprop', 'ro.build.version.sdk') != '33':
        raise RuntimeError('Unexpected Android SDK')
    if android('/system/bin/getprop', 'ro.dalvik.vm.native.bridge') != 'libhoudini.so':
        raise RuntimeError('Unexpected native bridge')
    if android('sha256sum', '/system/lib64/libhoudini.so').split()[0] != BRIDGE_SHA:
        raise RuntimeError('Native bridge checksum differs from the tested build')
    package = android('dumpsys', 'package', 'com.larus.nova')
    if not re.search(r'\bversionCode=15020040\b', package):
        raise RuntimeError('Doubao APK changed; compatibility must be revalidated')
    # Upstream reports expiry on 2028-07-01. Stop before that boundary so a
    # future expiring translator cannot silently become a crash/restart loop.
    if datetime.datetime.now(datetime.timezone.utc).date() >= datetime.date(2028, 6, 1):
        raise RuntimeError('Houdini expiry is approaching; validate a newer runtime')
    android('svc', 'bluetooth', 'disable')
    print('Runtime verified: Android13 / Houdini14 com1.3 / Doubao15.2.0', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--container', default='doubao-hpe14-13-test')
    verify(parser.parse_args().container)
