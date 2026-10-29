"""Validate task identity, native EOF, entity coverage and every source."""
import json
import re
from urllib.parse import urlsplit


class NativeDataError(RuntimeError):
    pass


def enum(value):
    return value.get('text') if isinstance(value, dict) else value


def text_entities(entities):
    return [e['textEntity']['text'] for e in entities if enum(e.get('type')) == 'TEXT']


def video_only_answer(task,binding,native,body,parts):
    """A finished video answer is an observation, not missing text in transit.

    Never invent a transcript, a website citation or a replacement question.
    The entire App-owned card and original request remain available for audit.
    """
    pattern=re.compile(r'!\[@replace_videoBoxV2&([^\]]+)\]\(https://yuanbao\)')
    markers=list(pattern.finditer(body))
    if not markers or pattern.sub('',body).strip():return None
    render=native.get('render_snapshot',{})
    context=render.get('h',{})
    if not native.get('render_snapshot_final'):return {'status':'pending','phase':'awaiting_complete_snapshot','reason':'final_video_card_pending','native_request_confirmed':True,'request_id':native['content']['traceId']}
    if context.get('conversationId')!=binding['conversation_id'] or context.get('msgId')!=binding['server_answer_id']:
        raise NativeDataError('Video card belongs to another native request')
    values=render.get('i',{}).get('replacesJson',[])
    if not isinstance(values,list):raise NativeDataError('Unsupported native replacement schema')
    try:cards=[json.loads(v) if isinstance(v,str) else v for v in values]
    except (ValueError,TypeError) as error:raise NativeDataError('Malformed native video card') from error
    selected=[]
    for marker in markers:
        matches=[c for c in cards if isinstance(c,dict) and c.get('display') in {'videoBoxV2','videoBoxStream'}
                 and isinstance(c.get('id'),str) and c['id'] and (marker[1]==c['id'] or marker[1].endswith('_'+c['id']))]
        if not matches or len({c['id'] for c in matches})!=1:return {'status':'pending','phase':'awaiting_complete_snapshot','reason':'native_video_card_pending','native_request_confirmed':True,'request_id':native['content']['traceId']}
        # One placeholder can own a main card plus a streamed related-video
        # carousel under the same native ID. Preserve both, including every
        # carousel item, rather than retaining only the first cover card.
        for card in matches:
            media=card.get('multimedias')
            if not isinstance(media,list) or not media:return {'status':'pending','phase':'awaiting_complete_snapshot','reason':'native_video_card_pending','native_request_confirmed':True,'request_id':native['content']['traceId']}
            for item in media:
                if not isinstance(item,dict) or item.get('type') not in {'videoBoxV2','videoBoxStream'} or not item.get('mediaId') or not str(item.get('title','')).strip():
                    raise NativeDataError('Incomplete or unsupported native video metadata')
                # Preserve App-provided asset/player metadata, never synthesize
                # WeChat URLs or treat a thumbnail as an article.
                parsed=urlsplit(item.get('resourceUrl',''))
                if parsed.scheme not in ('https','http') or not parsed.hostname:
                    raise NativeDataError('Native video asset reference is missing')
            if card not in selected:selected.append(card)
    if len(selected)!=len(cards):raise NativeDataError('Unaccounted native replacement card')
    return {'status':'nontext_complete','availability':'nontext_answer','native_answer_kind':'video_only',
        'reason':'native_video_only_answer','finished':True,'native_request_confirmed':True,
        'task_id':task['task_id'],'wire_question':task['wire_question'],
        'conversation_id':binding['conversation_id'],'request_id':native['content']['traceId'],
        'answer_id':native['message']['serverId'],'question_id':native['question']['serverId'],
        'body_markdown':body,'body_parts':parts,'text_body_present':False,
        'body_capture_complete':False,'source_capture_complete':False,
        'sources':[],'citations':[],'raw_source_entries':[],
        'rich_media_capture_complete':True,'rich_cards':selected,
        'native_snapshot':native,'capture_mode':'android_app_dtmp_native',
        'search_queries':[],'search_queries_exposed':False}


def parse_result(task, binding, native):
    message, content = native['message'], native['content']
    question, conversation = native['question'], native['conversation']
    if not message.get('id'):
        return {'status':'awaiting_native_history'}
    if (message.get('serverId') != binding['server_answer_id']
            or question.get('id') != message.get('pairId')
            or question.get('serverId') != message.get('serverPairId')):
        raise NativeDataError('Native request/answer pair changed')
    request_text = '\n\n'.join(text_entities(native['question_entities']))
    if request_text != task['wire_question']:
        raise NativeDataError('Native question differs from durable task')
    if enum(question.get('speaker')) != 'HUMAN' or enum(message.get('speaker')) != 'AI':
        raise NativeDataError('Unexpected native speaker pair')
    if int(message['contentCount']) != 1:
        raise NativeDataError('Multiple answer variants require explicit extraction')
    if (enum(message.get('state')) == 'INTERRUPTED' and enum(content.get('state')) == 'INTERRUPTED'
            and not conversation.get('isBusy') and content.get('traceId')):
        return {'status':'pending','phase':'awaiting_original_history','reason':'native_answer_interrupted',
                'request_id':content['traceId'],'native_request_confirmed':True}
    if enum(message.get('state')) != 'COMPLETED' or enum(content.get('state')) != 'COMPLETED' or not content.get('isEof') or conversation.get('isBusy'):
        return {'status':'pending','request_id':content.get('traceId'),'native_request_confirmed':True}
    def hydrating(reason):
        # DTMP metadata/entities are separate reads. EOF may become visible
        # before the related source/entity rows. Re-read this same request;
        # the worker's original 900s deadline still applies, with no resend.
        return {'status':'pending','phase':'awaiting_complete_snapshot','reason':reason,
                'request_id':content.get('traceId'),'native_request_confirmed':True}
    entities = native['entities']
    if len(entities) != int(content['entityCount']):
        return hydrating('native_entity_count_pending')
    allowed = {'TEXT','SEARCH_GUIDE','HINT','THINK','STEP','CONTINUE_STEP'}
    if any(enum(e.get('type')) not in allowed for e in entities):
        raise NativeDataError('Unsupported active answer entity; completeness unproven')
    parts = text_entities(entities)
    body = '\n\n'.join(parts)
    if not body.strip() or not content.get('traceId') or not content.get('contentId'):
        raise NativeDataError('Missing complete body or native identity')
    sources, raw_docs, headers, declared_counts = [], [], [], []
    for entity in entities:
        if enum(entity['type']) != 'SEARCH_GUIDE':continue
        search = entity['searchEntity']
        try:docs = json.loads(search['docsJson'])
        except (ValueError,TypeError) as error:raise NativeDataError('Malformed native source JSON') from error
        if not isinstance(docs,list):raise NativeDataError('Native source JSON is not an array')
        if len(docs) != len(search['docs']):
            return hydrating('native_source_count_pending')
        title_count = re.search(r'引用\s*(\d+)\s*篇', search['title'])
        if title_count and int(title_count[1]) != len(docs):
            return hydrating('displayed_source_count_pending')
        declared_counts.append(len(search['docs']))
        headers.append(search['title'])
        for doc in docs:
            url = urlsplit(doc.get('url') or '')
            if url.scheme not in ('http','https') or not url.netloc or not doc.get('docId'):
                raise NativeDataError('Incomplete source metadata')
            original_title=doc.get('title')
            missing_title=not isinstance(original_title,str) or not original_title.strip()
            # This is an explicit display label, never a fabricated article
            # title. Keep the original doc unchanged in both audit collections.
            label='未提供标题（'+str(doc.get('web_site_name') or doc.get('webSiteSource') or url.hostname)+'）'
            sources.append({'title':label if missing_title else original_title,'url':doc['url'],'doc_id':doc['docId'],
                            **({'title_missing':True,'original_title':original_title,'title_origin':'explicit_missing_title_label'} if missing_title else {}),
                            'index':doc['index'],'quote':doc.get('quote',''),'native_source':doc})
            raw_docs.append(doc)
    if not sources:
        video=video_only_answer(task,binding,native,body,parts)
        if video is not None:return video
        if body.strip()=='回答拉取失败，正在重试' and message.get('serverId','').startswith('local_'):
            return hydrating('native_answer_fetch_failed')
        return hydrating('required_sources_pending')
    indices = {int(source['index']):source for source in sources}
    if len(indices) != len(sources):
        raise NativeDataError('Ambiguous native source indices')
    citations = []
    for marker in re.finditer(r'\[citation:(\d+)\]',body):
        index = int(marker[1])
        if index not in indices:return hydrating('citation_source_pending')
        source = indices[index]
        citations.append({'index':index,'doc_id':source['doc_id'],'url':source['url'],
                          'title':source['title'],'offset':marker.start(),'marker':marker[0]})
    return {'status':'complete','finished':True,'task_id':task['task_id'],'wire_question':task['wire_question'],
            'conversation_id':binding['conversation_id'],'request_id':content['traceId'],
            'answer_id':message['serverId'],'question_id':question['serverId'],
            'body_markdown':body,'body_parts':parts,'sources':sources,'citations':citations,
            'search_queries':[],'search_queries_exposed':False,
            'expected_source_count':sum(declared_counts),'source_headers':headers,
            'native_request_confirmed':True,'body_capture_complete':True,'source_capture_complete':True,
            'native_snapshot':native,'raw_source_entries':raw_docs,
            'capture_mode':'android_app_dtmp_native'}
