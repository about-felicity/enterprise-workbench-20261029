"""Deliver proven Baidu prose separately from full source-backed captures.

No browser actions. The existing receiver stores the full raw observation and
keeps source_capture_complete=false; source KPIs retain their strict contract.
"""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
from geo_source_cards.runtime import atomic_json
from runtime_reliability import DeliveryGate


def envelope(row, value, config):
    url = urlsplit(str(value.get('url') or ''))
    evidence = value.get('source_exposure_evidence') or {}
    if not (
        config['model'] == 'baidu_ai' and value.get('availability') == 'body_only'
        and value.get('capture_mode') == 'baidu_search_ai'
        and value.get('card_available') is True
        and value.get('body_capture_complete') is True
        and value.get('source_capture_complete') is False
        and value.get('source_exposure') == 'not_publicly_exposed'
        and evidence.get('card_present') is True
        and not evidence.get('declared_count') and not evidence.get('drawer_opened')
        and not value.get('sources') and not value.get('expected_source_count')
        and str(value.get('body') or '').strip()
        and value.get('fresh_search') is True
        and value.get('verified_question') == value.get('question')
        and url.hostname in {'www.baidu.com', 'baidu.com'} and url.path == '/s'
        and parse_qs(url.query).get('wd') == [value['question']]
    ):
        raise ValueError('unproven_baidu_body_observation')
    record = {
        'collector_model': 'wenxin', 'question': value['question'], 'prompt': value['question'],
        'web_body': value['body'], 'sources': [], 'expected_source_count': 0,
        'source_capture_complete': False, 'body_capture_complete': True,
        'source_list_present': False, 'status': 'success', 'card_available': True,
        'capture_warning': '百度卡片正文完整；页面未公开引用来源，信源统计不计入此条。',
        'availability': 'body_only', 'source_exposure': 'not_publicly_exposed',
        'task_id': row['ordinal'] * config['rounds'] + row['round'],
        'capture_task_id': row['task_id'], 'batch_id': row['batch'], 'round': row['round'],
        'serial': config['device'], 'started_at': value['captured_at'], 'finished_at': value['captured_at'],
        'capture_mode': 'baidu_search_ai', 'url': value['url'], 'capture_label': '百度卡片',
        'daily_surface_target': config.get('daily_target_rounds',config['rounds']), 'capture_result': value,
    }
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    rid = hashlib.sha256(('wenxin\n' + config['device'] + '\n' + raw).encode()).hexdigest()
    return {'version': 1, 'model': 'wenxin', 'source_device': config['device'],
            'request_id': rid, 'sent_at': row['finished'], 'record': record}


def verify_receipt(reply, item):
    analysis = reply.get('analysis') or {}
    if (reply.get('request_id') != item['request_id'] or reply.get('model') != 'wenxin'
        or reply.get('source_device') != item['source_device'] or not reply.get('stored_run_id')
        or analysis.get('quarantined') or analysis.get('answer_present') is not True
        or analysis.get('answer_length') != len(item['record']['web_body'].strip())
        or analysis.get('body_capture_complete') is not True
        or analysis.get('source_capture_complete') is not False
        or analysis.get('source_count') != 0 or analysis.get('sources') != []):
        raise ValueError('body_only_receipt_mismatch')


class Delivery:
    def __init__(self, root, config, receiver_root):
        self.root, self.config = Path(root) / 'body-only', config
        for name in ('outbox', 'receipts'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        receiver = json.loads((Path(receiver_root) / 'runtime/lan_result_receiver.json').read_text())
        self.url = 'http://127.0.0.1:' + str(receiver['port'])
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers['Authorization'] = 'Bearer ' + receiver['token']
        self.gate = DeliveryGate(self.root, atomic_json)

    def sync(self, rows):
        result = {'observations': 0, 'processed': 0, 'pending_delivery': 0, 'errors': []}
        unique_processed = set()
        posted = 0
        for row in rows:
            if row['state'] != 'completed':
                continue
            value = json.loads(row['result'])
            if value.get('availability') != 'body_only':
                continue
            result['observations'] += 1
            try:
                item = envelope(row, value, self.config)
                rid = item['request_id']
                outbox = self.root / 'outbox' / (rid + '.json')
                path = self.root / 'receipts' / (rid + '.json')
                if not outbox.exists():
                    atomic_json(outbox, item)
                elif json.loads(outbox.read_text()) != item:
                    raise ValueError('body_outbox_identity_changed')
                if path.exists():
                    verify_receipt(json.loads(path.read_text()), item)
                    result['processed'] += 1
                    unique_processed.add((value['question'], value['body']))
                    continue
                if self.gate.due(rid):
                    response = self.session.get('http://127.0.0.1:8803/api/receipts/wenxin/' + rid, timeout=5)
                    response.raise_for_status()
                    reply = response.json()
                    if reply.get('status') == 'processed':
                        verify_receipt(reply['receipt'], item)
                        atomic_json(path, reply['receipt'])
                        self.gate.complete(rid)
                        result['processed'] += 1
                        unique_processed.add((value['question'], value['body']))
                    elif posted < 2 and self.gate.may_post(rid):
                        response = self.session.post(self.url + '/api/v1/models/wenxin/results', json=item, timeout=8)
                        response.raise_for_status()
                        ack = response.json()
                        if not ack.get('ok') or ack.get('request_id') != rid:
                            raise ValueError('body_receiver_ack_mismatch')
                        posted += 1
                        self.gate.waiting(rid, posted=True)
                    else:
                        self.gate.waiting(rid)
            except requests.RequestException as error:
                result['errors'].append({'task_id': row['task_id'], **self.gate.failed(rid, error)})
            except (OSError, ValueError, KeyError, TypeError) as error:
                result['errors'].append({'task_id': row['task_id'], 'code': type(error).__name__, 'retryable': False})
        result['pending_delivery'] = result['observations'] - result['processed']
        result['unique_processed'] = len(unique_processed)
        atomic_json(self.root / 'health.json', {'time': time.time(), **result})
        return result


def merge_health(health, root):
    """Present body observations honestly, retaining the source-backed counts."""
    path = Path(root) / 'body-only/health.json'
    body = health.get('body_only_delivery')
    if body is None and path.exists():
        body = json.loads(path.read_text())
    if not body:
        return health
    value = dict(health)
    observed, processed = body['observations'], body['processed']
    unique = body.get('unique_processed', processed)
    value.update(source_backed_captured=health.get('captured', 0),
                 source_backed_processed=health.get('processed', 0),
                 captured=health.get('captured', 0) + observed,
                 processed=health.get('processed', 0) + processed,
                 unique_processed=health.get('unique_processed', 0) + unique,
                 duplicates=health.get('duplicates', 0) + processed - unique,
                 unavailable=max(0, health.get('unavailable', 0) - observed),
                 body_only_observations=observed, body_only_processed=processed)
    value['errors'] = [*health.get('errors', []), *body.get('errors', [])]
    if (value.get('status') == 'complete_with_unavailable' and not value['unavailable']
        and processed == observed and not body.get('errors')):
        value['status'] = 'complete'
        value['progress'] = {**value.get('progress', {}), 'phase': 'complete', 'pending_delivery': 0}
    return value


if __name__ == '__main__':
    import argparse
    from capture_bridge import read_rows, load
    from geo_source_cards.runtime import process_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--base', type=Path, default=Path('/opt/monitor/geo-capture'))
    parser.add_argument('--receiver-root', type=Path, default=Path('/opt/monitor'))
    args = parser.parse_args()
    config = load(args.config)
    assert config['model'] == 'baidu_ai'
    root = args.base / 'batches' / config['batch']
    runner = Delivery(root, config, args.receiver_root)
    with process_lock(root / 'body-only/delivery.lock'):
        deadline = time.time() + 1800
        while time.time() < deadline:
            rows = read_rows(root / 'collector/tasks.sqlite', config['batch'])
            result = runner.sync(rows)
            if any(error.get('retryable') is False for error in result['errors']):
                raise SystemExit('Baidu body delivery requires review; see private health file')
            if (len(rows) == len(config['questions']) * config['rounds']
                and all(row['state'] == 'completed' for row in rows)
                and not result['pending_delivery'] and not result['errors']):
                print(json.dumps(result))
                break
            time.sleep(5)
        else:
            raise SystemExit('Baidu body delivery timeout; durable queue preserved')
