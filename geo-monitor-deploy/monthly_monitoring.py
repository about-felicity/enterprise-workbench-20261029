"""Overlay user-managed monthly questions onto the existing single-lane queues."""
from datetime import datetime
import hashlib
import json
import subprocess
import time
import unicodedata
from zoneinfo import ZoneInfo

MODELS = ('doubao1', 'doubao2', 'doubao3', 'doubao4', 'baidu_ai', 'wenxin_card', 'yuanbao')


def question_key(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def target(config, question):
    return config.get('question_targets', {}).get(question, config['rounds'])


def active_questions(rows, day, now):
    """Only the current month and currently open version; never old revisions."""
    questions = {}
    for row in sorted(rows, key=lambda r: r['product']):
        if str(row['month'])[:7] != day[:7]:
            continue
        for term in row['terms']:
            if not term.get('active') or not term.get('versions'):
                continue
            version = term['versions'][-1]
            if not any(start <= now and (end is None or now < end)
                       for start, end in version.get('windows', [])):
                continue
            for question in version['questions']:
                key = question_key(question)
                if key:
                    questions.setdefault(key, question)
    return [questions[key] for key in sorted(questions)]


def owner(question):
    # Adding/removing another term never migrates today's already sampled term.
    return 'doubao' + str(int(hashlib.sha256(question_key(question).encode()).hexdigest(), 16) % 4 + 1)


def overlay(config, model, questions, day, doubao_primary=()):
    primary = config.get('primary_questions', config['questions'])
    keys = {question_key(q) for q in primary}
    if model.startswith('doubao'):
        keys.update(question_key(q) for q in doubao_primary)
    secondary = [q for q in questions if question_key(q) not in keys
                 and (not model.startswith('doubao') or owner(q) == model)]
    return {**config, 'primary_questions': list(primary), 'secondary_questions': secondary,
            'questions': list(primary) + secondary,
            'question_targets': {**{q: config['rounds'] for q in primary}, **{q: 1 for q in secondary}},
            'secondary_month': day[:7]}


def database_questions(day):
    month = datetime.strptime(day, '%Y-%m-%d').strftime('%Y-%m-01')
    sql = ("select coalesce(json_agg(t),'[]') from (select product,month,terms "
           "from geo_monthly_keywords where month=date '%s')t") % month
    return json.loads(subprocess.check_output(
        ['docker', 'exec', 'monitor-postgres', 'psql', '-U', 'monitor_app', '-d', 'monitor', '-Atc', sql],
        text=True, timeout=12))


def sync(control, day, rows, now=None):
    """Persist goals only: never launch, stop, unpause or mutate a running batch."""
    now = time.time() if now is None else now
    questions = active_questions(rows, day, now)
    changed = []
    with control.lock, control.connect() as db:
        plans = {r['model']: dict(r) for r in db.execute('select * from daily_tasks where day=?', (day,))
                 if r['model'] in MODELS}
        configs = {model: json.loads(row['config']) for model, row in plans.items()}
        primary = [q for model, cfg in configs.items() if model.startswith('doubao')
                   for q in cfg.get('primary_questions', cfg['questions'])]
        for model, row in plans.items():
            # Let the durable launch intent finish/adopt first, then sync next pass.
            if str(row['batch'] or '').startswith('launch:'):
                continue
            cfg = overlay(configs[model], model, questions, day, primary)
            if cfg == configs[model]:
                continue
            status = 'queued' if row['status'] == 'complete' and row['desired'] == 'running' else row['status']
            db.execute('update daily_tasks set config=?,revision=revision+1,status=?,updated=? where model=? and day=?',
                       (json.dumps(cfg, ensure_ascii=False), status, now, model, day))
            changed.append(model)
    return {'month': day[:7], 'unique_questions': len(questions), 'changed': changed,
            'checked_at': now, 'status': 'ready'}
