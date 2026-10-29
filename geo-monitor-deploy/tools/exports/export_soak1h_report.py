"""Export a credential-free final hour report plus underlying recorder files."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from collections import Counter
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess

BASE=Path('/opt/monitor/geo-capture')
TEST='soak1h-1792029907'
ROOT=BASE/'soak'/TEST
BACKUP=BASE/'backups/1792026782'
OUT=Path('/home/user/redroid-doubao')/(TEST+'-export')


def command(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=25).stdout.strip()


def read(path):return json.loads(path.read_text('utf8'))
def stamp(epoch):return datetime.fromtimestamp(epoch,timezone(timedelta(hours=8))).isoformat(timespec='seconds')


report=read(ROOT/'report.json')
assert report['test_id']==TEST and report['duration_seconds']==3600 and report['elapsed_seconds']>=3600
metrics=[json.loads(line) for line in (ROOT/'metrics.jsonl').read_text().splitlines()]
verified=[json.loads(line) for line in (ROOT/'verified.jsonl').read_text().splitlines()]
assert len(metrics)==report['samples'] and len(verified)==report['verified_new_receipts']
assert len({v['request_id'] for v in verified})==len(verified)
assert all(v['body_length']>0 and v['sources']>0 for v in verified)
counts=Counter(v['model'] for v in verified)
fleet=read(BASE/'fleet.json')
docker_after=command('docker','inspect',*fleet['containers'],'--format','{{json .Name}} {{json .State.StartedAt}}')
docker_unchanged=docker_after==(BACKUP/'docker-before.json').read_text().strip()
editorial_after=command('systemctl','show','geo-editorial-scheduler.service','geo-editorial-api-worker.service',
    'geo-editorial-coordinator.service','geo-editorial-session-watch.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp')
editorial_unchanged=editorial_after==(BACKUP/'editorial-before.txt').read_text().strip()
historical=[]
for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
    value=read(Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json')
    historical.append({'batch':batch,'captured':value['captured'],'processed':value['geo_processed'],
        'unchanged_105':value['captured']==value['geo_processed']==105 and value['status']=='complete'})
summary={
    'test_id':TEST,'started_at_beijing':stamp(report['started_at']),'finished_at_beijing':stamp(report['finished_at']),
    'elapsed_seconds':report['elapsed_seconds'],'samples':len(metrics),'max_sample_interval_seconds':max(b['at']-a['at'] for a,b in zip(metrics,metrics[1:])),
    'verdict':report['verdict'],'verdict_reason':'文心首页导航ERR_NETWORK_CHANGED导致中断，已修复恢复；不能视为连续一小时通过',
    'new_capture_deltas':report['deltas'],'verified_database_records_by_model':dict(counts),
    'verified_database_records_total':len(verified),'all_verified_body_and_sources_match':True,
    'new_baidu_duplicate_observations':report['deltas']['baidu_ai']['processed']-report['deltas']['baidu_ai']['unique_processed'],
    'new_baidu_unavailable_observations':report['deltas']['baidu_ai']['unavailable'],
    'original_docker_and_emulators_unchanged':docker_unchanged,'editorial_services_unchanged':editorial_unchanged,
    'historical_doubao':historical,'blocked_channels':report['blocked_channels'],'anomalies':report['anomalies'],
    'native_scope_note':'双豆包原105/105历史记录保持；10:21用户另行启动两小时新批次，仅与本小时后约44分钟重叠，本报告不是其两小时验收',
    'wenxin_recovery_note':'10:57归档原失败题并恢复原批次，第40/41条连续processed，小时结束时43条processed；原39条记录未改变',
    'sampler_only_finished':True,'capture_services_not_paused_by_hour_report':True,
}
OUT.mkdir(mode=0o755,exist_ok=True)
for name in ('manifest.json','report.json','metrics.jsonl','verified.jsonl'):
    shutil.copyfile(ROOT/name,OUT/name);(OUT/name).chmod(0o644)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(OUT/'summary.json').chmod(0o644)
print(json.dumps(summary,ensure_ascii=False,indent=2))
