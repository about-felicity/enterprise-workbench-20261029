import hashlib
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
import unittest
from .source_adapter import article,snapshot,literal,channel

class SourceTests(unittest.TestCase):
    def row(self,text):return {'status':'ok','content_text':text,'text_length':len(text),
        'content_hash':hashlib.sha256(text.encode()).hexdigest(),'extraction_quality':'high',
        'final_url':'https://www.sohu.com/a/123','title':'完整文章','extraction_method':'readability','fetched_at':'today'}
    def test_full_body_not_excerpt(self):
        body='证据正文。'*2000
        self.assertEqual(article(self.row(body),'https://www.sohu.com/a/123')['text'],body)
    def test_hash_or_length_mismatch_rejected(self):
        for field,value in [('text_length',5),('content_hash','wrong'),('extraction_quality','low')]:
            row=self.row('正文内容。'*100);row[field]=value
            with self.assertRaises(ValueError):article(row,row['final_url'])
    def test_media_suffix_not_lookalike(self):
        row=self.row('正文内容。'*100);row['final_url']='https://sohu.com.evil.test/a'
        with self.assertRaises(ValueError):article(row,row['final_url'])
    def test_snapshot_deduplicates_full_body_preserves_both_origins(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbpath=Path(tmp)/'content.sqlite';text='完整证据。'*100;row=self.row(text);url=row['final_url']
            with closing(sqlite3.connect(dbpath)) as conn:
                conn.execute('create table source_content(url text primary key,status text,content_text text,text_length integer,content_hash text,extraction_quality text,final_url text,title text,extraction_method text,fetched_at text)')
                conn.execute('insert into source_content values(?,?,?,?,?,?,?,?,?,?)',(url,*[row[k] for k in ['status','content_text','text_length','content_hash','extraction_quality','final_url','title','extraction_method','fetched_at']]))
                conn.commit()
            before=dbpath.read_bytes()
            rows=[{'model_id':'wenxin','serial':s,'run_id':s,'day':'2026-10-15','question':'问题','answer':'回答全文',
                   'finished_at':'now','sources':[{'url':url,'title':'标题','source_type':'article'}]} for s in ['wenxin-card','baidu-ai']]
            result=snapshot(rows,dbpath)
            self.assertEqual(result['counts']['full_articles'],1)
            self.assertEqual(len(result['provenance'][url]),2)
            self.assertEqual(result['observations'][0]['sources'][0]['article']['text'],text)
            self.assertEqual(before,dbpath.read_bytes())
            self.assertEqual(result['platform_questions_sent'],0)
    def test_sql_literal_and_channel(self):
        self.assertEqual(literal("a'b\\c"),"E'a''b\\\\c'")
        self.assertEqual(channel('wenxin','geo-panel-baidu-ai-test'),'baidu_ai')

if __name__=='__main__':unittest.main()
