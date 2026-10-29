from pathlib import Path
root=Path(__file__).resolve().parents[2]/'geo-monitor-deploy/creation'
library=root/'library.js';base=library.read_text('utf-8').split('// Uploads have their own')[0]
new=base+(root/'uploads.js').read_text('utf-8');library.write_text(new,encoding='utf-8')
p=root/'panel.html';text=p.read_text('utf-8');start=text.index('// Independent product library.');end=text.index('</script>',start)
p.write_text(text[:start]+new+'\n'+text[end:],encoding='utf-8')
