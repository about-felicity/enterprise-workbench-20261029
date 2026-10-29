import hashlib,json,zipfile,subprocess,re
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image,ImageOps,ImageDraw
W=Path(__file__).resolve().parents[2];out=W/'outputs/brow-unattended-20261024';report=json.loads((out/'稿件/测试记录.json').read_text('utf8'));rows=[]
poppler=Path('C:/Users/78567/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin')
for entry in report['drafts']:
 word=out/'稿件'/entry['word'];assert hashlib.sha256(word.read_bytes()).hexdigest()==entry['word_sha256']
 with zipfile.ZipFile(word) as z:assert z.testzip() is None
 pdf=out/'rendered'/(word.stem+'.pdf');images=[]
 subprocess.run([str(poppler/'pdftoppm.exe'),'-scale-to','1000','-png',str(pdf),str(out/'rendered'/(word.stem+'-p'))],check=True,capture_output=True)
 for path in sorted((out/'rendered').glob(word.stem+'-p-*.png')):images.append(Image.open(path).convert('RGB'))
 for offset in range(0,len(images),4):
  group=images[offset:offset+4];w=max(im.width for im in group);h=max(im.height for im in group)
  sheet=Image.new('RGB',(w*2,(h+25)*((len(group)+1)//2)), '#cccccc');draw=ImageDraw.Draw(sheet)
  for j,im in enumerate(group):
   x=j%2*w;y=j//2*(h+25);sheet.paste(im,(x,y+25));draw.text((x+8,y+6),f'Page {offset+j+1}',fill='black')
  sheet.save(out/'rendered'/f'{word.stem}-contact-{offset//4+1}.png')
 with zipfile.ZipFile(word) as z:text=''.join(ET.fromstring(z.read('word/document.xml')).itertext())
 rows.append({'file':entry['word'],'pages':len(images),'word_sha_unchanged':True,'word_text_chars':len(text)})
(out/'rendered/render-verification.json').write_text(json.dumps({'articles':rows,'content_review_passed':False},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rows,ensure_ascii=False))
