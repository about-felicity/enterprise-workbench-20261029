import zipfile,re,json
from yuanbao_dex_class_utils import classes
names=set();terms=set()
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
    for file in z.namelist():
        if not file.endswith('.dex'):continue
        raw=z.read(file)
        names.update(c for c in classes(raw) if ('hunyuan' in c or 'dtmp' in c) and 'mpcommon/generated/biz/chat/bizmodel/' in c and '$' not in c and re.search(r'Content|Text|Reference|Citation|Search|Markdown|Detail|Meta|Message',c))
        for m in re.findall(rb'[A-Za-z][A-Za-z0-9_.:/]{4,160}',raw):
            s=m.decode()
            if re.search(r'(?:get|query|fetch|load|Get|Query|Fetch|Load)(?:Local)?(?:Chat)?(?:Message|Conversation|History)|(?:ChatMessage|ConversationDetail|MessageList)(?:Get|Query|Fetch|Load)',s):terms.add(s)
print(json.dumps({'classes':sorted(names)}))


