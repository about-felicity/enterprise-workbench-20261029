import json,unittest
from .client import recover_transport_json

class ResponseFramingTests(unittest.TestCase):
    def test_exact_dsml_tail_preserves_draft(self):
        result={'draft_markdown':'# 标题\n正文“引号”\n尾段'}
        suffix='</｜｜DSML｜｜ parameter>\n</｜｜DSML｜｜ invoke>\n</｜｜DSML｜｜ calls>'
        self.assertEqual(recover_transport_json(json.dumps(result,ensure_ascii=False)+suffix)[0],result)

    def test_extra_prose_or_second_object_not_accepted(self):
        for tail in [' instructions','{}','</script>','']:
            with self.assertRaises(ValueError):recover_transport_json('{"draft_markdown":"text"}'+tail)

    def test_stray_quote_only_with_complete_skeleton(self):
        result={'article_type':'ranking','tone':'客观','article_structure':['开头','比较'],
                'writing_rhythm':'先慢后快','special_style_elements':[],'forbidden_pattern':[]}
        value=json.dumps(result,ensure_ascii=False).replace('], "writing_rhythm"',']", "writing_rhythm"')
        self.assertEqual(recover_transport_json(value)[0],result)
        with self.assertRaises(ValueError):recover_transport_json('{"article_structure":["x"]", "writing_rhythm":"y"}')
