"""Use the existing authenticated control API with durable operation identities."""
import argparse
import json
from pathlib import Path
import time
import uuid
import requests

BASE = 'http://127.0.0.1:8803'
ROOT = Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start')
ROOT.mkdir(parents=True, exist_ok=True)
session = requests.Session()

def panel():
    r = session.get(BASE + '/api/panel', timeout=30)
    r.raise_for_status()
    return r.json()

def act(model, action, payload):
    data = panel()
    key = uuid.uuid4().hex
    evidence = ROOT / (model + '-' + action + '-' + key + '.json')
    record = {'at': time.time(), 'id': key, 'model': model, 'action': action, 'payload': payload}
    evidence.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    response = session.post(BASE + '/api/control/' + model + '/' + action,
                            headers={'Origin': BASE, 'X-CSRF-Token': data['csrf'], 'X-Action-Id': key},
                            json=payload, timeout=40)
    record.update(http_status=response.status_code, result=response.json())
    evidence.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(json.dumps({'model': model, 'action': action, 'http_status': response.status_code,
                      'result': record['result'], 'id': key}, ensure_ascii=False), flush=True)
    response.raise_for_status()
    return record['result']

def summary():
    for item in panel()['models']:
        if item['id'] in {'yuanbao', 'deepseek'}:
            current = item['current']
            print(json.dumps({'model': item['id'], 'login': item['login_status'],
                              'revision': item['revision'], 'settings': item['settings'],
                              'current': {key: current.get(key) for key in
                                          ['batch', 'state', 'service_state', 'planned', 'processed',
                                           'needs_review', 'progress', 'created_at']}}, ensure_ascii=False))

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['login', 'login-deepseek', 'sync', 'summary', 'new-deepseek', 'new-yuanbao'])
args = parser.parse_args()
if args.mode == 'login-deepseek':
    act('deepseek', 'login', {})
elif args.mode == 'login':
    for model in ['deepseek', 'yuanbao']:
        act(model, 'login', {})
elif args.mode == 'sync':
    act('deepseek', 'login_sync', {})
elif args.mode.startswith('new-'):
    model = args.mode[4:]
    item = next(m for m in panel()['models'] if m['id'] == model)
    assert item['current']['batch'].startswith('geo-panel-' + model + '-20261015-'), 'Inspect existing newer task first'
    if model == 'deepseek':
        assert item['settings']['rounds'] == 3 and item['settings']['interval'] == 600
    else:
        assert item['settings']['rounds'] == 5 and item['settings']['interval'] == 45
    act(model, 'new', {'revision': item['revision']})
else:
    summary()
