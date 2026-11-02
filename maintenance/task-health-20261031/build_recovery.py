from pathlib import Path
import sys
here=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'recover'
assert name in ['recover','recover_http','cache_candidates','recover_sources','recover_today_http']
body=(here/(name+'.py')).read_text('utf8')
(here/('run_'+name+'.py')).write_text('import subprocess\nraise SystemExit(subprocess.run(["/home/user/geo-editorial/venv/bin/python","-B","-c",'+repr(body)+'],timeout=360).returncode)\n',encoding='utf8')
