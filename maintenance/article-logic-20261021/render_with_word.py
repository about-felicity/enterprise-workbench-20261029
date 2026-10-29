"""Use the skill renderer with installed Word and bundled Poppler on Windows."""
import importlib.util,subprocess,sys
from pathlib import Path

skill=Path('C:/Users/78567/.codex/plugins/cache/openai-primary-runtime/documents/26.1015.12040/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('skill_renderer',skill);renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
def convert(doc_path,user_profile,convert_tmp_dir,stem,verbose=False):
    pdf=Path(convert_tmp_dir)/(stem+'.pdf')
    def literal(value):return "'"+str(value).replace("'","''")+"'"
    command="$ErrorActionPreference='Stop';$app=$null;$doc=$null;try{$app=New-Object -ComObject Word.Application;$app.Visible=$false;$app.DisplayAlerts=0;$doc=$app.Documents.Open("+literal(Path(doc_path).resolve())+",$false,$true,$false);$doc.ExportAsFixedFormat("+literal(pdf.resolve())+",17)}finally{if($doc){$doc.Close(0)};if($app){$app.Quit()}}"
    r=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=90)
    if r.returncode or not pdf.exists() or not pdf.stat().st_size:raise RuntimeError('Word read-only PDF export failed: '+r.stderr[-1200:])
    return str(pdf),'Installed Word read-only conversion; original DOCX not modified'
original_pages=renderer.convert_from_path
def pages(pdf_path,**kwargs):
    kwargs['poppler_path']='C:/Users/78567/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
    return original_pages(pdf_path,**kwargs)
renderer.convert_to_pdf=convert
renderer.convert_from_path=pages
renderer.main()
