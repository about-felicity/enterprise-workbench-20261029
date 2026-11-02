TEST="import copy,unittest\nfrom geo_source_cards.rewrite_v2.structure_parser import validate\nfrom geo_source_cards.rewrite_v2.full_writer import normalize_answer\nclass Formats(unittest.TestCase):\n def test_optional_strings_preserve_content(self):\n  x={'article_type':'ranking','tone':'plain','article_structure':['opening'],'writing_rhythm':'steady','special_style_elements':'contrast','forbidden_pattern':'no copying; keep attribution'}\n  before=copy.deepcopy(x);y=validate(x)\n  self.assertEqual(y['forbidden_pattern'],[x['forbidden_pattern']]);self.assertEqual(x,before)\n def test_invalid_fields_still_rejected(self):\n  x={'article_type':'ranking','tone':'plain','article_structure':['opening'],'writing_rhythm':'steady','special_style_elements':[],'forbidden_pattern':{}}\n  with self.assertRaises(ValueError):validate(x)\n def test_writer_note_only(self):\n  x={'draft_markdown':'# title\\n\\nbody','_note':'internal'}\n  self.assertEqual(normalize_answer(x),{'draft_markdown':x['draft_markdown']});self.assertIn('_note',x)\n  for value in [dict(x,unexpected=True),dict(x,_note={})]:self.assertEqual(normalize_answer(value),value)\n def test_writer_draft_note(self):\n  x={'draft_markdown':'# title\\n\\nbody','draft_markdown_note':'internal'}\n  self.assertEqual(normalize_answer(x),{'draft_markdown':x['draft_markdown']})\n  self.assertIn('draft_markdown_note',x)\n  for value in [dict(x,unexpected=True),dict(x,draft_markdown_note={}),dict(x,_note='extra')]:\n   self.assertEqual(normalize_answer(value),value)\nif __name__=='__main__':unittest.main()\r\n"
import json,sqlite3,subprocess,os
from pathlib import Path
base=Path('/opt/monitor')
for p in base.glob('*.db'):
 if 'doubao' not in p.name:continue
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
  print('DB',p.name,tables[:15])
  if 'responses' in tables:print('SCHEMA',list(db.execute('pragma table_info(responses)')))
work=base/'geo-content/maintenance/recovery-20261102/writer'
env=dict(os.environ,PYTHONPATH=str(base/'geo-content')+':'+str(base/'geo-content/engine'))
test=work/'test_response_format_recovery.py'
test.write_text(TEST)
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B',str(test)],env=env,capture_output=True,text=True,timeout=60)
print('TESTS',r.stdout+r.stderr);assert r.returncode==0

