"""Read-only GEO observation/full-article adapter. Never starts a platform collector."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from urllib.parse import urlsplit

MEDIA={
    'hgdaily.com.cn':'黄冈日报媒体平台','bandao.cn':'半岛网媒体平台','people.com.cn':'人民网',
    'xinhuanet.com':'新华网','news.cn':'新华网','chinadaily.com.cn':'中国日报网',
    'chinanews.com.cn':'中国新闻网','chinanews.com':'中国新闻网','gmw.cn':'光明网',
    'cnr.cn':'央广网','cctv.com':'央视网','thepaper.cn':'澎湃新闻','bjnews.com.cn':'新京报',
    '163.com':'网易内容平台（包含自媒体）','sohu.com':'搜狐内容平台（包含自媒体）',
    'baijiahao.baidu.com':'百家号内容平台（包含自媒体）',
}
CHANNELS={'deepseek','wenxin_card','baidu_ai'}


def literal(value):
    return "E'"+str(value).replace('\\','\\\\').replace("'","''")+"'"


def query(select):
    command=['docker','exec','monitor-postgres','psql','-X','-qAt','-v','ON_ERROR_STOP=1',
             '-U','monitor_app','-d','monitor','-c',
             "BEGIN READ ONLY; SET LOCAL statement_timeout='20s'; SELECT coalesce(json_agg(q),'[]') FROM ("+select+") q; COMMIT;"]
    raw=subprocess.check_output(command,text=True,timeout=30).strip()
    return json.loads(raw)


def channel(model,serial):
    if model=='deepseek':return 'deepseek'
    return 'baidu_ai' if 'baidu_ai' in serial or 'baidu-ai' in serial else 'wenxin_card'


def catalog():
    return {'dates':[r['day'] for r in query("SELECT DISTINCT day::text AS day FROM monitor_runs WHERE model_id in ('deepseek','wenxin') AND status='success' ORDER BY day DESC LIMIT 120")],
            'questions':[r['question'] for r in query("SELECT DISTINCT question FROM monitor_runs WHERE model_id in ('deepseek','wenxin') AND status='success' ORDER BY question")],
            'channels':[{'id':'deepseek','name':'DeepSeek'},{'id':'wenxin_card','name':'文心卡片'},{'id':'baidu_ai','name':'百度卡片'}]}


def observations(day,question,channels,limit=120):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or not isinstance(question,str) or not 1<=len(question)<=2000:
        raise ValueError('请选择有效日期和问题')
    if not channels or not set(channels)<=CHANNELS:raise ValueError('素材通道不正确')
    limit=max(1,min(int(limit),400))
    sql="""SELECT r.model_id,r.run_id,r.day::text AS day,r.question,r.serial,r.answer,r.finished_at,
      (SELECT coalesce(json_agg(json_build_object('url',s.url,'title',s.title,'canonical_url',s.canonical_url,'source_type',s.source_type) ORDER BY s.source_index),'[]')
       FROM monitor_sources s WHERE s.model_id=r.model_id AND s.run_id=r.run_id AND s.production_valid) sources
      FROM monitor_runs r WHERE r.model_id IN ('deepseek','wenxin') AND r.status='success'
      AND coalesce(r.payload->>'body_capture_complete','true')<>'false'
      AND coalesce(r.payload->>'source_capture_complete','true')<>'false'
      AND r.day="""+literal(day)+"::date AND r.question="+literal(question)+" ORDER BY r.finished_at DESC LIMIT "+str(limit)
    rows=query(sql)
    return [r for r in rows if channel(r['model_id'],r['serial']) in channels]


def media_identity(url):
    host=(urlsplit(url).hostname or '').lower().rstrip('.')
    return next((name for domain,name in MEDIA.items() if host==domain or host.endswith('.'+domain)),None)


def article(row,url):
    if not row or row['status']!='ok':raise ValueError('正文尚未成功抓取')
    text=row['content_text'] or ''
    if row['extraction_quality'] not in {'high','medium'}:raise ValueError('正文质量尚未通过')
    if len(text)<80 or len(text)!=row['text_length']:raise ValueError('正文长度校验失败')
    if hashlib.sha256(text.encode()).hexdigest()!=row['content_hash']:raise ValueError('正文哈希校验失败')
    if not media_identity(row['final_url'] or url):raise ValueError('不在原国内媒体素材范围')
    return {'url':url,'final_url':row['final_url'] or url,'status':'fetched','text':text,
            'title':row['title'] or '', 'text_length':len(text),'content_hash':row['content_hash'],
            'extraction_quality':row['extraction_quality'],'extraction_method':row['extraction_method'],
            'fetched_at':row['fetched_at'],'storage':'geo_source_content_sqlite',
            'media_registry_name':media_identity(row['final_url'] or url)}


def snapshot(rows,content_db,max_articles=100):
    result=[];provenance={};excluded=[];seen=set();selected=0
    with closing(sqlite3.connect(Path(content_db).resolve().as_uri()+'?mode=ro',uri=True,timeout=15)) as db:
        db.row_factory=sqlite3.Row;db.execute('pragma query_only=on');db.execute('begin')
        for row in rows:
            observation={'model':channel(row['model_id'],row['serial']),'question':row['question'],
                         'body':row['answer'],'sources':[],'geo_run_id':row['run_id'],'captured_at':row['finished_at']}
            for source in row['sources']:
                url=source['url'];key=source.get('canonical_url') or url
                origin={'model_id':row['model_id'],'channel':observation['model'],'run_id':row['run_id'],
                        'day':row['day'],'question':row['question'],'source_url':url,'source_title':source['title']}
                provenance.setdefault(key,[]).append(origin)
                if key in seen:continue
                seen.add(key)
                if source.get('source_type')=='video':excluded.append({'url':url,'reason':'视频不冒充文章正文'});continue
                if selected>=max_articles:excluded.append({'url':url,'reason':'本任务素材数量上限，原GEO数据保留'});continue
                content=db.execute('select * from source_content where url=?',(url,)).fetchone()
                if not content and key!=url:content=db.execute('select * from source_content where url=?',(key,)).fetchone()
                try:full=article(content,url)
                except ValueError as error:excluded.append({'url':url,'reason':str(error)});continue
                observation['sources'].append({'url':url,'title':source['title'],'article':full,
                                               'geo_provenance_key':key})
                selected+=1
            if observation['sources']:result.append(observation)
    return {'observations':result,'provenance':provenance,'excluded':excluded,
            'counts':{'geo_observations':len(rows),'unique_source_urls':len(seen),'full_articles':selected,
                      'excluded_sources':len(excluded)},'source':'existing_GEO_only','platform_questions_sent':0}
