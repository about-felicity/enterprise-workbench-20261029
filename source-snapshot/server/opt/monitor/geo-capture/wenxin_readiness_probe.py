"""One normal read-only search in the existing profile; never solve a challenge."""
import argparse,json,os,time
from pathlib import Path
from geo_source_cards.cli import create_collector
from geo_source_cards.runtime import atomic_json
from wenxin_monitor.controller import WENXIN_SEARCH_SNAPSHOT_JS

def main():
 p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);p.add_argument('--question',required=True);args=p.parse_args()
 os.environ['GEO_COLLECTOR_RUNTIME']=str(args.runtime)
 collector=None;record={'at':time.time(),'question':args.question,'status':'read_error'}
 try:
  collector=create_collector('wenxin_card')
  value=collector.collect_wenxin_search(args.question,timeout=45)
  if value.get('body_capture_complete') and value.get('source_capture_complete'):
   record.update(status='ready',body_length=len(value.get('body','')),sources=len(value.get('sources',[])))
 except Exception as error:
  record['error']=type(error).__name__+': '+str(error)[:300]
 finally:
  if collector:
   try:
    snapshot=collector.page.evaluate("({url:location.href,title:document.title,pageText:document.body.innerText.slice(0,1000)})")
    record['snapshot']=snapshot
    if collector._is_security_verification(snapshot):record['status']='verification_required'
   except Exception:pass
   collector.close()
  atomic_json(args.runtime/'verification_probe_latest.json',record)
  print(json.dumps(record,ensure_ascii=False),flush=True)
 return 0 if record['status']=='ready' else 77 if record['status']=='verification_required' else 75

if __name__=='__main__':raise SystemExit(main())
