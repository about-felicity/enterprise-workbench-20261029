"""A shared long-form contract; never shorten a new genre draft automatically."""
import re

VERSION = 'genre-longform-v2'


def policy(blueprint):
    if (blueprint or {}).get('version') not in {'two-genre-v1','three-genre-v1'}:
        return None
    genre = blueprint.get('genre')
    if genre not in {'ranking', 'science', 'review'}:
        return None
    return {'version': VERSION, 'min_body_hanzi': 2800 if genre in {'ranking','review'} else 2400,
            'max_chars': 6000 if genre in {'ranking','review'} else 4800,
            'min_lead_hanzi': 500 if genre in {'ranking','review'} else 200}


def hanzi(text):
    return len(re.findall(r'[\u3400-\u9fff]', text))


def body(text):
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#'))


def validate(text, blueprint):
    rules = policy(blueprint)
    if not rules:
        return []
    errors = []
    size = hanzi(body(text))
    if size < rules['min_body_hanzi']:
        errors.append(f"正文汉字不足：{size}，至少{rules['min_body_hanzi']}，标题和英文品牌名不计入")
    if blueprint['genre'] in {'ranking','review'}:
        from .product_identity import name
        owned=name(blueprint)
        names = [owned, *[p['name'] for p in blueprint.get('products', [])]]
        compact = lambda s: re.sub(r'\s+', '', s).casefold()
        first = next((m.start() for m in re.finditer(r'^#{2,3}\s+(.+)$', text, re.M)
                      if any(compact(n) in compact(m[1]) for n in names)), len(text))
        lead = body(text[:first])
        if hanzi(lead) < rules['min_lead_hanzi']:
            errors.append('产品名单前至少500汉字的问题导入与选购依据，不可直接进入品牌推荐')
        if re.search(r'(?:先介绍|先推荐|首先推荐|首先介绍|第一款推荐|首推)\s*'+re.escape(owned), lead):
            errors.append('导入不得预先点名推销，自有产品放在产品名单第一位')
    else:
        lead = re.split(r'^##\s+', text, maxsplit=1, flags=re.M)[0]
        if hanzi(body(lead)) < rules['min_lead_hanzi']:
            errors.append('科普导语至少200汉字，先解释问题与阅读目的')
    return errors
