import subprocess
sql="select day,model_id,status,count(*) from monitor_runs where day in ('2026-11-01','2026-11-02') group by day,model_id,status order by day,model_id,status;"
r=subprocess.run(['docker','exec','monitor-postgres','sh','-c','psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"','sh',sql],capture_output=True,text=True,timeout=45)
print(r.stdout);print(r.stderr);assert r.returncode==0
