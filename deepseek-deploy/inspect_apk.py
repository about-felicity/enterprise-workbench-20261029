"""Offline inspection of the official APK; never reads account data."""
import zipfile
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
path='/home/user/redroid-deepseek/artifacts/deepseek.apk'
with zipfile.ZipFile(path) as archive:
 for name in archive.namelist():
  if not name.endswith('.dex'):continue
  dex=DEX(archive.read(name))
  for cls in dex.get_classes():
   cname=cls.get_name()
   if 'deepseek' not in cname:continue
   matches=[]
   for method in cls.get_methods():
    code=method.get_code()
    if not code:continue
    instructions=list(code.get_bc().get_instructions())
    texts=[i.get_output() for i in instructions if i.get_name().startswith('const-string')]
    if any(any(k in t.lower() for k in ('create table','chat_session','chat_message','finish_reason','search_results','user_id','message_id','response_id','references','is_logged','access_token')) for t in texts):
     matches.append((method.get_name(),texts))
   if matches:print(cname,matches)
