"""Inspect fixed official APK model layouts, without interacting with the App."""
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
import zipfile
with zipfile.ZipFile('/home/user/redroid-deepseek/artifacts/deepseek.apk') as z:
 for name in z.namelist():
  if not name.endswith('.dex'):continue
  d=DEX(z.read(name))
  for c in d.get_classes():
   selected=[]
   for m in c.get_methods():
    if not m.get_code():continue
    ins=list(m.get_code().get_bc().get_instructions())
    strings=' '.join(i.get_output() for i in ins if i.get_name().startswith('const-string'))
    if any(x in strings for x in ['CREATE TABLE app_user','chat_session_messages_','chat_session_list','SearchResult','ChatMessageFragment','AppStaticMessage','ChatSessionMessageTable','ChatMessageSearch']):selected.append(m)
   if not selected:continue
   print('\nCLASS',c.get_name(),'FIELDS',[(f.get_name(),f.get_descriptor()) for f in c.get_fields()])
   for m in c.get_methods():
    if not m.get_code():continue
    if m in selected or c.get_name() in ['Labb;','Lqb1;','Lgec;']:
     print('METHOD',m.get_name(),m.get_descriptor())
     for i in m.get_code().get_bc().get_instructions():print(i.get_name(),i.get_output())
