"""Decode known empty Yuanbao rendering tokens without inventing answer text.

Raw request envelopes and native snapshots remain the acquisition evidence.
This module only produces the readable/analytical projection of that evidence.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs

NORMALIZATION_VERSION = 'yuanbao-native-text-v2'
_ANCHOR = re.compile(r'\[\]\(@(?:mark_underline|replace)=[A-Za-z0-9_-]+\)')
_CARD = re.compile(r'!\[@replace_(goods|videoBoxV2|miniProgramBox)&[^\]\r\n]+\]\(https://yuanbao/?\)')
_STYLE = re.compile(r'\[([^\]\r\n]*)\]\(@stylelink\?([^\r\n)]+)\)')
_MEDIA = re.compile(r'!\[([^\]\r\n]*)\]\(@replace=media_[A-Za-z0-9_-]+\)')
_UNHANDLED = re.compile(r'@(?:mark_[A-Za-z0-9_]+|replace(?:_[A-Za-z0-9_]+)?|stylelink)(?=[=?&])')


def decode_native_text(value):
    raw = str(value or '')
    text, anchors = _ANCHOR.subn('', raw)
    style_links = 0
    def visible_style_link(match):
        nonlocal style_links
        query = parse_qs(match[2])
        key = (query.get('key') or [''])[0]
        if key.startswith('@replace_miniProgram_') and query.get('display') == ['miniProgram']:
            style_links += 1
            return match[1]
        return match[0]
    text = _STYLE.sub(visible_style_link, text)
    media_cards = 0
    def visible_media_label(match):
        nonlocal media_cards
        media_cards += 1
        return '' if match[1].casefold() in {'', 'goods', 'image', 'video'} else match[1]
    text = _MEDIA.sub(visible_media_label, text)
    cards = list(_CARD.finditer(text))
    text = _CARD.sub('', text)
    unhandled = len(_UNHANDLED.findall(text))
    if not anchors and not cards and not style_links and not media_cards and not unhandled:
        return raw, {}
    # Preserve all words, punctuation, citations and their original ordering.
    # Collapse only blank runs left behind by empty visual-control paragraphs.
    text = re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', text).strip()
    return text, {
        'version': NORMALIZATION_VERSION,
        'raw_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'raw_length': len(raw), 'clean_length': len(text),
        'empty_controls_removed': anchors,
        'goods_cards_archived': sum(m[1] == 'goods' for m in cards),
        'video_cards_archived': sum(m[1] == 'videoBoxV2' for m in cards),
        'mini_program_cards_archived': sum(m[1] == 'miniProgramBox' for m in cards),
        'style_links_decoded': style_links,
        'media_cards_archived': media_cards,
        'unhandled_controls': unhandled,
    }


def clean_native_text(value):
    return decode_native_text(value)[0]
