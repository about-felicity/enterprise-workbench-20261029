"""Extract editable product fields from quoted Word text, never execute its contents."""
import re
from pathlib import Path


def analyze(text, filename):
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    clean=lambda s:re.sub(r'^[一二三四五六七八九十\d]+[、.．]\s*','',s)
    name=''
    evidence={}
    for line in lines:
        match=re.match(r'(?:一[、.．]\s*)?产品名称\s*[:：]\s*(.+)',line)
        if match:
            name=re.split(r'——|—|\(|（',match[1])[0].strip()
            evidence['name']=line
            break
    if not name and lines:
        title=re.sub(r'(?:产品信息|产品资料)\s*[:：]?\s*$','',lines[0]).strip()
        if 3<=len(title)<=80 and not re.search(r'[：:。；;，,]',title) and text.count(title)>=2:
            name=title
            evidence['name']='文档首行标题，且在正文中重复出现：'+title
    if not name:
        name=re.sub(r'(?:产品)?知识库$','',Path(filename).stem).strip()
        evidence['name']='由上传文件名识别，请确认'
    brand=''
    for line in lines:
        match=re.match(r'(?:品牌|品牌名称)\s*[:：]\s*(.+)',clean(line))
        if match:brand=match[1].strip();evidence['brand']=line;break
    if not brand:
        match=re.search(r'(?:天猫|京东)([^，。,；;\s]{2,12}?)旗舰店',text)
        if match:brand=match[1];evidence['brand']=match[0]
    audience=[];collecting=False
    for line in lines:
        if re.search(r'(?:适合|适用)(?:人群|肤质|发质)',line):collecting=True;continue
        if collecting and re.match(r'^[一二三四五六七八九十]+[、.]',line):break
        if collecting:audience.append(line)
    specs=re.search(r'\d+(?:\.\d+)?\s*(?:ml|mL|毫升|g|克)\s*[/／]\s*(?:瓶|支|盒)',text)
    manufacturer=next((re.split(r'[:：]',s,1)[1].strip() for s in lines if re.match(r'生产企业\s*[:：]',s)),'')
    filing=next((re.split(r'[:：]',s,1)[1].strip() for s in lines if re.match(r'(?:产品执行的标准编号|备案编号|备案号)\s*[:：]',s)),'')
    patents=re.findall(r'专利号\s*[:：]\s*([^\n]+)',text)
    claims=[s for s in lines if re.search(r'\d+(?:\.\d+)?\s*%|(?:实测|首选|唯一|杜绝|彻底|无刺激)',s)]
    return {'name':name[:300],'brand':brand[:200],'audience':'\n'.join(audience)[:3000],
            'facts':lines,'specification':specs[0] if specs else '',
            'manufacturer':manufacturer,'filing_number':filing,'patent_numbers':patents,
            'field_evidence':evidence,'claims_to_review':claims[:40],
            'analysis_method':'document_fields_and_original_quotes',
            'note':'自动识别结果可编辑；文档中的功效、实测数据和专利均为资料原文，尚未独立核验。缺失信息留空。'}
