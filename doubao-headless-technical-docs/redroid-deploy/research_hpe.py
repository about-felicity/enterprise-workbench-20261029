import requests,pathlib
repo='supremegamers/vendor_intel_proprietary_houdini'
j=requests.get(f'https://api.github.com/repos/{repo}/git/trees/hpe-14?recursive=1',timeout=30).json()
print('sha',j.get('sha'))
for x in j.get('tree',[]):
 if x['type']=='blob': print(x['path'],x.get('size'))
for p in ['houdini.mk','Android.mk','README.md']:
 r=requests.get(f'https://raw.githubusercontent.com/{repo}/hpe-14/{p}',timeout=20)
 if r.ok: print(p,r.text[:6000])
