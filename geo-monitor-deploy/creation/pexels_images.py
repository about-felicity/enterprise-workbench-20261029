"""Pexels search with private credentials and bounded local caching."""
import json,os,time,hashlib,re
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode,urlsplit
from geo_source_cards.runtime import process_lock,atomic_json,atomic_write
from . import runtime

KEY=Path('/opt/monitor/geo-content/secrets/pexels.key')
REUSE_INTERVAL=7*24*60*60
SCENE_ALTERNATIVES = {
    'woman touching hair scalp': (
        'woman washing hair shampoo', 'woman scalp massage hair care', 'woman shampooing hair in shower',
    ),
    'woman touching face skincare close up': (
        'woman applying face serum skincare', 'woman applying moisturizer face', 'woman clean face skin care portrait',
    ),
    'woman long hair close up': (
        'woman brushing long hair beauty', 'woman applying hair oil',
    ),
}

def monochrome_label(photo):
    return bool(re.search(r'black[\s-]*(?:and|&)[\s-]*white|monochrom|grayscale|greyscale|\bb&w\b',photo.get('alt','').lower()))

def is_color(path):
    from PIL import Image
    path=Path(path);receipt=path.with_suffix('.color.json');stamp=path.stat().st_mtime_ns
    saved=runtime.read(receipt)
    if saved.get('mtime_ns')==stamp:return saved['color']
    with Image.open(path) as im:
        im=im.convert('RGB');im.thumbnail((96,96));chroma=[max(p)-min(p) for p in im.getdata()]
    color=sum(c>=12 for c in chroma)/len(chroma)>=0.03 and sum(chroma)/len(chroma)>=4
    atomic_json(receipt,{'mtime_ns':stamp,'color':color})
    return color

def search(query,page=1):
    query=str(query).strip()
    if not query or len(query)>160:raise ValueError('请输入160字以内的场景关键词')
    cache=runtime.BASE/'pexels';cache.mkdir(parents=True,exist_ok=True)
    page=int(page)
    if not 1<=page<=10:raise ValueError('图片检索页码无效')
    path=cache/(hashlib.sha256((query.casefold()+':page:'+str(page)+':size:80').encode()).hexdigest()+'.json')
    with process_lock(path.with_suffix('.lock'),blocking=True):
        saved=runtime.read(path)
        if saved and time.time()-saved['at']<86400:return saved
        retry=path.with_suffix('.search-retry.json')
        if runtime.read(retry).get('until',0)>time.time():raise TimeoutError('图片检索暂时退避')
        key=os.environ.get('PEXELS_API_KEY') or (KEY.read_text().strip() if KEY.exists() else '')
        if not key:raise ValueError('Pexels API 尚未配置')
        req=Request('https://api.pexels.com/v1/search?'+urlencode({'query':query,'page':page,'per_page':80,'orientation':'landscape','size':'medium'}),headers={'Authorization':key,'User-Agent':'EnterpriseContentStudio/1.0','Accept':'application/json'})
        try:
            with urlopen(req,timeout=12) as response:raw=json.load(response)
        except Exception as error:
            atomic_json(retry,{'until':time.time()+30,'error':type(error).__name__})
            raise
        photos=[]
        for photo in raw.get('photos',[]):
            url=photo.get('src',{}).get('large','');photo_page=photo.get('url','')
            if urlsplit(url).hostname!='images.pexels.com' or urlsplit(photo_page).hostname not in ('www.pexels.com','pexels.com'):continue
            photos.append({'id':int(photo['id']),'url':photo_page,'image_url':url,'photographer':str(photo.get('photographer','')),'alt':str(photo.get('alt',''))})
        result={'at':time.time(),'query':query,'photos':photos,'has_more':bool(raw.get('next_page'))}
        atomic_json(path,result)
        return result
def scene_query(name):
    for terms,query in [
        (('护发精油','护发素'),'woman long hair close up'),
        (('染发','黑茶色'),'woman hair portrait close up'),
        (('洗发','防脱','头皮','道和小红瓶'),'woman touching hair scalp'),
        (('睫毛',),'woman eyelashes close up'),
        (('眉毛',),'woman eyebrows close up'),
        (('眼霜',),'woman eye skin close up'),
        (('护手','手部'),'woman applying hand cream'),
        (('身体乳','沐浴'),'woman applying body lotion'),
        (('防晒',),'woman applying sunscreen face'),
        (('面膜','面霜','精华','卸妆','洁面','洗面','爽肤'),'woman touching face skincare close up'),
        (('造型','喷雾'),'woman long hair beauty portrait'),
    ]:
        if any(t in name for t in terms):return query
    return ''

def person_candidates(photos,query):
    results=[]
    for photo in photos:
        alt=photo.get('alt','').lower()
        if monochrome_label(photo):continue
        if re.search(r'\b(bottle|bottles|jar|packaging|mannequin|doll|statue|cat|dog|animal)\b|still life|flat lay|product shot',alt):continue
        if 'eye' in query and re.search(r'extension|false eyelash|eye patch|eye mask|under.eye patch|under.eye mask|frost|snow|floral|branches|procedure',alt):continue
        if not re.search(r'\b(woman|women|female|girl|person|people|model|face|facial|eye|eyes|eyelash|eyelashes|eyebrow|eyebrows|hands|hand)\b',alt):continue
        relevant=('hair','scalp') if 'hair' in query else ('eye','eyes','eyelash','eyelashes') if 'eye' in query else ('skin','face','facial','hand','hands','lotion')
        if not any(term in alt for term in relevant):continue
        score=3*bool(re.search(r'close.up|macro',alt))+2*bool(re.search(r'natural|skincare|skin care|beauty|applying|touching',alt))
        if 'eyebrow' in query:score+=2*bool(re.search(r'eyebrow',alt))
        if 'eyelash' in query:score+=2*bool(re.search(r'eyelash',alt))
        results.append((score,photo))
    if not results:return []
    best=max(score for score,_ in results)
    return [photo for score,photo in results if score>=best-1]

def claim_photo(base,assignment,candidates):
    import secrets
    registry=base/'used-images.json'
    with process_lock(base/'used-images.lock',blocking=True):
        now=time.time()
        state=runtime.read(registry)
        if not state:
            used=set()
            for record in [*base.glob('*.choice.json'),*(runtime.BASE/'illustrated').glob('*/scene.json')]:
                photo=runtime.read(record)
                if photo.get('id'):used.add(int(photo['id']))
            state={'version':1,'ids':sorted(used)}
        if state.get('version')!=2:
            # Earlier receipts have no reliable allocation time; start a full cooldown.
            state={'version':2,'last_used':{str(i):now for i in state.get('ids',[])}}
            atomic_json(registry,state)
        used=state['last_used']
        saved=runtime.read(assignment)
        rejected=lambda p:monochrome_label(p) or runtime.read(base/(str(p['id'])+'.color.json')).get('color') is False
        if saved and rejected(saved):
            atomic_json(assignment.with_suffix('.rejected-'+str(saved['id'])+'.json'),saved)
            assignment.unlink();saved={}
        if saved:
            if str(saved['id']) not in used:
                used[str(saved['id'])]=now;atomic_json(registry,state)
            return saved
        available=[photo for photo in candidates if not rejected(photo) and (str(photo['id']) not in used or now-used[str(photo['id'])]>=REUSE_INTERVAL)]
        if not available:return None
        photo=secrets.choice(available)
        # Reserve first so an interrupted write cannot bypass the reuse cooldown.
        used[str(photo['id'])]=now;atomic_json(registry,state)
        atomic_json(assignment,photo)
        return photo

def scene_once(folder,name):
    from PIL import Image,ImageOps
    import io
    base=runtime.BASE/'pexels';base.mkdir(parents=True,exist_ok=True)
    identity=hashlib.sha256(('person-closeup-v2:'+str(Path(folder).resolve())).encode()).hexdigest()
    assignment=base/(identity+'.choice.json')
    with process_lock(assignment.with_suffix('.lock'),blocking=True):
        photo=claim_photo(base,assignment,[])
        if photo and (base/(str(photo['id'])+'.png')).is_file():
            cached=base/(str(photo['id'])+'.png')
            if is_color(cached):return photo,cached
            photo=claim_photo(base,assignment,[])
        query=scene_query(name)
        if not query:return None
        if not photo:
            for term in (query, *SCENE_ALTERNATIVES.get(query, ())):
                for page in range(1, 11 if term == query else 6):
                    result=search(term,page)
                    used=runtime.read(base/'used-images.json').get('last_used',{})
                    available=[p for p in result['photos'] if runtime.read(base/(str(p['id'])+'.color.json')).get('color') is not False and (str(p['id']) not in used or time.time()-used[str(p['id'])]>=REUSE_INTERVAL)]
                    candidates=person_candidates(available,term)
                    photo=claim_photo(base,assignment,candidates)
                    if photo or not result.get('has_more',bool(result['photos'])):break
                if photo:break
            if not photo:return None
        path=base/(str(photo['id'])+'.png')
        if not path.exists():
            req=Request(photo['image_url'],headers={'User-Agent':'EnterpriseContentStudio/1.0'})
            with urlopen(req,timeout=12) as response:
                if urlsplit(response.url).hostname!='images.pexels.com':raise ValueError('图片来源异常')
                raw=response.read(10*1024*1024+1)
            if len(raw)>10*1024*1024:raise ValueError('场景图片过大')
            with Image.open(io.BytesIO(raw)) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1600,1200))
                buf=io.BytesIO();im.save(buf,'PNG')
            temporary=path.with_suffix('.tmp');temporary.write_bytes(buf.getvalue());temporary.replace(path)
        if not assignment.exists():atomic_json(assignment,photo)
        if not is_color(path):
            claim_photo(base,assignment,[])
            return False
        return photo,path

def scene(folder,name):
    for _ in range(6):
        result=scene_once(folder,name)
        if result is not False:return result
    return None

def image_path(identity):
    if not str(identity).isdigit() or len(str(identity))>15:raise ValueError('场景图编号无效')
    path=runtime.BASE/'pexels'/(str(identity)+'.png')
    if not path.is_file():raise ValueError('图片尚未下载')
    return path

def first_body(markdown):
    for block in re.finditer(r'\S.*?(?=\n[ \t]*\n|\Z)',markdown,re.S):
        text=block.group().strip()
        if not text.startswith(('#','![','---','***','```')):
            return block.end(),text
    return None

def project(root,folder,original):
    from PIL import Image
    from docx import Document
    from docx.shared import Cm,Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import logging
    name=(runtime.read(folder/'rewrite_context.json').get('product') or {}).get('name')
    if not name:name=runtime.product_label(root,folder.relative_to(root/'approved').parts[0])['name']
    if not scene_query(name):
        job=runtime.read(root/'job.json')
        name+=' '+str(job.get('question',''))+' '+' '.join(job.get('questions',[]))
    query=scene_query(name)
    try:selected=scene(folder,name)
    except Exception as error:
        logging.warning('pexels_scene_unavailable query=%s type=%s',query,type(error).__name__)
        return original
    if not selected:return original
    photo,path=selected
    wordhash=hashlib.sha256(original['word'].read_bytes()).hexdigest()
    md=original['markdown'].read_text('utf8')
    opening=first_body(md)
    if opening is None:return original
    key=runtime.digest(['pexels-layout-v8-page-fit',str(folder),wordhash,md,photo['id']])
    out=runtime.BASE/'illustrated'/key
    with process_lock(out.with_suffix('.lock'),blocking=True):
        if not (out/'scene.json').exists():
            out.mkdir(parents=True,exist_ok=True)
            doc=Document(original['word'])
            normalize=lambda text:re.sub(r'\s+','',text.replace('**',''))
            anchor=next((p for p in doc.paragraphs if normalize(p.text)==normalize(opening[1])),None)
            if anchor is None:return original
            with Image.open(path) as im:w,h=im.size
            section=doc.sections[0]
            max_width=(section.page_width-section.left_margin-section.right_margin)/360000
            max_height=(section.page_height-section.top_margin-section.bottom_margin)/360000*0.40
            scale=min(max_width/w,max_height/h,2.54/72)
            paragraph=doc.add_paragraph();paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent=Cm(0)
            paragraph.paragraph_format.left_indent=Cm(0)
            paragraph.paragraph_format.right_indent=Cm(0)
            paragraph.paragraph_format.line_spacing=1.0
            paragraph.paragraph_format.keep_with_next=True
            paragraph.add_run().add_picture(str(path),width=Cm(w*scale),height=Cm(h*scale))
            caption='图片来源：Pexels · '+photo['photographer']
            credit=doc.add_paragraph()
            credit.alignment=WD_ALIGN_PARAGRAPH.CENTER
            credit.paragraph_format.first_line_indent=Pt(0)
            credit.add_run(caption).font.size=Pt(9)
            anchor._p.addnext(paragraph._p)
            paragraph._p.addnext(credit._p)
            tmp=out/'pending.docx';doc.save(tmp);tmp.replace(out/'article.docx')
            illustration='\n\n![使用场景](/api/geo-creation/download?kind=scene-image&id='+str(photo['id'])+')\n\n'+caption+'\n\n'
            body=md[:opening[0]]+illustration+md[opening[0]:].lstrip('\n')
            atomic_write(out/'draft.md',body)
            atomic_json(out/'scene.json',photo)
    return {**original,'word':out/'article.docx','markdown':out/'draft.md','scene_image':path,'scene_meta':photo,'product_export_record':original['word'].parent/'complete.json'}
