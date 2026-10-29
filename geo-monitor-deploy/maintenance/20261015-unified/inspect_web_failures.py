import json
from pathlib import Path
import sqlite3
from contextlib import closing
base=Path('/opt/monitor/geo-capture/batches')
for batch in ['geo-panel-deepseek-20261015-181821-879aca5d','geo-panel-wenxin-card-20261015-181822-d5a69c59']:
    root=base/batch;output={'batch':batch}
    with closing(sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        rows=[dict(r) for r in db.execute("select * from captures where state not in ('pending','completed')")]
        output['rows']=[{k:v for k,v in row.items() if k not in {'result'}} for row in rows]
        output['tables']=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
    output['health']=json.loads((root/'bridge_health.json').read_text())
    lines=(root/'capture.log').read_text().splitlines()
    # Never emit browser storage, authentication headers or opaque URLs.
    output['diagnostic_lines']=[line[:700] for line in lines[-100:] if any(word in line for word in ['Error:','Timeout','failed','Traceback','error','waiting','state']) and not any(word in line.lower() for word in ['token','cookie','authorization','password'])]
    print(json.dumps(output,ensure_ascii=False))
