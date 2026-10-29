"""Creation-only bounded search adapter. Does not alter main GEO or DeepSeek."""
import json,time
from geo_source_cards import search_recovery
from geo_source_cards.journal import Journal

MAX_ATTEMPTS=3
OriginalRecovery=search_recovery.SearchRecovery

def settle_failed_reads(db,batch):
    if not db.execute("select 1 from sqlite_master where name='search_recovery_attempts'").fetchone():return
    # Only exhausted, known read failures; never relabel success or an in-flight call.
    with db:
        db.execute("""update captures set state='failed_deferred'
          where batch=? and model in ('baidu_ai','wenxin_card')
          and state in ('pending','needs_attention','failed_deferred')
          and task_id in (select task_id from search_recovery_attempts where kind='read_error'
                         group by task_id having count(*)>=?)""",(batch,MAX_ATTEMPTS))

def bounded_automatic(self,batch):
    settle_failed_reads(self.db,batch)
    with self.db:
        for row in self.db.execute("select * from captures where batch=? and state='needs_attention'",(batch,)).fetchall():
            if row['model'] not in ('baidu_ai','wenxin_card'):continue
            self.db.execute("update captures set state='pending' where task_id=?",(row['task_id'],))
            self.db.execute('insert into automatic_recovery_events(task_id,event,details,epoch) values(?,?,?,?)',
                (row['task_id'],'creation_read_retry',json.dumps({'error':row['error']}),time.time()))

class BoundedRecovery(OriginalRecovery):
    def failure(self,task,error,partial=None):
        result=super().failure(task,error,partial)
        if result and result['kind']=='read_error':
            count=self.db.execute("select count(*) from search_recovery_attempts where task_id=? and kind='read_error'",(task['task_id'],)).fetchone()[0]
            result['attempt_limit']=MAX_ATTEMPTS
            if count>=MAX_ATTEMPTS:
                with self.db:self.db.execute("update captures set state='failed_deferred' where task_id=? and state in ('pending','failed_deferred')",(task['task_id'],))
                result.update(exhausted=True,defer=True,status='failed_deferred')
            self.publish(**result)
        return result

def main():
    from geo_source_cards import cli
    args=cli.parse_args()
    if args.model not in ('baidu_ai','wenxin_card'):raise ValueError('This adapter is only for creation search channels')
    from pathlib import Path
    if not args.runtime_dir or Path('/opt/monitor/geo-content') not in args.runtime_dir.resolve().parents:raise ValueError('Creation runtime required')
    from .materials import supplement_origin,ROOT
    origin=supplement_origin(ROOT)
    if origin!=ROOT:
        from geo_source_cards import search_profiles
        original=search_profiles.profile_for_search
        day=args.runtime_dir.parents[1].name
        profile=original(origin/'days'/day/args.model/'collector',args.model)
        search_profiles.profile_for_search=lambda runtime,model: profile if model==args.model else original(runtime,model)
    # No unavailable placeholder may be exported as a successful observation.
    args.optional_baidu=False
    Journal.automatic_recovery=bounded_automatic
    search_recovery.SearchRecovery=BoundedRecovery
    try:
        code=cli.run(args)
    except RuntimeError as error:
        if str(error)=="等待人工处理百度验证；不会因重启自动恢复":return 77
        raise
    if code==2:
        import sqlite3
        with sqlite3.connect(args.runtime_dir/'tasks.sqlite') as db:
            states={r[0] for r in db.execute('select distinct state from captures where batch=?',(args.batch,))}
        if states and states<={'completed','failed_deferred'}:return 0
    return code

if __name__=='__main__':raise SystemExit(main())
