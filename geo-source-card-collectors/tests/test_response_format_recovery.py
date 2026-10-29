import copy,unittest
from geo_source_cards.rewrite_v2.structure_parser import validate
from geo_source_cards.rewrite_v2.full_writer import normalize_answer
class Formats(unittest.TestCase):
 def test_optional_strings_preserve_content(self):
  x={'article_type':'ranking','tone':'plain','article_structure':['opening'],'writing_rhythm':'steady','special_style_elements':'contrast','forbidden_pattern':'no copying; keep attribution'}
  before=copy.deepcopy(x);y=validate(x)
  self.assertEqual(y['forbidden_pattern'],[x['forbidden_pattern']]);self.assertEqual(x,before)
 def test_invalid_fields_still_rejected(self):
  x={'article_type':'ranking','tone':'plain','article_structure':['opening'],'writing_rhythm':'steady','special_style_elements':[],'forbidden_pattern':{}}
  with self.assertRaises(ValueError):validate(x)
 def test_writer_note_only(self):
  x={'draft_markdown':'# title\n\nbody','_note':'internal'}
  self.assertEqual(normalize_answer(x),{'draft_markdown':x['draft_markdown']});self.assertIn('_note',x)
  for value in [dict(x,unexpected=True),dict(x,_note={})]:self.assertEqual(normalize_answer(value),value)
if __name__=='__main__':unittest.main()
