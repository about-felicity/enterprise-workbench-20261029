import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(sys.argv[1]);rows=json.loads((root/'render-manifest.json').read_text('utf8'));out=root/'contacts';out.mkdir(exist_ok=True);manifest=[]
for row in rows:
 folder=Path(row['directory']);pages=sorted(folder.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
 for offset in range(0,len(pages),2):
  pair=pages[offset:offset+2];images=[Image.open(p).convert('RGB') for p in pair]
  canvas=Image.new('RGB',(sum(i.width for i in images),max(i.height for i in images)+25),'#d9dee0');draw=ImageDraw.Draw(canvas);x=0
  for p,img in zip(pair,images):
   draw.text((x+8,5),row['key']+' / '+p.stem,fill='black');canvas.paste(img,(x,25));x+=img.width
  path=out/(row['key']+'-'+str(offset+1)+'.png');canvas.save(path);manifest.append(str(path.resolve()))
(root/'contact-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'images':len(manifest),'pages':sum(r['pages'] for r in rows)}))
