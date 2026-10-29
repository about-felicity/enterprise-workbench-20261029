"""Inspect structural sync evidence without disclosing credentials/messages."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,sqlite3,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from active_database_accounts import current_uid
c='doubao-hpe14-account2';uid=current_uid(c)
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
repo=app/'files/keva/repo'
managers=[d.name.removeprefix('FlowIMSDKconversation-local-manager') for d in repo.glob('FlowIMSDKconversation-local-manager*')]
def walk(v,where):
    if isinstance(v,dict):
        ids={k:str(val) for k,val in v.items() if k.lower() in ('uid','user_id','userid','id') and not isinstance(val,(dict,list))}
        secs={k:str(val) for k,val in v.items() if k.lower() in ('sec_uid','sec_user_id','secuid')}
        if secs:print('identity_record',where,{'id_matches_current':any(i==uid for i in ids.values()),'id_keys':list(ids),'sec_cache_matches':[any(s==m for m in managers) for s in secs.values()]})
        for k,val in v.items():
            if not re.search('token|cookie|authorization|password|secret',k,re.I):walk(val,where+'/'+k)
    elif isinstance(v,list):
        for val in v:walk(val,where+'[]')
    elif isinstance(v,str) and v[:1] in ('{','['):
        try:walk(json.loads(v),where)
        except ValueError:pass
for p in (app/'shared_prefs').glob('*.xml'):
    try:
        for node in ET.parse(p).getroot():
            k=node.get('name','')
            if re.search('user|account|profile',k,re.I) and not re.search('token|cookie|auth',k,re.I): walk(node.text or '',p.name+'/'+k)
    except ET.ParseError:pass
db=sqlite3.connect((app/'databases'/('im_database_'+uid)).as_uri()+'?mode=ro',uri=True)
for table in ('im_conversation','im_project','im_bot','im_participant'):
    print('table',table,db.execute('select count(*) from '+table).fetchone()[0])
    print('columns',table,[r[1] for r in db.execute('pragma table_info('+table+')')])
tea=sqlite3.connect((app/'databases/482431@bd_tea_agent.db').as_uri()+'?mode=ro',uri=True)
for table in ('eventv3','forward_eventv3'):
    for event,params in tea.execute('select event,params from '+table+' order by _id desc limit 500'):
        if re.search('conversation|im_|message_send',event):
            v=json.loads(params or '{}')
            fields={k:val for k,val in v.items() if k in ('error_code','success','result','status','cmd','duration','command','http_status','error_msg') and isinstance(val,(int,float,bool,str))}
            print('telemetry',event,fields)
for d in repo.iterdir():
    if re.search('conversation-local-manager|CMD_',d.name):
        print('repo',re.sub('(?:MS4.*|[0-9]{8,})','[account]',d.name),'files',[(p.suffix,p.stat().st_size) for p in d.iterdir()])
        for p in d.glob('*.blk'):
            strings=[s.decode() for s in re.findall(rb'[ -~]{5,160}',p.read_bytes())]
            structural=[s for s in strings if re.search('cursor|sync|version|conversation|init|pull|check',s,re.I) and not re.search('token|auth|session|MS4|https?',s,re.I)]
            print('structural_strings',[re.sub(r'\d{8,}','[id]',s) for s in structural])
