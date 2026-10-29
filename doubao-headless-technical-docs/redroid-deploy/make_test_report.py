import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root/'artifacts/first-three-store-results.json').read_text(encoding='utf-8'))
output = root/'test-results'
output.mkdir(exist_ok=True)
assert len(rows) == 3 and all(r['status'] == 'ok' and r['finished'] for r in rows)
assert all(s.get('url') and s.get('title') for r in rows for s in r['sources'])
(output/'answers.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
with (output/'answers.jsonl').open('w',encoding='utf-8') as file:
    for row in rows:
        file.write(json.dumps(row,ensure_ascii=False)+'\n')
with (output/'answers.csv').open('w',encoding='utf-8-sig',newline='') as file:
    writer = csv.DictWriter(file,fieldnames=['index','question','body_markdown','source_count','citation_count','sources','citations'])
    writer.writeheader()
    for row in rows:
        values = {key:row[key] for key in writer.fieldnames}
        values['sources'] = json.dumps(values['sources'],ensure_ascii=False)
        values['citations'] = json.dumps(values['citations'],ensure_ascii=False)
        writer.writerow(values)
with (output/'sources.csv').open('w',encoding='utf-8-sig',newline='') as file:
    writer = csv.DictWriter(file,fieldnames=['question_index','source_index','title','url','doc_id'])
    writer.writeheader()
    for row in rows:
        for source in row['sources']:
            writer.writerow({'question_index':row['index'],'source_index':source['index'],
                             'title':source['title'],'url':source['url'],'doc_id':source['doc_id']})
lines = ['# 无头模拟器测试结果（2026-10-06）','',
         '三题均由服务器上的 Android 15 Redroid 内豆包 App 发出并收到完整回答，测试时已关闭 scrcpy 投屏。',
         '直接读取模拟器中的聊天 SQLite 数据库（只读事务），提取原始 Markdown 正文、37 条信源记录和 15 处引用信息。重复信源保留原始编号。',
         '', '连续稳定运行未通过：App 后续出现 ARM 转译组件错误 `guest_params_arch.h:278: CHECK failed: 32080 <= 0`，并发生 SIGABRT。UI 也曾停在搜索状态，尽管答案已经写入数据库。',
         '这份结果证明数据可提取，不代表当前 x86 转译环境可以长期无人值守。测试没有停止或重启原有业务容器。',
         '', '## 字段说明', '', '`sources` 是搜索参考资料列表；`citations` 是正文实际引用，包含原始位置、标题、URL、doc_id。两者分别保存。',
         '正文中的时间、地址等内容是豆包原始输出，未在本测试中独立核验。', '']
for row in rows:
    lines.extend([f"## 第 {row['index']} 题",'',row['question'],'',row['body_markdown'],'',
                  f"参考资料：{row['source_count']} 条；正文引用：{row['citation_count']} 处。",''])
    for source in row['sources']:
        lines.append(f"- {source['index']}. [{source['title']}]({source['url']})")
    lines.append('')
(output/'report.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps([{'index':r['index'],'body_chars':len(r['body_markdown']),
                   'sources':r['source_count'],'citations':r['citation_count']} for r in rows]))
print('Saved:',output)
