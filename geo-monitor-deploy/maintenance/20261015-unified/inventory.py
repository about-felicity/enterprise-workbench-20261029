import json,subprocess
from pathlib import Path

def sql(q):return subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',q],text=True,timeout=30).strip()
print('TABLES',sql("select string_agg(table_name,', ' order by table_name) from information_schema.tables where table_schema='public'"))
print('COLUMNS',sql("select coalesce(json_agg(json_build_object('table',table_name,'column',column_name,'type',data_type)),'[]') from information_schema.columns where table_schema='public' and table_name in ('monitor_runs','monitor_sources','monitor_ingest_events','runs','sources','source_documents')"))
print('CORE',[p.name for p in Path('/opt/monitor/monitor_core').glob('*.py') if any(w in p.name for w in ('db','postgres','source','analytics','ingest','api','analysis','product'))])
print('DASHBOARD',subprocess.check_output(['grep','-nE','analytics|web_body|answerText|round_number|HTTPServer|api/','/opt/monitor/doubao_dashboard_server.py'],text=True)[:9000])
print('SERVICES',subprocess.check_output(['systemctl','show','geo-editorial-api-worker.service','geo-editorial-scheduler.service','-p','ExecStart','-p','EnvironmentFiles'],text=True))
