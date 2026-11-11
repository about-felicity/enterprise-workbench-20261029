"""Keep ambiguous send attempts for readback without blocking independent tasks."""
import hashlib
import json
from unattended_worker import atomic_json


def identity(task):
    return {'prepared_at': task.get('prepared_at'),
            'question_sha256': hashlib.sha256(task['question'].encode()).hexdigest()}


def valid(root, queue, task):
    if task.get('request_id') or not task.get('prepared_at'):
        return False
    path = root / 'uncertain_send_quarantine.json'
    if not path.exists():
        return False
    saved = json.loads(path.read_text()).get(task['task_id'])
    if saved != identity(task):
        return False
    boundary = queue.attempt_boundary(task['task_id'])
    return bool(queue.db.execute("select 1 from events where task_id=? and event='send_click_intent_committed' and id>?",
                                 (task['task_id'], boundary)).fetchone())


def quarantine(root, queue, task, observed, now):
    if (task.get('request_id') or observed.get('request_id') or observed.get('native_request_confirmed')
            or task.get('state') not in {'prepared','needs_attention'} or not task.get('prepared_at')
            or now - task['prepared_at'] <= 900):
        return False
    boundary = queue.attempt_boundary(task['task_id'])
    if not queue.db.execute("select 1 from events where task_id=? and event='send_click_intent_committed' and id>?",
                            (task['task_id'], boundary)).fetchone():
        return False
    path = root / 'uncertain_send_quarantine.json'
    saved = json.loads(path.read_text()) if path.exists() else {}
    proof = identity(task)
    if saved.get(task['task_id']) == proof and task['state'] == 'needs_attention':
        return False
    saved[task['task_id']] = proof
    atomic_json(path, saved)
    with queue.db:
        queue.db.execute("update tasks set state='needs_attention',error=? where task_id=?",
                         ('发送结果未确认；已隔离并保留原始证据，后续只读回查，不重复发送', task['task_id']))
        queue.event(task['task_id'], 'uncertain_send_quarantined', 'No resend; independent pending tasks may continue')
    return True
