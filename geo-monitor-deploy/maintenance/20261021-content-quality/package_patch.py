from pathlib import Path
import zipfile
root=Path.cwd()
files={
 **{'geo-source-card-collectors/geo_source_cards/'+n:'engine/geo_source_cards/'+n for n in ['consumer_voice.py','consumer_prompts.py','staged_editorial.py','daily_editorial.py','genre_prompts.py','api_prompts.py','reference_prompts.py','auto_repair.py','append_repair.py','api_worker.py']},
 **{'geo-monitor-deploy/creation/'+n:'creation/'+n for n in ['service.py','runtime.py','client.py','panel.html','wizard.js','article_export.py','quality_repair.py','test_download_service.py','test_materials.py','test_workflow.py','test_client_projection.py']},
 'geo-source-card-collectors/tests/test_consumer_voice.py':'tests/test_consumer_voice.py',
 'geo-source-card-collectors/tests/test_append_repair.py':'tests/test_append_repair.py',
}
out=root/'geo-monitor-deploy/maintenance/20261021-content-quality/patch.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for source,target in files.items():z.write(root/source,target)
print(len(files))
