import unittest
from geo_source_cards.append_repair import apply


class AppendRepairTests(unittest.TestCase):
    def test_preserves_original_and_merges_claims(self):
        old = '# 标题\n\n原段落。\n\n## 知识\n\n原解释。'
        claims = {'claims':[{'text':'原事实','evidence_ids':['KU1']}]}
        answer = {'additions':[{'after':'原段落。','text':'新增导语。'},
                               {'after':'原解释。','text':'新增解释。'}],
                  'additional_claims':[{'text':'新增解释。','evidence_ids':['KU2']}]}
        result = apply(old,claims,{'sections':[]},answer)
        self.assertEqual(result['draft_markdown'].replace('\n\n新增导语。','').replace('\n\n新增解释。',''),old)
        self.assertEqual(len(result['claim_map']['claims']),2)
        self.assertEqual(len(claims['claims']),1)

    def test_rejects_missing_ambiguous_and_heading_edits(self):
        for original, anchor, addition in [('正文','不存在','补充'),('重复重复','重复','补充'),('正文','正文','## 新章'),('# 标题\n\n背景','# 标题','还有一层困惑')]:
            with self.assertRaises(ValueError):
                apply(original,{'claims':[]},{}, {'additions':[{'after':anchor,'text':addition}]})
