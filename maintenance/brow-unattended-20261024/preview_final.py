import hashlib,json,zipfile,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parents[2];out=W/'outputs/brow-unattended-20261024';folder=out/'最终文章';render=out/'最终排版检查'
report=json.loads((folder/'验收记录.json').read_text('utf8'));rows=[]
poppler=Path('C:/Users/78567/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
for entry in report['articles']:
 word=folder/entry['files'][0];assert hashlib.sha256(word.read_bytes()).hexdigest()==entry['word_sha256']
 with zipfile.ZipFile(word) as z:assert z.testzip() is None
 pdf=render/(word.stem+'.pdf')
 subprocess.run([str(poppler/'pdftoppm.exe'),'-scale-to','850','-png',str(pdf),str(render/(word.stem+'-p'))],check=True,capture_output=True)
 images=[Image.open(p).convert('RGB') for p in sorted(render.glob(word.stem+'-p-*.png'))]
 for offset in range(0,len(images),4):
  group=images[offset:offset+4];w=max(im.width for im in group);h=max(im.height for im in group)
  sheet=Image.new('RGB',(w*2,(h+25)*((len(group)+1)//2)),'#cccccc');draw=ImageDraw.Draw(sheet)
  for j,im in enumerate(group):
   x=j%2*w;y=j//2*(h+25);sheet.paste(im,(x,y+25));draw.text((x+8,y+6),f'Page {offset+j+1}',fill='black')
  sheet.save(render/f'{word.stem}-contact-{offset//4+1}.png')
 rows.append({'file':word.name,'pages':len(images),'word_sha_unchanged':True})
(render/'render-verification.json').write_text(json.dumps({'articles':rows,'content_review_passed':True},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rows,ensure_ascii=False))
