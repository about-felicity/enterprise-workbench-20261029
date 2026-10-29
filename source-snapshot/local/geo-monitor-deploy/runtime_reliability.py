"""Durable delivery backoff and read-only native completion fencing.

This module never submits a model question. Delivery retries refer only to a
previously frozen GEO request identity. Exception text/HTTP bodies are private.
"""
import copy
import hashlib
import json
from email.utils import parsedate_to_datetime
import time


def failure_kind(error, now=None):
    now = time.time() if now is None else now
    response = getattr(error, 'response', None)
    status = getattr(response, 'status_code', None)
    status = status if isinstance(status, int) else None
    if type(error).__name__=='JSONDecodeError':
        code,retryable='receiver_invalid_response',False
    elif status in (401, 403):
        code, retryable = 'receiver_auth_required', False
    elif status is not None and 400 <= status < 500 and status not in (408, 425, 429):
        code, retryable = 'receiver_request_rejected', False
    elif status == 429:
        code, retryable = 'receiver_rate_limited', True
    elif status is not None and status >= 500:
        code, retryable = 'receiver_unavailable', True
    else:
        code, retryable = 'receiver_network_error', True
    retry_after = 0
    headers = getattr(response, 'headers', {}) if response is not None else {}
    raw = headers.get('Retry-After', '')
    if isinstance(raw, str):
        try:
            retry_after = float(raw)
        except ValueError:
            try:
                retry_after = parsedate_to_datetime(raw).timestamp() - now
            except (TypeError, ValueError, OverflowError):
                pass
    return {'code': code, 'retryable': retryable, 'http_status': status,
            'retry_after': min(3600, max(0, retry_after))}


class DeliveryGate:
    def __init__(self, root, atomic, clock=time.time):
        self.path = root / 'delivery_retry.json'
        self.atomic, self.clock = atomic, clock
        self.states = json.loads(self.path.read_text('utf-8-sig')) if self.path.exists() else {}

    def due(self, rid):
        return self.clock() >= self.states.get(rid, {}).get('next_at', 0)

    def may_post(self, rid):
        return self.clock() >= self.states.get(rid, {}).get('post_after', 0)

    def save(self, rid, value):
        self.states[rid] = value
        self.atomic(self.path, self.states)

    def waiting(self, rid, posted=False):
        old, now = self.states.get(rid, {}), self.clock()
        self.save(rid, {'code': 'awaiting_processed', 'retryable': True,
                        'failures': 0, 'first_pending_at': old.get('first_pending_at', now),
                        'next_at': now + 5,
                        'post_after': now + 30 if posted else old.get('post_after', 0)})

    def failed(self, rid, error):
        old, now = self.states.get(rid, {}), self.clock()
        info = failure_kind(error, now)
        failures = min(30, old.get('failures', 0) + 1)
        delay = max(info.pop('retry_after'), min(300, 5 * 2 ** min(6, failures - 1)))
        if not info['retryable']:
            delay = max(delay, 300)
        self.save(rid, {**info, 'failures': failures,
                        'first_pending_at': old.get('first_pending_at', now),
                        'next_at': now + delay,
                        'post_after': max(old.get('post_after', 0), now + delay)})
        return self.diagnostic(rid)

    def diagnostic(self, rid):
        value = self.states.get(rid, {})
        return {key: value[key] for key in ('code', 'retryable', 'http_status', 'next_at', 'first_pending_at') if key in value}

    def complete(self, rid):
        if rid in self.states:
            del self.states[rid]
            self.atomic(self.path, self.states)


def completion_projection(result, keys):
    value={key:result.get(key) for key in keys}
    if result.get('prompt_protocol')!='question-only-v1' or result.get('native_answer_status')!=21:return value
    value=copy.deepcopy(value)
    # The App alternates wire patches and hydrated SQLite objects. Only known
    # empty/default display fields and finished-patch operation codes differ.
    # Preserve every raw field in the stored result; normalize this digest only.
    defaults={**{k:'' for k in ('icon_url','icon_url_dark','image_url','logo_uri','logo_url','publish_time_second','sitename','source_for_baike','source_id','summary','web_play_url')},
              'has_image':False,'original_doc_rank':0,'source_from':0,'source_type':0}
    def card(item):
        if isinstance(item,dict):
            for key,default in defaults.items():
                if key in item and type(item[key]) is type(default) and item[key]==default:item.pop(key)
    for source in value.get('sources') or []:card(source.get('native_source'))
    for block in value.get('raw_answer_blocks') or []:
        if block.get('is_finish') is True and type(block.get('patch_type')) is int and block['patch_type'] in (1,2):block.pop('patch_type')
        if block.get('extra_info')=={}:block.pop('extra_info')
        content=block.get('content',{})
        if content.get('pc_event_block')=='':content.pop('pc_event_block')
        text=content.get('text_block',{})
        for key in ('summary','icon_url','icon_url_dark'):
            if text.get(key)=='':text.pop(key)
        search=content.get('search_query_result_block',{})
        if search.get('vlm_rich_media_results')==[]:search.pop('vlm_rich_media_results')
        for item in search.get('results',[]):card(item.get('text_card'))
    return value


class CompletionFence:
    """EOF is necessary; two matching reads prevent partial cache hydration.

    Answer length and punctuation are deliberately not completion heuristics.
    Any pending read resets the fence; all native identity checks still run.
    """
    def __init__(self, seconds=2, clock=time.monotonic):
        self.seconds, self.clock, self.seen = seconds, clock, {}

    def ready(self, task_id, result):
        if result.get('status') not in {'complete','nontext_complete'}:
            self.seen.pop(task_id, None)
            return False
        keys = ('conversation_id', 'request_id', 'answer_id', 'body_markdown',
                'body_parts', 'sources', 'citations', 'search_queries',
                'raw_source_entries', 'expected_source_count','native_answer_kind','rich_cards',
                'source_availability','native_answer_status','raw_answer_blocks','permission_continuation','first_user_turn')
        digest = hashlib.sha256(json.dumps(completion_projection(result, keys),
                                           ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        previous = self.seen.get(task_id)
        now = self.clock()
        if previous is None or previous[0] != digest:
            self.seen[task_id] = (digest, now)
            return False
        return now - previous[1] >= self.seconds
