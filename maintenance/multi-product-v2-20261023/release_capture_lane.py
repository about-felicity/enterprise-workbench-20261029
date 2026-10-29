import hashlib,json,os,py_compile,shutil,signal,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
target=Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py')
new=BASE/'engine/geo_source_cards/cli.py'
expected='cceb58b987324ba32529d3ea0919db380216e311b0621686f6eb4a9d7b573bdc'
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected, 'Live collector changed; inspect before replacing'
backup=BASE/'capture-cli-before.py';shutil.copy2(target,backup)
staged=target.with_suffix('.v2-lane-fix.py');shutil.copy2(new,staged)
py_compile.compile(str(staged),doraise=True)
staged.replace(target)
pid=16484
cmdline=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
assert 'creation-material-2026-10-22-baidu_ai' in cmdline and '--max-new-captures 1' in cmdline
folder=Path('/opt/monitor/geo-content/studio/capture/plan-fbb1750d49ea45cb8d3a490b44a19e32/days/2026-10-22/baidu_ai')
recovery=json.loads((folder/'collector/search_recovery.json').read_text())
assert recovery['kind']=='read_error' and not recovery['blocked']
record={'before_sha256':expected,'after_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'backup':str(backup),'interrupted_pid':pid,'original_recovery':recovery,
        'at':time.time(),'reason':'One-question collector held shared lock across repeated read-only search cooldowns',
        'original_task_journal_preserved':True,'policy_and_intervals_unchanged':True}
(BASE/'capture-lane-deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
os.kill(pid,signal.SIGINT)
print(json.dumps(record,ensure_ascii=False))
