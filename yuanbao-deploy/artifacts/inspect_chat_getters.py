import zipfile,struct
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
targets={'Lcom/tencent/hunyuan/mpcommon/generated/biz/chat/bizmodel/T;':{'c','h','i','m'},'Lcom/tencent/hunyuan/mpcommon/generated/biz/chat/bizmodel/ChatBizModel$GetConversationMessagesResult;':{'toString'},'Lcom/tencent/hunyuan/mpcommon/generated/biz/chat/bizmodel/Message;':{'toString'},'Lcom/tencent/hunyuan/mpcommon/generated/biz/chat/bizmodel/Conversation;':{'toString'}}
def classes(b):
    ns,so=struct.unpack_from('<II',b,56);nt,to=struct.unpack_from('<II',b,64);nc,co=struct.unpack_from('<II',b,96)
    def string(i):
        p=struct.unpack_from('<I',b,so+4*i)[0]
        while b[p]&128:p+=1
        p+=1
        return b[p:b.index(0,p)].decode('utf8',errors='replace')
    return {string(struct.unpack_from('<I',b,to+4*struct.unpack_from('<I',b,co+32*i)[0])[0]) for i in range(nc)}
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
    for name in z.namelist():
        if not name.endswith('.dex'):continue
        raw=z.read(name)
        if not set(targets).intersection(classes(raw)):continue
        dex=DEX(raw)
        for c in dex.get_classes():
            if c.get_name() not in targets:continue
            print('CLASS',c.get_name(),'SUPER',c.get_superclassname(),'FLAGS',c.get_access_flags_string())
            for m in c.get_methods():
                if m.get_name() not in targets[c.get_name()]:continue
                print(m.get_name(),m.get_descriptor())
                for i in m.get_instructions():print(i.get_name(),i.get_output())

