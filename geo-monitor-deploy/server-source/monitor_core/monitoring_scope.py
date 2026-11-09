"""Keep specific user prompts out of the broad-question performance baseline."""
import re
import unicodedata
from monitor_core.recommendation_questions import PRODUCTS, _ALIASES, _QUESTION_ALIASES


def key(value):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]+', '', unicodedata.normalize('NFKC', value).casefold())


PRIMARY = {key(pattern.format(product)) for product in (*PRODUCTS, *_ALIASES)
           for pattern in ('推荐一款{}', '推荐{}', '{}推荐', '{}')}
PRIMARY.update(key(q) for q in _QUESTION_ALIASES)


def scope_fields(record):
    native = record.get('native_result') or {}
    capture = record.get('capture_result') or {}
    prompt = str(record.get('wire_question') or record.get('prompt')
                 or native.get('wire_question') or capture.get('question')
                 or record.get('question') or record.get('chatTitle') or '').strip()
    return {'original_prompt': prompt,
            'monitoring_scope': 'secondary' if prompt and key(prompt) not in PRIMARY else 'primary'}
