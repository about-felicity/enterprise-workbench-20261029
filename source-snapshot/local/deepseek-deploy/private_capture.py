"""One additional creation-only question per invocation; same device/account/rate lock."""
import argparse,json,signal,sqlite3
from pathlib import Path
from worker import run,load_config,stop_signal

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--lane',type=Path,required=True);parser.add_argument('--batch',required=True);parser.add_argument('--rounds',type=int,required=True)
 args=parser.parse_args();lane=args.lane.resolve()
 if not lane.is_relative_to(Path('/opt/monitor/geo-content/materials').resolve()) or lane.is_symlink():raise ValueError('Private material directory required')
 questions=[s for s in (lane/'questions.txt').read_text().splitlines() if s.strip()]
 config={'model':'deepseek','batch':args.batch,'questions':questions,'rounds':args.rounds,'interval':600,'prompt_mode':'question_only','private_root':str(lane)}
 path=lane/'native-config.json'
 if path.exists() and json.loads(path.read_text())!=config:raise ValueError('Private frozen config changed')
 if not path.exists():path.write_text(json.dumps(config,ensure_ascii=False));path.chmod(0o600)
 marker=lane/'native/maintenance_pause.json'
 if marker.exists():
  if json.loads(marker.read_text()).get('source')!='acceptance_limit':return 0
  marker.unlink()
 count=0;dbpath=lane/'native/tasks.sqlite'
 if dbpath.exists():
  with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:count=db.execute("select count(*) from tasks where state='completed'").fetchone()[0]
 signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
 return run(load_config(path),count+1)

if __name__=='__main__':raise SystemExit(main())
