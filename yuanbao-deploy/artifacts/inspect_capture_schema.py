import sys,json,os
sys.path.insert(0,'/tmp')
import yuanbao_native_storage as ns
for index,path in enumerate(ns.databases()):
    with ns.open_readonly(path) as db:
        print(json.dumps({'store':index,'tables':{table:[dict(r) for r in db.execute('pragma table_info("'+table+'")')] for table in [*ns.REQUIRED,'ChatConversations']},'counts':{t:db.execute('select count(*) from '+t).fetchone()[0] for t in ns.REQUIRED}}))
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
from pathlib import Path
base=Path('/home/user/redroid-yuanbao/diagnostics/native-capture-20261015');base.mkdir(mode=0o700,exist_ok=True)
(base/'logged-in-ui.xml').write_text(d.dump_hierarchy(),encoding='utf8')
print(json.dumps({'ui_saved':True,'current_activity':d.app_current().get('activity')}))
