import os,sys,json
from pathlib import Path
B=Path(__file__).resolve().parent;os.environ['GEO_CREATION_ROOT']=str(B/'runtime');sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.pipeline_control import pause
s=runtime.read(B/'state.json');root=runtime.job_root(s['job_id'])
pause(root,'maintenance_prompt_compaction','Reduce repeated ingestion metadata in model inputs; finish already sent calls')
budget=runtime.SharedBudget(root)
print(json.dumps([list(r) for r in budget.db.execute('select c.category,c.article,c.stage,c.state,c.charged,c.reserved from costs c join studio_cost_scopes s on s.id=c.id where s.job=?',(s['job_id'],))],ensure_ascii=False))
budget.db.close()
