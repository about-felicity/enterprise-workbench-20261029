"""下载前端依赖到本地，解决国内CDN访问问题"""
import urllib.request
import os

VENDOR_DIR = os.path.join(os.path.dirname(__file__), "vendor")
os.makedirs(VENDOR_DIR, exist_ok=True)

# 需要下载的文件
files = {
    # Tailwind CSS Play CDN (通过 jsdelivr 的 @tailwindcss/browser v4)
    "tailwind.js": "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.1.7/dist/index.global.js",
    # Font Awesome CSS (通过 jsdelivr，国内有 CDN 节点)
    "fontawesome.css": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css",
}

for filename, url in files.items():
    filepath = os.path.join(VENDOR_DIR, filename)
    if os.path.exists(filepath):
        print(f"[跳过] {filename} 已存在")
        continue
    print(f"[下载] {filename} ← {url}")
    try:
        urllib.request.urlretrieve(url, filepath)
        print(f"[完成] {filename} ({os.path.getsize(filepath)} bytes)")
    except Exception as e:
        print(f"[失败] {filename}: {e}")

print("\n所有依赖下载完成。")
