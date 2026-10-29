"""Verify snapshot bytes, including Git's index, against both recovery manifests."""
import argparse,hashlib,json,subprocess
from pathlib import Path
W=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--index',action='store_true');parser.add_argument('--live-local',action='store_true');args=parser.parse_args()
 expected={}
 server=json.loads((W/'source-snapshot/production-manifest.json').read_text('utf-8'))
 for row in server['files']:expected['source-snapshot/'+row['snapshot']]=row['sha256']
 local=json.loads((W/'source-snapshot/local-manifest.json').read_text('utf-8'))
 for row in local['files']:expected['source-snapshot/local/'+row['source']]=row['sha256']
 client_path=W/'source-snapshot/client-manifest.json'
 if client_path.exists():
  for row in json.loads(client_path.read_text('utf-8'))['files']:expected['source-snapshot/'+row['snapshot']]=row['sha256']
 errors=[]
 if args.live_local:
  for row in local['files']:
   path=W/row['source']
   if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:errors.append({'path':row['source'],'error':'live_local_source_changed_since_manifest'})
 for relative,digest in expected.items():
  data=(W/relative).read_bytes()
  if hashlib.sha256(data).hexdigest()!=digest:errors.append({'path':relative,'error':'working_copy_hash_mismatch'})
  if args.index:
   result=subprocess.run(['git','show',':'+relative],cwd=W,capture_output=True)
   if result.returncode or hashlib.sha256(result.stdout).hexdigest()!=digest:errors.append({'path':relative,'error':'git_index_hash_mismatch'})
 print(json.dumps({'files':len(expected),'index_checked':args.index,'errors':errors},ensure_ascii=False))
 raise SystemExit(bool(errors))
if __name__=='__main__':main()
