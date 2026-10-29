"""Read only the requested test conversations from the emulator's SQLite store."""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--questions', default='/home/user/redroid-doubao/test_questions.json')
parser.add_argument('--output', default='/home/user/redroid-doubao/store-results.json')
parser.add_argument('--stdout', action='store_true')
args = parser.parse_args()
questions = json.loads(Path(args.questions).read_text(encoding='utf-8-sig'))
container = json.loads(subprocess.check_output(['docker','inspect','doubao-redroid-redroid-1']))[0]
mount = next(m['Source'] for m in container['Mounts'] if m['Destination'] == '/data')
database_dir = Path(mount) / 'data/com.larus.nova/databases'
databases = [p for p in database_dir.glob('im_database_*') if p.is_file() and not p.name.endswith(('-wal','-shm','-journal'))]

def unpack(value):
    if not isinstance(value, str):
        return value
    for _ in range(3):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            value = value.replace('\\"','"').replace('\\\\','\\')
    return {'raw':value}

results = []
for index, question in enumerate(questions, 1):
    result = {'index':index, 'question':question, 'extraction':'emulator SQLite read-only transaction', 'status':'not_found'}
    for path in databases:
        try:
            db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
            db.row_factory = sqlite3.Row
            db.execute('pragma query_only=on')
            db.execute('begin')
            request = db.execute('select conversation_id,local_index,create_time from im_message where fts_content=? order by create_time desc limit 1', (question,)).fetchone()
            if request is None:
                db.close()
                continue
            result['request_time'] = request['create_time']
            answer = None
            for row in db.execute('select content,fts_content,create_time from im_message where conversation_id=? and local_index>? order by local_index asc', (request['conversation_id'],request['local_index'])):
                blocks = unpack(row['content'])
                if not isinstance(blocks,list):
                    continue
                if not any(b.get('content',{}).get('text_block',{}).get('text') for b in blocks):
                    continue
                if row['fts_content'] == question:
                    continue
                answer = (row, blocks)
                break
            if answer is not None:
                row, blocks = answer
                body, sources, citations, queries = [], [], [], []
                for block in blocks:
                    content = block.get('content',{})
                    if 'text_block' in content:
                        body.append(content['text_block'].get('text',''))
                    search = content.get('search_query_result_block',{})
                    queries.extend(search.get('queries',[]))
                    for item in search.get('results',[]):
                        card = item.get('text_card')
                        if card:
                            sources.append({k:card.get(k) for k in ['index','title','url','doc_id']})
                    for meta in block.get('meta_info',[]):
                        info = unpack(meta.get('info',''))
                        if isinstance(info,dict) and info.get('url'):
                            citations.append({k:info.get(k) for k in ['pos','insert_text','title','url','doc_id','summary','website_name','authority']})
                result.update(status='ok', finished=all(b.get('is_finish',False) for b in blocks), body_markdown='\n\n'.join(body),
                              body_text=row['fts_content'], sources=sources, citations=citations, search_queries=queries,
                              source_count=len(sources), citation_count=len(citations))
            else:
                result['status'] = 'answer_pending'
            db.close()
            break
        except sqlite3.DatabaseError:
            # Other IM stores may be encrypted or use a different schema.
            continue
    results.append(result)
if args.stdout:
    print(json.dumps(results, ensure_ascii=False))
else:
    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    for result in results:
        print(json.dumps({k:result.get(k) for k in ['index','status','finished','source_count','citation_count']}, ensure_ascii=False))
