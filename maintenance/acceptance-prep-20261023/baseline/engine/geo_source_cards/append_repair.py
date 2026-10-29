"""Apply evidence-reviewed additions without losing previously written text."""
import copy
import re

MARKER = '[APPEND_REPAIR_V1]'

def eligible_error(reason):
    parts=re.split(r';\s*',reason.removeprefix('Draft checks rejected: '))
    return bool(parts) and all(any(token in part for token in ('正文汉字不足','正文过短','科普导语至少','产品名单前至少')) for part in parts)


def apply(previous, claims, sections, answer):
    additions = answer.get('additions')
    if not isinstance(additions, list) or not 1 <= len(additions) <= 5:
        raise ValueError('Expected one to five anchored additions')
    edits = []
    anchors = set()
    for item in additions:
        anchor, text = item.get('after'), item.get('text')
        if not isinstance(anchor, str) or not anchor.strip() or previous.count(anchor) != 1 or anchor in anchors:
            raise ValueError('Addition anchor must occur exactly once in original draft')
        if anchor.lstrip().startswith('#'):
            raise ValueError('Addition anchor must be a complete body paragraph, preserving the original opening')
        if not isinstance(text, str) or not text.strip() or len(text) > 1800:
            raise ValueError('Invalid addition text')
        if any(line.lstrip().startswith('#') for line in text.splitlines()):
            raise ValueError('Additions cannot change outline headings')
        anchors.add(anchor)
        edits.append((previous.index(anchor)+len(anchor), text.strip()))
    result = previous
    for index, text in sorted(edits, reverse=True):
        result = result[:index]+'\n\n'+text+result[index:]
    mapping = copy.deepcopy(claims)
    extra = answer.get('additional_claims', [])
    if not isinstance(extra, list):
        raise ValueError('Invalid additional claims')
    mapping['claims'].extend(extra)
    return {**answer, 'draft_markdown':result, 'claim_map':mapping,
            'knowledge_to_sections':copy.deepcopy(sections)}
