"""One isolated pass for known logic-rejected masks; never replay uncertain calls."""
import sys,json,hashlib,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,quality_repair as q
from geo_source_cards.article_logic import enforce,WRITING_RULES
from geo_source_cards.staged_editorial import research_for_writer
from geo_source_cards.runtime import process_lock,atomic_json
q.ROOT=runtime.BASE/'quality-repair/20261021-mask-logic';q.ROOT.mkdir(parents=True,exist_ok=True)
q.reuse_verified_delivery=lambda *args:None
M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic');root=runtime.BASE/'runs/creation-1792556219-bbc55e13'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with process_lock(q.ROOT/'process.lock',blocking=False):
 original_control=(root/'control.json').read_bytes() if (root/'control.json').exists() else None
 results=[]
 for row in runtime.read(M/'audit.json')['articles']:
  if row['state']!='needs_revision':continue
  folder=root/'approved'/row['id']
  try:enforce(runtime.read(folder/'logic_review.json'),(folder/'draft.md').read_text(),runtime.read(folder/'logic_product.json'));continue
  except ValueError:pass
  assert sha(folder/'draft.md')==row['draft_sha256'],'Changed article requires fresh inventory'
  day,category,num=row['id'].split('/');writer=Path(row['writer'])
  item={'key':hashlib.sha256((str(root)+'/'+row['id']).encode()).hexdigest()[:24],'root':str(root),'id':row['id'],'date':day,'category':category,'number':int(num),'title':row['title'],'original_word_sha256':sha(folder/'article.docx'),'writer':str(writer),'research':str(research_for_writer(writer))}
  q.REASON='用户指出全文逻辑严重错误；保留真实来源与事实，不延续原稿论证。逐项修复：\n'+json.dumps(row.get('issues',[]),ensure_ascii=False)+'\n'+WRITING_RULES
  result=q.revise(item);results.append(result);atomic_json(M/'repairs.json',{'at':time.time(),'articles':results})
  print(json.dumps(result,ensure_ascii=False),flush=True)
  if q.STOP.is_set():break
 if original_control is not None:assert (root/'control.json').read_bytes()==original_control
 print('Isolated repair pass complete; controls unchanged',flush=True)
