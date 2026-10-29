import json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);ws=Path(__file__).resolve().parents[3]
helper=ws/'outputs/api-editorial/diagnostics/render_word_pages.py'
env={**os.environ,'PYTHONIOENCODING':'utf-8'}
poppler=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
env['PATH']=str(poppler)+os.pathsep+env['PATH']
rows=json.loads((root/'manifest.json').read_text('utf8'));report=[]
for row in rows:
 out=root/'pages'/row['key'];done=out/'render-complete.json'
 if not done.exists():
  out.mkdir(parents=True,exist_ok=True)
  process=subprocess.run([sys.executable,str(helper),row['file'],'--output_dir',str(out),'--dpi','100'],capture_output=True,text=True,encoding='utf8',errors='replace',env=env,timeout=100)
  (out/'render.log').write_text(process.stdout+'\n'+process.stderr,encoding='utf8')
  if process.returncode:raise RuntimeError('Render failed: '+row['key']+'; see '+str(out/'render.log'))
  done.write_text(json.dumps({'pages':len(list(out.glob('page-*.png')))}))
 pages=json.loads(done.read_text())['pages'];report.append({**row,'pages':pages,'directory':str(out.resolve())});print(json.dumps({'key':row['key'],'pages':pages}),flush=True)
(root/'render-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
