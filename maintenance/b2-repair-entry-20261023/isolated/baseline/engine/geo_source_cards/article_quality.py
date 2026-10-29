"""Remove recognizable page chrome before counting a fetched article as evidence."""
import hashlib,re

FOOTER=re.compile(r'^(?:评论(?:\s*\d+)?|扫码下载百度APP|搜最新资讯、看热门视频|设为首页|关于百度|About Baidu|使用百度前必读|帮助中心|相关阅读|相关推荐)$',re.I)

def normalize(article):
 if article.get('status')!='fetched':return article
 original=article.get('text','');parts=re.split(r'\n\s*\n|\n',original);kept=[]
 for part in parts:
  text=part.strip()
  if FOOTER.fullmatch(text):break
  if text:kept.append(text)
 body='\n\n'.join(kept).strip()
 result={**article,'title':re.sub(r'(?:icon_voice(?:_on)?)+$','',article.get('title','')).strip()}
 if body!=original:
  result.update(text=body,pre_cleanup_sha256=hashlib.sha256(original.encode()).hexdigest(),sha256=hashlib.sha256(body.encode()).hexdigest(),cleanup='page_chrome_v1')
  result['paragraphs']=[p for p in article.get('paragraphs',[]) if p.get('text','') in body]
  result['headings']=[h for h in article.get('headings',[]) if h in body]
 if len(re.sub(r'\s','',body))<160:
  result.update(status='failed',text='',rejected_text=original,error='Only page chrome or too little article body remains after cleanup')
 return result
