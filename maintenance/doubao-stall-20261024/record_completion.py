from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
v=json.loads((D/'verification.json').read_text('utf8'));c=v['current']
text=f'''

## 2026-10-24 豆包1第53题停滞已修复

现场为原题草稿末尾多一个换行、三个原生数据库无新增请求，旧精确匹配恢复器持续等待。新增发送前键盘关闭/三次布局稳定检查；仅在两次完整数据库无发送证据且无用户暂停时，限一次去掉单个尾部换行并提交原草稿。37项回归及真实现场回放通过。第53题572字/16信源已processed且PG正文一致、原生会话仅1条用户提问；最新实测豆包1已捕获{c['captured']}/105、入库{c['geo_processed']}/105，原批次继续。豆包2已105/105未动。未清队列、未重启App/容器；整批及跨日尚未重新验收。源码恢复映射234项。详见 maintenance/doubao-stall-20261024/REPORT.md 与 verification.json。
'''
for name in ['PROJECT_STATUS.md','CURRENT_PROJECT_HANDOFF.md','SOURCE_CONTROL.md']:
 p=R/name;raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';p.write_bytes(raw+text.replace('\n',nl).encode('utf8'))
