import subprocess
sql="select column_name,data_type from information_schema.columns where table_name in ('monitor_runs','monitor_sources') order by table_name,ordinal_position; select model_id,count(*),min(day),max(day) from monitor_runs group by model_id;"
r=subprocess.run(['docker','exec','monitor-postgres','sh','-c','psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"','sh',sql],capture_output=True,text=True,timeout=40)
print(r.stdout);print(r.stderr);assert r.returncode==0
