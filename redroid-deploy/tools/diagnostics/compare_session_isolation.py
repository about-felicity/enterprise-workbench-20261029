"""Compare session fingerprints locally; never print credentials or hashes."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,sqlite3,hashlib,re,xml.etree.ElementTree as ET
from pathlib import Path
from active_database_accounts import current_uid
accounts=[]
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    uid=current_uid(name)
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
    c=sqlite3.connect((app/'databases/account_db').resolve().as_uri()+'?mode=ro',uri=True)
    values={}
    def scan(value,prefix):
        if isinstance(value,dict):
            for key,item in value.items():
                if re.search(r'session|token|ticket',key,re.I) and isinstance(item,str) and item:
                    values[prefix+'.'+key]=hashlib.sha256(item.encode()).digest()
                elif isinstance(item,(dict,list)):scan(item,prefix+'.'+key)
        elif isinstance(value,list):
            for item in value:scan(item,prefix)
    rows=c.execute('select info,ext from login_info where cast(uid as text)=?',(uid,)).fetchall()
    for row in rows:
        for raw in row:
            try:
                value=json.loads(raw or '{}')
                print('login_json_keys',list(value) if isinstance(value,dict) else type(value).__name__)
                scan(value,'active_login')
            except ValueError:pass
    cookies={}
    p=app/'shared_prefs/cookieStore.xml'
    print('cookie_storage_keys',[(node.get('name','')[:100],len(node.text or '')) for node in ET.parse(p).getroot()][:12])
    for node in ET.parse(p).getroot():
        key=node.get('name','')
        if 'session' in key.lower() and node.text:
            cookies[key]=hashlib.sha256(node.text.encode()).digest()
    for filename in ('token_shared_preference.xml','com_ss_android_token_sp_host.xml','last_sp_session.xml'):
        p=app/'shared_prefs'/filename
        if not p.exists():continue
        for node in ET.parse(p).getroot():
            key=node.get('name','')
            if node.text and re.search('session|token',key,re.I):
                values[filename+'.'+key]=hashlib.sha256(node.text.encode()).digest()
    print('im_pref_files',[str(p.relative_to(app/'files')) for p in (app/'files/keva').rglob('*') if p.is_file() and re.search('im_|im-sdk|im_sdk|conversation|omni',p.name,re.I)][:80])
    accounts.append((values,cookies))
    print(json.dumps({'container':name,'active_uid_masked':'***'+uid[-6:],'login_rows':len(rows),'session_field_names':list(values),'session_cookie_count':len(cookies)}))
common=set(accounts[0][0]) & set(accounts[1][0])
print(json.dumps({'compared_session_fields':{k:('same' if accounts[0][0][k]==accounts[1][0][k] else 'different') for k in common},'matching_session_cookie_values':len(set(accounts[0][1].values()) & set(accounts[1][1].values()))}))
