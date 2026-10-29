"""The supported JSON-Schema subset for Evidence/Claim/Section/Issue/Repair.

Export SCHEMAS for external tooling. Runtime validates these same definitions;
cross-object provenance, semantics and hashes have additional explicit gates.
"""
SCHEMAS={
 'Evidence':{'type':'object','required':['id','source_id','text','subjects','statement_type','verification','dimensions','source_kind','source_refs'],
  'properties':{'id':{'type':'string'},'source_id':{'type':'string'},'text':{'type':'string'},'subjects':{'type':'array','items':{'type':'string'}},
   'statement_type':{'enum':['product_fact','comparative_fact','general_advice','inference','opinion','transition']},
   'verification':{'type':'string'},'dimensions':{'type':'array','items':{'type':'string'}},'source_kind':{'enum':['supplier','retrieved_source']},'source_refs':{'type':'array'}}},
 'Claim':{'type':'object','required':['id','text','statement_type','evidence_ids','source_ids','subjects','allowed','reasoning'],
  'properties':{'id':{'type':'string'},'text':{'type':'string'},'statement_type':{'type':'string'},'allowed':{'enum':[True]},
   'evidence_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'source_ids':{'type':'array','minItems':1,'items':{'type':'string'}},
   'subjects':{'type':'array','items':{'type':'string'}},'reasoning':{'type':'object','required':['operation','premises','scope']}}},
 'Section':{'type':'object','required':['id','topic','role','claim_ids','evidence_ids','reasoning','depends_on_claims','reads_previous_section'],
  'properties':{'id':{'type':'string'},'topic':{'type':'string'},'role':{'type':'string'},'claim_ids':{'type':'array','items':{'type':'string'}},
   'evidence_ids':{'type':'array','items':{'type':'string'}},'reasoning':{'type':'object','required':['premises','operation','conclusion_scope']},
   'depends_on_claims':{'type':'array','items':{'type':'string'}},'reads_previous_section':{'type':['string','null']}}},
 'Issue':{'type':'object','required':['issue_id','type','severity','text','paragraph_ids','reason','origin','repair_scope','affected_sections'],
  'properties':{'issue_id':{'type':'string'},'type':{'type':'string'},'severity':{'enum':['major','minor']},'text':{'type':'array','items':{'type':'string'}},
    'paragraph_ids':{'type':'array','minItems':1,'items':{'type':'string'}},'reason':{'type':'string'},'origin':{'enum':['deterministic','fact_review','logic_review','arbitration']},
   'repair_scope':{'enum':['sentence','paragraph','section','multi-section','outline','replan']},'affected_sections':{'type':'array','items':{'type':'string'}}}},
 'Repair':{'type':'object','required':['version','draft_sha256','evidence_sha256','action','editable_ids','issues','unresolved_review','attempts','max_repairs','review_verdict_overridden'],
  'properties':{'version':{'type':'string'},'draft_sha256':{'type':'string'},'evidence_sha256':{'type':'string'},
   'action':{'enum':['PATCH','REWRITE','REPLAN','NEED_MORE_EVIDENCE','REVIEW_DISPUTED','REPAIR_EXHAUSTED']},
   'editable_ids':{'type':'array','items':{'type':'string'}},'issues':{'type':'array'},'unresolved_review':{'type':'array'},
   'attempts':{'type':'integer'},'max_repairs':{'enum':[2]},'review_verdict_overridden':{'enum':[False]}}}}


def validate_record(kind,value):
    def walk(schema,item,path):
        types=schema.get('type',[]);types=[types] if isinstance(types,str) else types
        matches={'object':isinstance(item,dict),'array':isinstance(item,list),'string':isinstance(item,str) and bool(item.strip()),
                 'integer':type(item) is int and item>=0,'null':item is None}
        if types and not any(matches.get(t,False) for t in types):raise ValueError('Invalid '+path+' type')
        if 'enum' in schema and not any(type(item) is type(v) and item==v for v in schema['enum']):raise ValueError('Invalid '+path+' value')
        if isinstance(item,dict):
            if not set(schema.get('required',[]))<=item.keys():raise ValueError('Missing '+path+' fields')
            for key,sub in schema.get('properties',{}).items():
                if key in item:walk(sub,item[key],path+'.'+key)
        if isinstance(item,list):
            if len(item)<schema.get('minItems',0):raise ValueError('Empty '+path)
            if 'items' in schema:
                for i,child in enumerate(item):walk(schema['items'],child,path+f'[{i}]')
    walk(SCHEMAS[kind],value,kind)
    return value
