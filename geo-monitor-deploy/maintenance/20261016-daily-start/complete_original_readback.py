"""Read and validate the one known submitted conversation; never submit."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import time
from geo_source_cards.runtime import process_lock,atomic_json
from geo_source_cards.journal import Journal
from geo_source_cards.cli import normalize_result
from web_collectors.collector import BrowserCollector

root=Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261016-094039-dc64b7e1/collector')
os.environ['GEO_COLLECTOR_RUNTIME']=str(root);os.environ['GEO_DEEPSEEK_PORT']='9514'
with process_lock(root/'collector.lock'):
    journal=Journal(root/'tasks.sqlite');collector=None
    try:
        task=journal.db.execute("select * from captures where state='needs_attention'").fetchone()
        if task is None:
            print(json.dumps({'state':'already_recovered'}));raise SystemExit(0)
        task=dict(task);url=journal.original_conversation(task);assert url
        collector=BrowserCollector('deepseek')
        collector.page.call('Page.navigate',{'url':url},timeout=30)
        time.sleep(5)
        value=normalize_result(collector.resume(task['question'],url),'deepseek',task['question'])
        assert value['url']==url and value['source_capture_complete'] and value['sources']
        record={**value,'model':'deepseek','question':task['question'],'round':task['round'],
                'task_id':task['task_id'],'batch':task['batch'],
                'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')}
        journal.complete_readback(task['task_id'],record);journal.export(Path(task['output']))
        atomic_json(root/'deepseek_last_prompt.json',{'last_prompt_epoch':time.time(),'fence':'original_readback_completed'})
        print(json.dumps({'state':'original_completed','task_id':task['task_id'],'sources':len(value['sources']),
                          'body_length':len(value['body']),'submitted':False}))
    finally:
        if collector is not None:collector.close()
        journal.close()
