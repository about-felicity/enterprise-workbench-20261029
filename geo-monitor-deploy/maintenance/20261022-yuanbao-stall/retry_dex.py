import zipfile,sys,struct
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
def class_names(b):
 ns,so=struct.unpack_from('<II',b,56);nt,to=struct.unpack_from('<II',b,64);nc,co=struct.unpack_from('<II',b,96)
 def string(i):
  p=struct.unpack_from('<I',b,so+4*i)[0]
  while b[p]&128:p+=1
  p+=1
  return b[p:b.index(0,p)].decode('utf8',errors='replace')
 return {string(struct.unpack_from('<I',b,to+4*struct.unpack_from('<I',b,co+32*i)[0])[0]) for i in range(nc)}
targets={'Lcom/tencent/hunyuan/app/chat/biz/chats/conversation/base/viewholder/loading/ConversationNetworkLoadingVM;','LYl/f;','LYl/g;'}
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
 for name in z.namelist():
  if not name.endswith('.dex'):continue
  data=z.read(name)
  if not targets&set(class_names(data)):continue
  dex=DEX(data)
  for c in dex.get_classes():
   if c.get_name() not in targets:continue
   print('CLASS',c.get_name())
   for method in c.get_methods():
    print('METHOD',method.get_name(),method.get_descriptor())
    for ins in method.get_instructions():print(ins.get_name(),ins.get_output())
