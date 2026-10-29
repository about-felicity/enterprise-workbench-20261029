import zipfile
from pathlib import Path
ws=Path(__file__).resolve().parents[3]
out=Path(__file__).with_name('eye-daily-patch.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for name in ['studio.py','runtime.py','materials.py','worker.py','knowledge.py','article_export.py','panel.html','wizard.js','wizard_sections.html','test_workflow.py','test_materials.py']:
  z.write(ws/'geo-monitor-deploy/creation'/name,'creation/'+name)
 for name in ['daily_editorial.py','article_allocation.py','article_quality.py','genre_pools.py','reference_design.py','genre_prompts.py','genre_outline.py','product_identity.py','append_repair.py','auto_repair.py']:
  z.write(ws/'geo-source-card-collectors/geo_source_cards'/name,'engine/geo_source_cards/'+name)
 for name in ['test_article_allocation.py','test_article_quality.py','test_genre_pools.py','test_reference_design.py','test_product_identity.py','test_genre_length.py','test_auto_repair.py']:
  z.write(ws/'geo-source-card-collectors/tests'/name,'tests/'+name)
print(out)
