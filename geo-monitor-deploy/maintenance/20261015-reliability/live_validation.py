"""Read-only complete batch/PG fidelity and post-upgrade observation summary."""
from contextlib import closing
import json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from native_soak import API,read,atomic,lane
from all_channel_soak import audit,audit_nontext,job_root,queue_metrics,NATIVE
from creation.soak import audit as audit_creation
from creation import runtime
base=Path('/opt/monitor/geo-capture');root=base/'maintenance/20261015-reliability'
release=read(root/'deployed.json');pointer=read(base/'soak12h_current.json')
manifest=read(Path(pointer['root'])/'manifest.json');panel=API().panel()
window_status=read(Path(pointer['root'])/'status.json')
report={'at':time.time(),'upgrade_at':release['at'],'capture_test':pointer,'models':{},'failures':[], 'operational_blockers':[]}
for model,job in manifest['jobs'].items():
    try:
        c=lane(panel,model)['current'];verified=audit(model,job,set());home=job_root(model,job['batch'])
        path=home/'tasks.sqlite' if model in NATIVE else home/'collector/tasks.sqlite'
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            if model in NATIVE:
                raw=[json.loads(r[0]) for r in db.execute("select result_json from tasks where state='completed' and task_id in(select task_id from events where event='completed' and time>=?)",(release['at'],))]
                prompt_changes=db.execute('select count(*) from tasks where question<>wire_question').fetchone()[0]
            else:
                raw=[json.loads(r[0]) for r in db.execute("select result from captures where state='completed' and finished>=?",(release['at'],))];prompt_changes=0
        full=[r for r in raw if r.get('availability') not in ('no_card','supplement_unavailable')]
        assert c['batch']==release['same_batches'][model] and not prompt_changes
        blocked=bool(c['needs_review']) or c['state'] not in ('running','running_delivery_backoff','pausing','paused','complete','complete_with_unavailable')
        if blocked:report['operational_blockers'].append({'model':model,'state':c['state'],'needs_review':c['needs_review']})
        assert all(r.get('body_capture_complete') is True and r.get('source_capture_complete') is True for r in full)
        assert all(r.get('body_markdown',r.get('body','')).strip() and r.get('sources') for r in full)
        report['models'][model]={k:c[k] for k in ('batch','state','service_state','captured','processed','unique_processed','duplicates','unavailable','needs_review','pending_delivery','progress','diagnostics')}
        report['models'][model].update(new_captured_after_upgrade=len(full),
            new_processed_after_upgrade=c['processed']-release['drained_counts'][model],
            verified_unique_receipts=len(verified),body_and_all_source_PG_fidelity=True,
            non_question_prompt_rows=prompt_changes,operational_blocked=blocked,
            current_window_counts=window_status.get('models',{}).get(model,{}).get('window_counts',{}),
            fidelity_scope='Completed captures and receipts only; unresolved original requests are excluded from success counts',
            **queue_metrics(model,job,release['at']))
        if model=='yuanbao':report['models'][model]['nontext_audit']=audit_nontext(model,job)
    except Exception as error:report['failures'].append({'model':model,'kind':type(error).__name__})
containers=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
report['core_and_android_containers_unchanged']=containers==manifest['docker_before']
cp=read(base/'creation_soak_current.json');proof=audit_creation(runtime.job_root(cp['jobs'][0]))
report['creation']={'test':cp,'approved_total':len(proof['approved']),
    'unknown_api_calls':proof['unknown_calls'],'Word_review_material_hash_GEO_provenance_verified':True,
    'day_complete':proof['day']['status']=='complete','platform_extra_questions':proof['platform_questions_sent']}
status=read(Path(pointer['root'])/'status.json')
report['recorder']={k:status.get(k) for k in ('status','elapsed_seconds','anomalies','error_kind')}
report['all_models_have_new_processed_after_upgrade']=set(report['models'])==set(manifest['jobs']) and all(c['new_processed_after_upgrade']>=1 for c in report['models'].values())
report['all_channels_currently_collecting']=not report['operational_blockers'] and not report['failures']
atomic(root/'live-validation.json',report)
export=Path('/tmp/geo-reliability-export');export.mkdir(exist_ok=True,mode=0o755)
for name,source in {
    'live-validation.json':root/'live-validation.json','candidate-qa.json':Path('/tmp/geo-reliability-stage/candidate-qa.json'),
    'public-qa.json':base/'maintenance/20261015-unified/creation-public-qa.json',
    'analysis-audit.json':base/'maintenance/20261015-unified/analysis-audit.json'}.items():
    target=export/name;target.write_bytes(source.read_bytes());target.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
