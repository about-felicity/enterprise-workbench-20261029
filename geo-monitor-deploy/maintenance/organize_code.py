"""Prepare/review file classification; actual moves use native PowerShell."""
import ast
from collections import Counter,defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'geo-monitor-deploy/maintenance/20261015-reorganize'
AUDIT.mkdir(parents=True,exist_ok=True)
PLAN=AUDIT/'organization-plan.json'

def digest(data):return hashlib.sha256(data).hexdigest()
def relative(path):return path.relative_to(ROOT).as_posix()
def inbound(base):
    files={p.stem:p for p in base.glob('*.py')}; result=defaultdict(set)
    for p in files.values():
        try:tree=ast.parse(p.read_text('utf-8-sig'))
        except SyntaxError:continue
        for node in ast.walk(tree):
            names=([node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else
                [v.name.split('.')[0] for v in node.names] if isinstance(node,ast.Import) else [])
            for name in names:
                if name in files:result[name].add(p.name)
    return result

def category(path,project,refs):
    name=path.name
    if path.suffix=='.py':
        if name.startswith('test_') and name!='test_phase_recovery_live.py':return 'tests'
        protected={'remote.py','tunnel.py','unattended_core.py','unattended_worker.py','runtime_preflight.py',
            'geo_batch_bridge.py','maintenance_control.py','active_database_accounts.py','soak_sequence.py','soak_monitor.py',
            'capture_bridge.py','completion_guard.py','control_panel.py','fleet_status.py','login_probe.py','native_entry.py','native_soak.py','vps_geo_access.py'}
        text=path.read_text('utf-8-sig')
        if name in protected or refs[path.stem] or '__file__' in text:return None
        if name.startswith(('apply_','repair_','recover_','rebuild_','reset_','reconcile_','retry_','resume_','reload_','isolate_','mark_','fix_','migrate_','start_account','switch_')) or name in ('create_account2.py','clean_server_project.py','test_phase_recovery_live.py'):
            return 'archive/one_off'
        if name.startswith(('deploy_','build_','install_','fetch_','prepare_','backup_','transfer_')) or name in ('finalize.py',):return 'tools/deployment'
        if name.startswith(('export_','package_')):return 'tools/exports'
        if name=='start_native_soak.py':return 'tools/soak'
        return 'tools/diagnostics'
    if path.suffix=='.md' and name!='README.md':
        if project=='geo-monitor-deploy':
            return 'docs/guides' if name in ('CONTROL_PANEL_GUIDE.md','DASHBOARD_INTEGRATION_20261015.md','VPS_GEO_ACCESS_20261015.md') else 'docs/reports'
        return 'docs/operations' if name in ('ACCOUNT2.md','HPE14_FIX.md','UNATTENDED.md','PROJECT_GUIDE.md','PROJECT_TREE.md') else 'docs/history'
    if project=='geo-monitor-deploy' and path.suffix in ('.json','.jsonl','.png'):return 'reports/20261015'
    if path.suffix=='.zip' or name.endswith(('.tar.gz','.tgz')):return 'releases/20261015' if project=='geo-monitor-deploy' else 'releases/history'
    return None

def prepare():
    assert not (AUDIT/'organization-applied.json').exists(),'Organization already applied'
    moves=[];catalog=[]
    for project in ('geo-monitor-deploy','redroid-deploy'):
        base=ROOT/project;refs=inbound(base)
        for path in sorted(base.iterdir()):
            if not path.is_file():continue
            group=category(path,project,refs)
            target=base/group/path.name if group else path
            row={'source':relative(path),'target':relative(target),'sha256':digest(path.read_bytes()),'category':group or 'stable-entrypoint-or-configuration'}
            catalog.append(row)
            if group:
                assert not target.exists()
                moves.append(row)
    data={'root':str(ROOT),'moves':moves,'catalog':catalog}
    PLAN.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    with zipfile.ZipFile(AUDIT/'before-organization.zip','w',zipfile.ZIP_DEFLATED) as z:
        for row in catalog:z.write(ROOT/row['source'],row['source'])
        for p in (ROOT/'README.md',ROOT/'PROJECT_HANDOFF.md'):z.write(p,relative(p))
    print(json.dumps({'moves':len(moves),'categories':dict(Counter(r['category'] for r in moves)),'plan':str(PLAN)},ensure_ascii=True))

def patch():
    plan=json.loads(PLAN.read_text('utf8'))
    mapping={(ROOT/r['source']).resolve():(ROOT/r['target']).resolve() for r in plan['moves']}
    for row in plan['moves']:
        path=ROOT/row['target']
        assert path.exists() and digest(path.read_bytes())==row['sha256']
        if path.suffix!='.py':continue
        text=path.read_text('utf-8-sig')
        if 'from __future__' in text:
            tree=ast.parse(text);line=max(n.end_lineno for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=='__future__')
        else:
            tree=ast.parse(text);line=tree.body[0].end_lineno if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str) else 0
        depth=len(path.relative_to(ROOT/row['source'].split('/')[0]).parts)-1
        boot=f'\n# Stable runtime imports after tool/test classification.\nimport sys as _geo_sys\nfrom pathlib import Path as _GeoPath\n_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[{depth}]\n_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))\n'
        lines=text.splitlines(keepends=True);text=''.join(lines[:line])+boot+''.join(lines[line:])
        if path.name=='test_capture_bridge.py':text=text.replace('parents[1] / "geo-source-card-collectors"','parents[2] / "geo-source-card-collectors"')
        if path.name=='test_unattended.py':text=text.replace('cwd=Path(__file__).parent','cwd=_GEO_TOOL_ROOT')
        ast.parse(text)
        path.write_text(text,encoding='utf8')
    # Rewrite only resolved local Markdown links, including links from files
    # that themselves moved. Historical shell commands remain dated evidence.
    reverse={new:old for old,new in mapping.items()}
    documents=[ROOT/'README.md',ROOT/'PROJECT_HANDOFF.md']
    documents += list((ROOT/'geo-monitor-deploy').rglob('*.md'))
    documents += list((ROOT/'redroid-deploy').rglob('*.md'))
    for path in documents:
        before=path.read_text('utf-8-sig');old=reverse.get(path.resolve(),path.resolve())
        def replace(match):
            target=match.group(2)
            if '://' in target or target.startswith('#'):return match.group(0)
            raw,sep,fragment=target.partition('#')
            resolved=(old.parent/raw).resolve()
            actual=mapping.get(resolved,resolved)
            # Unmoved links in moved documents still need a new relative base.
            if resolved not in mapping and old==path.resolve():return match.group(0)
            updated=os.path.relpath(actual,path.parent).replace('\\','/')
            return match.group(1)+updated+(sep+fragment if sep else '')+match.group(3)
        after=re.sub(r'(!?\[[^\]]*\]\()([^\n)]+)(\))',replace,before)
        if after!=before:path.write_text(after,encoding='utf8')
    for project in ('geo-monitor-deploy','redroid-deploy'):
        tests=ROOT/project/'tests';tests.mkdir(exist_ok=True)
        (tests/'__init__.py').write_text('"""Project regression tests."""\n',encoding='utf8')
        rows=[r for r in plan['catalog'] if r['source'].startswith(project+'/')]
        note='# 代码与文件分类\n\n正式运行入口与配置保持原路径。测试、维护工具、一次性历史修复、文档、报告和发布包已分目录。`archive/one_off`是历史现场脚本，不能当常规重启或通用恢复命令运行。\n\n'
        note+='| 分类 | 文件数 |\n|---|---:|\n'+''.join(f'| {k} | {v} |\n' for k,v in Counter(r['category'] for r in rows).items())
        note+='\n| 原位置 | 当前路径 |\n|---|---|\n'+''.join(f"| `{r['source'].split('/',1)[1]}` | [{r['target'].split('/',1)[1]}]({r['target'].split('/',1)[1]}) |\n" for r in rows)
        (ROOT/project/'CODE_LAYOUT.md').write_text(note,encoding='utf8')
    applied={'moves':len(plan['moves']),'source_backup':'before-organization.zip',
        'files':[{'source':r['source'],'target':r['target'],'before_sha256':r['sha256'],'after_sha256':digest((ROOT/r['target']).read_bytes())} for r in plan['moves']]}
    (AUDIT/'organization-applied.json').write_text(json.dumps(applied,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'organized_files':len(plan['moves']),'syntax_checked':sum(r['target'].endswith('.py') for r in plan['moves'])}))

if __name__=='__main__':
    {'prepare':prepare,'patch':patch}[sys.argv[1]]()
