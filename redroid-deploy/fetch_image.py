"""Download verified Docker Hub blobs in parallel and create a portable image archive."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import sys
import base64
import subprocess
import os

import requests

ROOT = Path(__file__).resolve().parent / "artifacts" / "image"
ROOT.mkdir(parents=True, exist_ok=True)
REPOSITORY = "erstt/redroid"
TAG = os.environ.get("REDROID_IMAGE_TAG", "13.0.0_ndk_ChromeOS")
base = f"https://registry-1.docker.io/v2/{REPOSITORY}"
session = requests.Session()
sources = {}
headers = {}
if len(sys.argv) > 1:
    source_config = json.loads(Path(sys.argv[1]).read_text())
    TAG = source_config.get("tag", TAG)
    manifest_bytes = base64.b64decode(source_config["manifest"])
    expected_digest = source_config["digest"]
    sources = source_config["sources"]
else:
    token = session.get("https://auth.docker.io/token", params={
        "service": "registry.docker.io", "scope": f"repository:{REPOSITORY}:pull"
    }, timeout=30).json()["token"]
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    response = session.get(f"{base}/manifests/{TAG}", headers=headers, timeout=30)
    response.raise_for_status()
    manifest_bytes = response.content
    expected_digest = response.headers.get("Docker-Content-Digest")
manifest = json.loads(manifest_bytes)
manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
if expected_digest != manifest_digest:
    raise ValueError("Manifest digest mismatch")
print("Manifest verified:", manifest_digest, flush=True)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while data := source.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def download(blob):
    digest = blob["digest"].split(":", 1)[1]
    path = ROOT / digest
    if path.exists() and file_hash(path) == digest:
        return path
    blob_url = sources.get(blob["digest"], f"{base}/blobs/{blob['digest']}")
    if blob["size"] < 1024 * 1024:
        r = session.get(blob_url, headers=headers, timeout=30)
        r.raise_for_status()
        path.write_bytes(r.content)
    else:
        r = session.get(blob_url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()
        url = r.url
        r.close()
        size = blob["size"]
        chunk_size = 8 * 1024 * 1024
        ranges = [(i, min(i + chunk_size, size) - 1) for i in range(0, size, chunk_size)]
        def part(bounds):
            start, end = bounds
            part_path = ROOT / f"{digest}.{start}.part"
            if part_path.exists() and part_path.stat().st_size == end - start + 1:
                return part_path
            for attempt in range(4):
                try:
                    if sources:
                        result = subprocess.run([
                            "curl", "-fsSL", "--connect-timeout", "10", "--max-time", "90",
                            "--range", f"{start}-{end}", "--output", str(part_path), url
                        ], capture_output=True, timeout=100)
                        if result.returncode:
                            raise RuntimeError("curl range failed: " + result.stderr.decode("utf-8", "replace")[-200:])
                    else:
                        with requests.get(url, headers={"Range": f"bytes={start}-{end}"},
                                          timeout=(15, 60), stream=True) as result:
                            result.raise_for_status()
                            if result.status_code != 206 or not result.headers.get("Content-Range", "").startswith(f"bytes {start}-{end}/"):
                                raise ValueError("Server did not honor range")
                            with part_path.open("wb") as output:
                                for data in result.iter_content(256 * 1024):
                                    output.write(data)
                    if part_path.stat().st_size != end - start + 1:
                        raise ValueError("Incomplete range")
                    return part_path
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(attempt + 1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            parts = []
            for index, part_path in enumerate(pool.map(part, ranges), 1):
                parts.append(part_path)
                if index % 8 == 0 or index == len(ranges):
                    print(digest[:12], f"{index}/{len(ranges)} chunks", flush=True)
        with path.open("wb") as output:
            for part_path in parts:
                with part_path.open("rb") as source:
                    while data := source.read(1024 * 1024):
                        output.write(data)
                part_path.unlink()
    if file_hash(path) != digest:
        path.unlink()
        raise ValueError("Blob digest mismatch")
    print("Blob verified:", digest, flush=True)
    return path


blobs = [manifest["config"], *manifest["layers"]]
paths = [download(blob) for blob in blobs]
archive = ROOT.parent / ("redroid-image.tar" if TAG == "13.0.0_ndk_ChromeOS" else f"redroid-{TAG}.tar")
with tarfile.open(archive, "w") as tar:
    def add_json(name, data):
        encoded = json.dumps(data).encode()
        info = tarfile.TarInfo(name)
        info.size = len(encoded)
        tar.addfile(info, io.BytesIO(encoded))
    for blob, path in zip(blobs, paths):
        tar.add(path, arcname="blobs/sha256/" + path.name)
    mpath = "blobs/sha256/" + manifest_digest.split(":", 1)[1]
    info = tarfile.TarInfo(mpath)
    info.size = len(manifest_bytes)
    tar.addfile(info, io.BytesIO(manifest_bytes))
    add_json("oci-layout", {"imageLayoutVersion": "1.0.0"})
    add_json("index.json", {"schemaVersion": 2, "manifests": [{
        "mediaType": manifest["mediaType"], "digest": manifest_digest,
        "size": len(manifest_bytes), "platform": {"os": "linux", "architecture": "amd64"},
        "annotations": {"io.containerd.image.name": f"docker.io/{REPOSITORY}:{TAG}",
                        "org.opencontainers.image.ref.name": f"docker.io/{REPOSITORY}:{TAG}"}
    }]})
    add_json("manifest.json", [{"Config": "blobs/sha256/" + paths[0].name,
                               "RepoTags": [f"docker.io/{REPOSITORY}:{TAG}"],
                               "Layers": ["blobs/sha256/" + p.name for p in paths[1:]]}])
print("Archive:", archive, archive.stat().st_size, flush=True)
