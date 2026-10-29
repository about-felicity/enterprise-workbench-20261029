import requests,base64,pathlib
root=pathlib.Path('redroid-deploy/artifacts'); root.mkdir(exist_ok=True)
u='https://android.googlesource.com/platform/frameworks/libs/binary_translation/+/refs/heads/main/guest_abi/arm64/include/berberis/guest_abi/guest_params_arch.h?format=TEXT'
r=requests.get(u,timeout=30); print('AOSP',r.status_code)
if r.ok:
 s=base64.b64decode(r.content).decode(); (root/'guest_params_arch.h').write_text(s)
 for i,line in enumerate(s.splitlines(),1):
  if 240<=i<=310: print(i,line)
r=requests.get('https://api.github.com/repos/ERSTT/redroid/issues?state=all&per_page=100',timeout=30)
print('issues',r.status_code)
if r.ok:
 for x in r.json(): print(x['number'],x['title'],(x.get('body') or '')[:2500])
