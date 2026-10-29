"""Local fingerprints of the actual review sources, mappings and contracts."""
import json,re
from pathlib import Path
from .argument_plan import digest

VERSION='review-inputs-v2'
FILES=('writer_done.json','compilation.json','article_structure.json','claim_map.json',
       'knowledge_to_sections.json','evidence_matrix.json','claim_ledger.json',
       'reasoning_outline.json','writing_job.json','paragraph_repair.json')

def writer_for(location):
    location=Path(location);writer=location
    if writer.parent.name=='runs' and writer.parent.parent.name=='api':
        owner=writer.parents[2];active=owner/'api/active.json'
        if active.exists():
            state=json.loads(active.read_text('utf8'));ticket=owner/'queue'/state.get('ticket','')/'ticket.json'
            if state.get('run_id')==writer.name and ticket.is_file():writer=owner/json.loads(ticket.read_text('utf8'))['location']
    if writer.name=='review':writer=writer.parent/'writer'
    return writer

def snapshot(location,*,text=None,knowledge=None,product=None):
    from .staged_editorial import research_for_writer
    from .consumer_prompts import evidence_units
    location=Path(location);writer=writer_for(location);research=research_for_writer(writer)
    def load(path):return json.loads(path.read_text('utf-8-sig')) if path.is_file() else None
    def effective(name):
        local=location/name
        return load(local if local.is_file() else writer/name)
    text=(location/'draft.md').read_text('utf-8-sig') if text is None else text
    knowledge=effective('knowledge.json') if knowledge is None else knowledge
    product=effective('product.json') if product is None else product
    # C-spans are deterministic from text and are not transported to final
    # delivery. Verify a stored map against that derivation rather than ignoring it.
    spans={}
    for i,m in enumerate(re.finditer(r'[^\n。！？]+[。！？]?',text),1):
        if not m.group().strip():continue
        line=text[text.rfind('\n',0,m.start())+1:text.find('\n',m.start()) if '\n' in text[m.start():] else len(text)]
        if not line.lstrip().startswith('#'):spans[f'C{i}']=m.group()
    if (location/'claim_spans.json').exists() and load(location/'claim_spans.json')!=spans:
        raise ValueError('Stale review source mapping: claim spans differ from current text')
    return {'version':VERSION,'text':text,'knowledge':knowledge,'product':product,
        'contracts_and_maps':{n:effective(n) for n in FILES},'claim_spans':spans,
        'writer_records':{n:load(writer/n) for n in ('knowledge.json','product.json',*FILES)},
        'research_input':load(research/'research_input.json'),'research_result':load(research/'research_result.json'),
        'research_evidence_map':load(research/'evidence_spans.json'),
        'effective_original_units':evidence_units(location)}

def fingerprint(location,**kwargs):return digest(snapshot(location,**kwargs))
