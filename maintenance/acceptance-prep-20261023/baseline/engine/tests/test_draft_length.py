import unittest

from geo_source_cards.draft_length import fit_draft


class DraftLengthTests(unittest.TestCase):
    def test_preserves_claims_and_sections_while_removing_only_whole_paragraphs(self):
        draft = (
            "# 标题\n\n本文涉及自有品牌产品。\n\n## 选择\n\n必要解释。\n\n"
            + "重复例子。" * 20
            + "\n\n产品规格200ml。\n\n## 核对\n\n保留条件。"
        )
        value = {
            "draft_markdown": draft,
            "claim_map": {"claims": [{"text": "产品规格200ml。"}]},
        }
        result, removed = fit_draft(value, minimum=20, maximum=80)
        self.assertTrue(removed)
        self.assertIn("产品规格200ml。", result["draft_markdown"])
        self.assertIn("## 核对\n\n保留条件。", result["draft_markdown"])
        self.assertEqual(result["claim_map"], value["claim_map"])

    def test_does_not_force_trim_when_all_content_is_protected(self):
        value = {
            "draft_markdown": "# 标题\n\n" + "重要证据。" * 30,
            "claim_map": {"claims": []},
        }
        result, removed = fit_draft(value, minimum=20, maximum=60)
        self.assertEqual(result, value)
        self.assertFalse(removed)

    def test_within_limit_is_unchanged(self):
        value = {"draft_markdown": "# 标题\n\n完整内容。"}
        self.assertEqual(fit_draft(value), (value, []))
