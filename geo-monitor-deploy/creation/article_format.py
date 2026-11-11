"""Shared publication checks for approved drafts and their editorial revisions."""

import hashlib
import re


VERSION = 'publication-format-v3'

_ORDINAL = r'(?:[一二三四五六七八九十零]{1,3}|\d{1,2})'
_PRODUCT = re.compile(r'^(?:[^：:。！？]{2,16}总结[：:])?第' + _ORDINAL + r'(款|名|个产品)[：:]\s*\S')
_SECTION = re.compile(r'^[一二三四五六七八九十]{1,3}、\s*\S')
_SUBSECTION = re.compile(r'^[（(]' + _ORDINAL + r'[）)]\s*[^。！？]{2,24}[：:]$')
_LABEL = re.compile(r'^(?:Q|A|问|答|推荐理由|产品特点|核心卖点|来源|图片来源)[：:]', re.I)
_HEADING = re.compile(r'^(#{2,6})\s+(.+)$')
_RANK_ENTRY = re.compile(
    rf'^(?:第(?P<ordinal>{_ORDINAL})(?:款|名|位|个产品)[：:、.． |｜]+|'
    rf'(?:TOP|NO[.．]?)\s*(?P<top>{_ORDINAL})[：:、.． ]+|'
    rf'(?:推荐|品牌)(?P<brand>{_ORDINAL})[：:、.． ]+|'
    rf'(?P<number>\d{{1,2}})(?:[.．、:：)）]|\ufe0f?\u20e3)\s*)(?P<name>\S.+)$', re.I,
)
_PRODUCT_WORD = re.compile(
    r'洗发(?:水|露|乳)|洗液|护发(?:油|精油|膜|乳)|发油|润发|(?:染发|护染)(?:剂|膏|霜|啫喱|梳|泡)|'
    r'精华(?:液|霜|油|乳|原液)?|面霜|淡斑霜|增长液|滋养液|凝胶|安瓶|发膜|面膜|啫喱|'
    r'育发液|生发液|乳液|防脱小水枪|染梳|祛痘修红|修护霜'
)
_BODY_LABEL = re.compile(
    r'^(?:产品定位|定位标签|适用人群|适配人群|安全提示|推荐理由|核心卖点|产品特点|'
    r'价格|质地|使用方法|温馨提示|配方思路|使用感受)\s*[：:|｜]'
)
_PLATFORM_NOTE = re.compile(
    r'本平台所发布信息|本账号发布目的|本账号赞同|原单位或组织独立承担|'
    r'(?:本网站|本站|本平台).{0,14}(?:转载|不承担)|本文系.{0,8}转载|转载请注明'
)
_STAFF = re.compile(r'^(?:编辑|责任编辑|本文编辑|校对|审核|责编|初审|复审|终审|记者|作者|供图|编审|排版|主编|监制)\s*[：:]\s*\S.{0,32}$')
_COUNT_TOKEN = r'(?:[1-9]\d?|[一二三四五六七八九十两]{1,3})'
_TITLE_COUNT = re.compile(rf'(?<![\d一二三四五六七八九十])({_COUNT_TOKEN})\s*(?:款|个品牌|个产品)|(?:TOP|排行榜前)\s*({_COUNT_TOKEN})', re.I)
_BODY_COUNT = re.compile(rf'(?:本次(?:选取|选了|对比|盘点)|以上(?:这)?|以下(?:这)?|下面这|这)\s*({_COUNT_TOKEN})\s*款(?:产品|单品)')
_CANONICAL_ENTRY = re.compile(rf'^第\s*({_ORDINAL})\s*款[：:]\s*(\S.+)$')
_INTRO_LIST = re.compile(r'(?:产品|单品|对象|品牌)(?:清单)?(?:分别(?:是|为)|包括|如下)[：:]?\s*(.+)|(?:选取|选了|对比|汇总|涵盖).{0,34}?(?:产品|单品|品牌)[：:]\s*(.+)')
_LIST_SPLIT = re.compile(r'、|，以及(?:一款[^，。]{0,22}——)?|，及(?:一款[^，。]{0,20}——)?')


def _short_heading(line):
    return 4 <= len(line) <= 74 and not re.search(r'[。！？!?；;]$', line)


def normalize(markdown):
    """Recover clear headings without changing the substance of the text."""
    lines = markdown.splitlines()
    if not lines or not lines[0].startswith('# '):
        return markdown
    changed = False

    flat = not any(re.match(r'^#{2,6}\s', line) for line in lines)
    numbered = sum(bool(_SECTION.match(line.strip())) for line in lines) >= 2
    has_product_list = sum(bool(_PRODUCT.match(line.strip())) for line in lines) >= 2
    out = [lines[0]]
    fenced = False
    section_level = 0
    for index, line in enumerate(lines[1:], 1):
        text = line.strip()
        if text.startswith(('```', '~~~')):
            fenced = not fenced
        heading = re.match(r'^(#{2,6})\s', text)
        if heading:
            section_level = len(heading[1])
        if fenced or not text or text.startswith(('#', '```', '~~~')):
            out.append(line)
            continue

        if text.startswith('**') and text.endswith('**'):
            text = text[2:-2].strip()
        product = _PRODUCT.match(text)
        title, separator, detail = text.partition('。') if product else (text, '', '')
        if product and _short_heading(title) and (not separator or detail.strip()):
            level = 3 if numbered or (not flat and section_level >= 2) or (product[1] == '名' and section_level == 2) else 2
        elif (numbered and _SECTION.match(text) or text.startswith(('💎 ', '💰 ', '💡 '))) and _short_heading(text):
            level = 2
        elif flat and _SUBSECTION.fullmatch(text):
            level = 3
        elif (flat and has_product_list and index > 2 and not lines[index - 1].strip() and index + 2 < len(lines)
              and not lines[index + 1].strip() and len(lines[index + 2].strip()) >= 45
              and _short_heading(text) and len(text) <= 38 and not _LABEL.match(text)
              and not text.startswith(('-', '*', '+', '>', '|', '!', '[', '（', '('))
              and not re.match(r'^\d+[.、．）)]', text)):
            level = 2
        else:
            out.append(line)
            continue

        changed = True
        if not product:
            section_level = level
        out.extend(['', '#' * level + ' ' + title, ''])
        if detail:
            out.append(detail.lstrip())
    if not changed:
        return markdown
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out).rstrip()) + '\n'


def _visible(line):
    return re.sub(r'^#{1,6}\s+', '', line.strip()).strip('* ').strip()


def _comparable(text):
    return re.sub(r'[\W_]+', '', text).casefold()


def _number(value):
    if value.isdigit():
        return int(value)
    digits = '零一二三四五六七八九'
    value = value.replace('两', '二')
    if '十' in value:
        tens, _, units = value.partition('十')
        if (tens or '一') in tuple(digits) and (units or '零') in tuple(digits):
            return 10 * digits.index(tens or '一') + digits.index(units or '零')
    return digits.index(value) if len(value) == 1 and value in digits else None


def _product_name(text):
    name = re.split(r'——|｜|\s+\|\s+|【|[：:]', text, maxsplit=1)[0].strip()
    return (5 <= len(name) <= 52 and _PRODUCT_WORD.search(name)
            and not re.search(r'[。；！？：:，,]|^(?:本次|常见|怎么|如何|几款|以上|选购|其他|不同)', name)
            and not re.search(r'建议|方案|选购|推荐|解析|榜单|比较|适合|优点|哪些|是什么|挑选|使用方法|挑法|的作用|产品介绍|逐一|逐款', name)
            and not re.match(rf'^{_COUNT_TOKEN}\s*款', name))


def _entry(text):
    match = _RANK_ENTRY.fullmatch(text)
    if not match:
        return None
    family = next(key for key in ('ordinal', 'top', 'brand', 'number') if match[key])
    name = match['name']
    if family == 'number' and not (_product_name(name) or (len(name) <= 75 and _product_name(re.split('[：:]', name)[-1]))):
        return None
    return family, _number(match[family]), name


def _restore_rank_headings(markdown, ranking):
    if not ranking:
        return markdown
    lines = markdown.splitlines()
    headings = [_visible(line) for line in lines[1:] if _HEADING.match(line)]
    candidates = [(_visible(line), index) for index, line in enumerate(lines[1:], 1)
                  if not _HEADING.match(line) and _short_heading(_visible(line))]
    product_lines = {index for value, index in candidates if _product_name(value) and not _entry(value)}
    ranks = {index for value, index in candidates if _entry(value)}
    if len(product_lines) < 2:
        product_lines.clear()
    if len(ranks) < 2 and not any(_entry(value) for value in headings):
        ranks.clear()
    candidate_lines = product_lines | ranks
    if not candidate_lines:
        return markdown
    out = []
    fenced = False
    for index, line in enumerate(lines):
        value = line.strip()
        if value.startswith(('```', '~~~')):
            fenced = not fenced
        if index not in candidate_lines or fenced or _BODY_LABEL.match(value) or value.startswith(('- ', '+ ', '> ', '![', '|')):
            out.append(line)
        else:
            out.extend(('', '## ' + _visible(line), ''))
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out).rstrip()) + '\n'


def _strip_source_footer(markdown, reference):
    lines = markdown.splitlines()
    tail = [i for i, line in enumerate(lines) if i and line.strip()][-12:]
    issues = []
    normalized_reference = _comparable(reference)
    for index in tail:
        line = _visible(lines[index])
        platform = _PLATFORM_NOTE.search(line)
        if not (platform or _STAFF.fullmatch(line)):
            continue
        copied = bool(normalized_reference and _comparable(line) in normalized_reference)
        if copied:
            lines[index] = ('本文涉及产品推广，相关产品信息供选购参考。'
                            if '本内容为广告' in line or '本文为推广资讯' in line else '')
        else:
            issues.append('稿尾含平台声明或人员署名，请核对发布主体')
    revised = '\n'.join(lines).rstrip() + '\n'
    if revised == markdown.rstrip() + '\n':
        return markdown, tuple(dict.fromkeys(issues))
    return re.sub(r'\n{3,}', '\n\n', revised), tuple(dict.fromkeys(issues))


def _roster_counts(markdown):
    lines = markdown.splitlines()
    groups = {}
    unnumbered = []
    for line in lines:
        if not _HEADING.match(line):
            continue
        title = _visible(line)
        entry = _entry(title)
        if entry:
            family, number, name = entry
            groups.setdefault(family, []).append((number, _comparable(name)))
        elif _product_name(title):
            unnumbered.append(_comparable(title))
    counts = {len(items) for items in groups.values()
              if len(items) >= 2 and [number for number, _ in items] == list(range(1, len(items) + 1))
              and len(set(name for _, name in items)) == len(items)}
    if not counts and len(unnumbered) >= 2 and len(set(unnumbered)) == len(unnumbered):
        counts.add(len(unnumbered))

    body = [line for line in lines[1:] if line.strip()]
    for index, line in enumerate(body[:6]):
        rest = _comparable('\n'.join(body[index + 1:]))
        for sentence in line.split('。'):
            match = _INTRO_LIST.search(sentence)
            if not match:
                continue
            names = [_comparable(name) for name in _LIST_SPLIT.split(match[1] or match[2])]
            if (len(names) >= 2 and len(set(names)) == len(names)
                    and all(3 <= len(name) <= 65 and name in rest for name in names)):
                counts.add(len(names))
    return counts


def _publication_issues(markdown, ranking, reviewed_count=None):
    lines = markdown.splitlines()
    if not lines or not lines[0].startswith('# '):
        return ('缺少独立文章标题',)
    issues = []
    headings = [line for line in lines if _HEADING.match(line)]
    if ranking and (not headings or (len(markdown) >= 1300 and len(headings) < 2)):
        issues.append('榜单缺少独立的产品小标题')
    elif not headings and len(markdown) >= 1800:
        issues.append('长文缺少主题小标题')
    title_counts = set()
    for match in _TITLE_COUNT.finditer(lines[0]):
        number = _number(match[1] or match[2])
        if number is not None:
            comparison = match[1] and lines[0][:match.start()].rstrip().endswith(('与', '另加'))
            title_counts.add(number + bool(comparison))
    canonical = [match.groups() for line in headings
                 if (match := _CANONICAL_ENTRY.fullmatch(_visible(line)))]
    numbers = [_number(number) for number, _ in canonical]
    names = [_comparable(name) for _, name in canonical]
    if reviewed_count is None and canonical and (
            numbers != list(range(1, len(numbers) + 1)) or len(set(names)) != len(names)):
        issues.append('产品小标题编号跳号、重复或重复列出同一产品，请核对清单')
    if title_counts and (ranking or canonical):
        evidence = {reviewed_count} if reviewed_count is not None else _roster_counts(markdown)
        if evidence and evidence != title_counts:
            titles = '、'.join(map(str, sorted(title_counts)))
            body = '、'.join(map(str, sorted(evidence)))
            issues.append(f'标题写 {titles} 款，正文名单核对为 {body} 款，请统一款数')
        elif len(title_counts) != 1 or (not evidence and title_counts != {1}):
            issues.append('标题写了具体款数，但正文缺少可核对的产品清单')
        elif any(_number(m[1]) not in title_counts for m in _BODY_COUNT.finditer('\n'.join(lines[1:]))):
            issues.append('正文中提到的产品款数不一致，请核对导语和总结')
    return tuple(issues)


def prepare(markdown, category, *, reference='', strict=False, reviewed_count=None):
    revised = normalize(markdown)
    ranking = category in ('排行类', 'ranking')
    revised = _restore_rank_headings(revised, ranking)
    revised, footer_issues = _strip_source_footer(revised, reference)
    issues = _publication_issues(revised, ranking, reviewed_count) + footer_issues if strict else ()
    return revised, issues


def contract_issues(markdown, category):
    """Require actual product sections in new ranking drafts, even with an unnumbered title."""
    if category not in ('排行类', 'ranking'):
        return ()
    lines = markdown.splitlines()
    if not lines:
        return ()
    if any(_number(match[1] or match[2]) == 1 for match in _TITLE_COUNT.finditer(lines[0])):
        return ()
    product_headings = [line for line in lines if _HEADING.match(line)
                        and (_entry(_visible(line)) or _product_name(_visible(line)))]
    if len(product_headings) < 2:
        return ('榜单须逐款列出独立产品小标题',)
    return ()


def revision_path(folder):
    """Locate durable editorial data separately from generated export caches."""
    from . import runtime

    key = runtime.digest(str(folder.resolve()))
    return runtime.BASE / 'publication-revisions' / (key + '.json')


def editorial_revision(folder, markdown):
    from . import runtime

    record = runtime.read(revision_path(folder))
    if not isinstance(record, dict):
        return None
    if record.get('source_sha256') != hashlib.sha256(markdown.encode('utf-8')).hexdigest():
        return None
    revised = record.get('markdown')
    count = record.get('reviewed_count')
    if (not isinstance(revised, str) or not revised.startswith('# ')
            or record.get('revision_sha256') != hashlib.sha256(revised.encode('utf-8')).hexdigest()
            or (count is not None and (type(count) is not int or count < 1))):
        return None
    return record


def publication(folder, markdown):
    """Use the same reviewed text for catalog, single export and bulk export."""
    category = folder.parent.name
    revision = editorial_revision(folder, markdown)
    if revision:
        markdown = revision['markdown']
    reference = ''
    tail = [line for line in markdown.splitlines()[1:] if line.strip()][-12:]
    if any(_PLATFORM_NOTE.search(line) or _STAFF.fullmatch(_visible(line)) for line in tail):
        from . import runtime
        reference = (runtime.read(folder / 'rewrite_context.json').get('reference') or {}).get('text', '')
    if revision:
        revised, footer_issues = _strip_source_footer(markdown, reference or '')
        return revised, _publication_issues(revised, category in ('排行类', 'ranking'), revision.get('reviewed_count')) + footer_issues
    return prepare(markdown, category, reference=reference or '', strict=True)


def project(folder):
    """Prepare Markdown and Word together so both exports share the same structure."""
    from geo_source_cards.runtime import atomic_write, process_lock
    from geo_source_cards.word_export import export_docx

    from . import runtime

    original = {'word': folder / 'article.docx', 'markdown': folder / 'draft.md', 'image': None}
    markdown = original['markdown'].read_text('utf-8')
    revised, _ = publication(folder, markdown)
    if revised == markdown:
        return original
    key = runtime.digest([VERSION, str(folder), revised])
    output = runtime.BASE / 'illustrated' / key
    with process_lock(output.with_suffix('.lock'), blocking=True):
        word = output / 'article.docx'
        draft = output / 'draft.md'
        if not (draft.is_file() and word.is_file()):
            export_docx(revised, word)
            atomic_write(draft, revised)
    return {'word': word, 'markdown': draft, 'image': None}
