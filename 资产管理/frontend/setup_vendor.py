#!/usr/bin/env python3
"""下载所有前端静态资源到本地，彻底去除 CDN 依赖"""
import urllib.request
import os
import sys

FRONTEND = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(FRONTEND, "vendor")
os.makedirs(VENDOR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def download(url, filename):
    path = os.path.join(VENDOR, filename)
    if os.path.exists(path):
        print(f"  跳过（已存在）: {filename}")
        return True
    print(f"  下载: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        urllib.request.urlretrieve(url, path)
        size = os.path.getsize(path)
        print(f"  完成: {filename} ({size:,} bytes)")
        return True
    except Exception as e:
        print(f"  失败: {e}")
        return False

print("=== 下载前端资源到本地 ===\n")

# 1. Tailwind CSS Play CDN v3 (多源尝试)
print("[1/3] Tailwind CSS Play CDN:")
tailwind_urls = [
    "https://cdn.tailwindcss.com",
    "https://cdn.jsdelivr.net/gh/tailwindlabs/tailwindcss-play-cdn@main/tailwind.js",
]
ok = False
for u in tailwind_urls:
    if download(u, "tailwind.js"):
        ok = True
        break
if not ok:
    print("  Tailwind CDN 全部失败，将使用纯 CSS 方案")
    sys.exit(1)

# 2. Font Awesome CSS
print("\n[2/3] Font Awesome CSS:")
download("https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css", "fontawesome.css")

# 3. Font Awesome 字体文件
print("\n[3/3] Font Awesome 字体:")
font_base = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/webfonts"
fonts = [
    "fa-solid-900.woff2",
    "fa-regular-400.woff2", 
    "fa-brands-400.woff2",
]
for f in fonts:
    download(f"{font_base}/{f}", f)

print("\n=== 完成 ===")
