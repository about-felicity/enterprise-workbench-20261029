import urllib.request
import os

vendor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "vendor")
os.makedirs(vendor, exist_ok=True)

# 下载 Tailwind v3 Play CDN (原始脚本)
url = "https://cdn.tailwindcss.com"
dst = os.path.join(vendor, "tailwind.js")
print(f"Downloading Tailwind from {url} ...")
try:
    urllib.request.urlretrieve(url, dst)
    print(f"OK: {os.path.getsize(dst)} bytes")
except Exception as e:
    print(f"FAIL: {e}")

# 下载 Font Awesome CSS (用 jsdelivr, 国内有节点)
url2 = "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css"
dst2 = os.path.join(vendor, "fontawesome.css")
print(f"Downloading Font Awesome from {url2} ...")
try:
    urllib.request.urlretrieve(url2, dst2)
    print(f"OK: {os.path.getsize(dst2)} bytes")
except Exception as e:
    print(f"FAIL: {e}")
    # fallback to bootcdn
    url3 = "https://cdn.bootcdn.net/ajax/libs/font-awesome/6.5.1/css/all.min.css"
    print(f"Trying bootcdn: {url3} ...")
    try:
        urllib.request.urlretrieve(url3, dst2)
        print(f"OK: {os.path.getsize(dst2)} bytes")
    except Exception as e2:
        print(f"FAIL2: {e2}")

print("Done.")
