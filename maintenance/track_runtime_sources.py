"""Stage only reviewed mapped source files outside existing nested repositories."""
import json,subprocess
from pathlib import Path
W=Path(__file__).resolve().parents[1]
manifest=json.loads((W/'source-snapshot/local-manifest.json').read_text('utf-8'))
nested={'geo-source-card-collectors','redroid','Scrapling','doubao-headless-technical-docs'}
allowed={'.py','.js','.ts','.tsx','.jsx','.html','.css','.md','.service','.timer','.conf'}
sources=sorted({r['source'] for r in manifest['files'] if Path(r['source']).parts[0] not in nested and Path(r['source']).suffix in allowed})
subprocess.run(['git','add','-f','--',*sources],cwd=W,check=True)
print(json.dumps({'reviewed_live_source_files_staged':len(sources),'existing_nested_repositories_untouched':True}))
