"""Separate article titles from introductions without dropping body paragraphs."""
import re

def clean(value):
    return re.sub(r'^标题\s*[:：]\s*','',re.sub(r'^#{1,6}\s+','',value.strip()).strip('* ')).strip()

def is_title(value):
    value=clean(value)
    return bool(value) and len(value)<=80 and '\n' not in value and not re.search(r'[。；;]',value) and len(re.findall(r'[！？!?]',value))<=2

def fallback_title(body,product=None,category=None):
    # Use only existing product metadata and topics actually present in the intro.
    intro=body[:600]
    question=re.match(r'^([^\n。！？!?]{4,38}[？?])',intro)
    if question:return question.group(1)
    product=product or {};category=category or {}
    name=product.get('name') or product.get('product_name') or '产品'
    name=re.sub(r'\s+',' ',str(name)).strip()[:40]
    topics=[v for v in ('控油','蓬松','防脱','去屑','保湿','祛痘','修护','染发','眉毛','睫毛') if v in intro][:2]
    genre=category.get('category') or category.get('type') or category.get('label') or ''
    tail='选购与使用指南' if genre in ('ranking','排行类') else '产品特点与使用指南'
    return name+'：'+('、'.join(topics)+'需求下的' if topics else '')+tail

def normalize(markdown,product=None,category=None):
    text=markdown.strip();lines=text.splitlines()
    if not lines:return text
    if is_title(lines[0]):
        title=clean(lines[0]);body='\n'.join(lines[1:]).lstrip('\n')
    else:
        # A paragraph mistakenly prefixed with H1 is still body, not a title.
        body=re.sub(r'^#\s+','',text)
        title=fallback_title(body,product,category)
    return '# '+title+'\n\n'+body+'\n'

def display_title(markdown,product=None,category=None):
    return clean(normalize(markdown,product,category).splitlines()[0]) if markdown.strip() else '未命名文章'
