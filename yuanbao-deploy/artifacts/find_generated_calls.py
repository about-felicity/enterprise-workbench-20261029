import zipfile,json
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
need=['ChatBizModel$GetConversationMessagesArgs','ChatBizModel$GetMessageContentArgs','ChatBizModel$GetConversationInfoArgs']
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
    for name in z.namelist():
        if not name.endswith('.dex'):continue
        raw=z.read(name)
        if not any(n.encode() in raw for n in need):continue
        dex=DEX(raw)
        for c in dex.get_classes():
            for m in c.get_methods():
                code=m.get_code()
                if not code:continue
                lines=[(i.get_name(),i.get_output()) for i in m.get_instructions()]
                if any('invoke-direct' in op and any(n+';-><init>' in out for n in need) for op,out in lines):
                    print(json.dumps({'class':c.get_name(),'method':m.get_name(),'signature':m.get_descriptor(),'code':lines}))
