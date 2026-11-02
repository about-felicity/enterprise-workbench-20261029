import subprocess
from pathlib import Path
b=Path('/home/user/redroid-doubao'); w=b/'expansion-20261102'
a=(b/'geo-batch-code/question_only_adapters.py').read_text()
pos=a.index('    if not any(',a.index('def assert_question_only_composer'))
a=a[:pos]+'''    lists=[n for n in nodes if n.get('resource-id')==prefix+'message_list']
    welcome='嗨，我是豆包，可以帮你解答问题，给你工作和学习提供帮助，也能陪你聊天。今天有什么可以帮你的吗？'
    if len(lists)==1 and len(lists[0])==2:
        greeting,suggestions=lists[0]
        if ([n.get('text') for n in greeting.iter() if n.get('text')]==[welcome]
            and any(n.get('class')=='android.widget.HorizontalScrollView' for n in suggestions.iter())
            and any(n.get('resource-id')==prefix+'mask_container' for n in suggestions.iter())
            and any(n.get('resource-id')==prefix+'larus_chat_top_left_create_new_cvs' and n.get('content-desc')=='创建新对话' for n in nodes)
            and any(n.get('resource-id')==prefix+'back_icon' and n.get('content-desc')=='对话列表' for n in nodes)
            and any(n.get('resource-id')==prefix+'input_text' and (not landing or n.get('text') in ('','发消息')) for n in nodes)
            and not any(n.get('resource-id','').startswith((prefix+'msg_action_',prefix+'md_')) or n.get('resource-id')==prefix+'side_bar_merged_main_title' for n in nodes)):
            return
'''+a[pos:]
(w/'expansion_adapters.py').write_text(a)
p=w/'question_only_worker.py';s=p.read_text().replace('from question_only_adapters import','from expansion_adapters import');p.write_text(s)
for n in (3,4):
 subprocess.run(['systemd-run','--unit',f'geo-expand-welcome{n}-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(b/'geo-batch-code'),str(b/'worker-venv/bin/python'),'-u',str(p),'--config',str(w/f'smoke{n}.json')],check=True)
