"""Attach independent, topic-matched reading to Markdown and Word deliveries."""

import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from geo_source_cards.runtime import atomic_write, process_lock

from . import runtime


HEADING = re.compile(r'(?:#{1,6}\s+)?(?:参考信源|参考资料|参考链接|参考文献|参考来源)\s*[:：]?')
LIBRARY = Path(__file__).with_name('reference_library.json')
LOG = logging.getLogger(__name__)


def _url_key(url):
    if not isinstance(url, str) or re.search(r'[\s<>"\\\x00-\x1f]', url):
        return None
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme not in ('http', 'https') or not host or '.' not in host or parts.username is not None:
        return None
    query = tuple(sorted((name, value) for name, value in parse_qsl(parts.query, keep_blank_values=True)
                         if not name.casefold().startswith('utm_')))
    return host.removeprefix('www.'), parts.path.rstrip('/'), query


def _footer_index(lines):
    for index in range(len(lines) - 1, 0, -1):
        line = lines[index].strip()
        if HEADING.fullmatch(line):
            return index
        if re.match(r'^#{1,6}\s', line):
            break
    return None


def topic_references(folder, markdown):
    primary = runtime.read(folder / 'provenance.json').get('primary_reference') or {}
    context = runtime.read(folder / 'rewrite_context.json').get('reference') or {}
    seen = {_url_key(primary.get('primary_url')), _url_key(context.get('url')), None}
    lines = markdown.splitlines()
    content = lines[:_footer_index(lines)]
    title = next((line.casefold() for line in content if line.strip()), '')
    headings = '\n'.join(line for line in content if line.startswith('##')).casefold()
    body = '\n'.join(content).casefold()
    ranked = []
    for item in runtime.read(LIBRARY, []):
        url, label = item['url'], item['label']
        key = _url_key(url)
        if key in seen:
            continue
        groups = [[term.casefold() for term in group] for group in item['topics']]
        scores = [max((6 if term in title else 4 if term in headings else min(body.count(term), 3)
                       for term in group), default=0) for group in groups]
        if scores and all(scores) and max(scores) >= 2:
            seen.add(key)
            # Keep sources about an explicit ingredient ahead of generic care tips.
            ingredient_bonus = 4 if item.get('kind') == 'ingredient' else 0
            ranked.append((sum(scores) / len(scores) + ingredient_bonus, len(groups), url, label))
    ranked.sort(key=lambda row: row[:2], reverse=True)
    return tuple((url, label) for _, _, url, label in ranked[:3])


def prepare_footer(markdown, references):
    lines = markdown.rstrip().splitlines()
    index = _footer_index(lines)
    footer = '\n'.join(lines[index + 1:]) if index is not None else None
    existing_urls = {_url_key(url.rstrip(').,。')) for url in re.findall(r'https?://[^\s<>\]]+', footer or '')}
    numbers = re.findall(r'(?m)^[ \t]*(?:\[(\d+)\]|(\d+)\.)', footer or '')
    start = 1 + max((int(bracketed or dotted) for bracketed, dotted in numbers), default=0)
    entries = tuple((number, url, label) for number, (url, label) in enumerate(
        ((url, label) for url, label in references if _url_key(url) not in existing_urls), start))
    if not entries:
        return markdown, (), False
    heading = footer is None
    items = []
    for number, url, label in entries:
        label = re.sub(r'([\\\[\]<>*_`])', r'\\\1', label)
        items.append(f'{number}. {label}  \n   <{url}>')
    prefix = '## 参考信源\n\n' if heading else ''
    return markdown.rstrip() + '\n\n' + prefix + '\n\n'.join(items) + '\n', entries, heading


def append_word(document, entries, heading):
    from docx.opc.constants import RELATIONSHIP_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    if heading:
        document.add_heading('参考信源', level=1)
    for number, url, label in entries:
        paragraph = document.add_paragraph(f'{number}. {label}')
        paragraph.paragraph_format.left_indent = Pt(24)
        paragraph.paragraph_format.first_line_indent = Pt(-24)
        paragraph.paragraph_format.keep_together = True
        paragraph.add_run().add_break()
        hyperlink = OxmlElement('w:hyperlink')
        hyperlink.set(qn('r:id'), paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
        run = paragraph.add_run(url)
        run.underline = True
        run.font.color.rgb = RGBColor(37, 99, 235)
        hyperlink.append(run._r)
        paragraph._p.append(hyperlink)


def project(folder, original):
    source = original['markdown'].read_text('utf-8')
    references = topic_references(folder, source)
    if not references:
        return original
    markdown, entries, heading = prepare_footer(source, references)
    if not entries:
        return original

    from docx import Document

    key = runtime.digest(['article-reference-links-v3', str(folder), markdown,
                          hashlib.sha256(original['word'].read_bytes()).hexdigest()])
    output = runtime.BASE / 'illustrated' / key
    word, draft = output / 'article.docx', output / 'draft.md'
    with process_lock(output.with_suffix('.lock'), blocking=True):
        if not (word.is_file() and draft.is_file()):
            document = Document(original['word'])
            append_word(document, entries, heading)
            output.mkdir(parents=True, exist_ok=True)
            staged = output / 'pending.docx'
            document.save(staged)
            staged.replace(word)
            atomic_write(draft, markdown)
    return {**original, 'word': word, 'markdown': draft,
            'product_export_record': original.get('product_export_record', original['word'].parent / 'complete.json')}


def prepare_created(root, day, started_at_ns):
    """Build the referenced edition as soon as a new article is accepted."""
    from .article_format import project as format_article

    for receipt in (root / 'approved' / day).glob('*/*/receipt.json'):
        try:
            if receipt.stat().st_mtime_ns < started_at_ns:
                continue
            if runtime.read(receipt).get('status') == 'accepted_for_user_review':
                project(receipt.parent, format_article(receipt.parent))
        except Exception as error:
            # Preview and download can regenerate this local edition from the accepted files.
            LOG.warning('Article reference preparation failed for %s: %s', receipt.parent.name, type(error).__name__)
