import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from .article_format import contract_issues, editorial_revision, prepare


class ArticleFormatTests(unittest.TestCase):
    def test_product_lines_become_word_compatible_headings(self):
        original = '# 洗发水选购\n\n开头。\n\nTop1. 清风洗发水\n\n第一段。\n\nTop2. 海岸洗发露\n\n第二段。\n'
        revised, issues = prepare(original, '排行类', strict=True)
        self.assertFalse(issues)
        self.assertIn('## Top1. 清风洗发水\n\n第一段。', revised)
        self.assertIn('## Top2. 海岸洗发露\n\n第二段。', revised)
        self.assertEqual(prepare(revised, '排行类', strict=True), (revised, ()))

    def test_count_check_uses_the_complete_numbered_roster(self):
        original = '# 三款洗发水选购\n\n## 产品清单\n\n### 第1款：清风洗发水\n\n### 第2款：海岸洗发露\n'
        _, issues = prepare(original, '排行类', strict=True)
        self.assertIn('标题写 3 款，正文名单核对为 2 款', issues[0])
        correct = original.replace('三款', '两款')
        self.assertEqual(prepare(correct, '排行类', strict=True)[1], ())
        misleading = correct + '\n以上三款产品各有侧重。\n'
        self.assertIn('正文中提到的产品款数不一致', prepare(misleading, '排行类', strict=True)[1][0])

    def test_missing_product_roster_requires_review(self):
        original = '# 三款精华怎么挑\n\n## 选购要点\n\n看肤质。\n\n## 日常用法\n\n留意用量。\n'
        self.assertIn('正文缺少可核对的产品清单', prepare(original, '排行类', strict=True)[1][0])

    def test_copied_staff_and_platform_notes_are_removed(self):
        note = '（声明：本平台所发布信息的内容和准确性由提供消息的原单位或组织独立承担完全责任!）'
        staff = '责任编辑：张编辑'
        disclosure = '（本稿涉及自有品牌产品，存在商业关联。）'
        original = f'# 标题\n\n正文。\n\n{disclosure}\n\n{note}\n\n{staff}\n'
        revised, issues = prepare(original, '科普类', reference=note + '\n' + staff, strict=True)
        self.assertFalse(issues)
        self.assertIn(disclosure, revised)
        self.assertNotIn(note, revised)
        self.assertNotIn(staff, revised)

    def test_unverified_staff_mark_is_reported(self):
        original = '# 标题\n\n正文。\n\n作者：李作者\n'
        revised, issues = prepare(original, '科普类', strict=True)
        self.assertEqual(revised, original)
        self.assertIn('请核对发布主体', issues[0])

    def test_numbering_is_checked_even_without_a_count_in_the_title(self):
        original = '# 旅行装备选购\n\n## 推荐清单\n\n### 第1款：轻便帐篷\n\n### 第3款：折叠炊具\n'
        _, issues = prepare(original, '排行类', strict=True)
        self.assertIn('编号跳号', issues[0])

    def test_ranking_contract_does_not_count_generic_sections_as_product_headings(self):
        original = '# 旅行装备选购\n\n## 选购指南\n\n正文。\n\n## 总结\n\n正文。\n'
        self.assertIn('逐款列出', contract_issues(original, '排行类')[0])
        corrected = original + '\n### 第1款：轻便帐篷\n\n### 第2款：折叠炊具\n'
        self.assertFalse(contract_issues(corrected, '排行类'))

    def test_explicit_product_names_work_outside_the_original_categories(self):
        original = '# 三款旅行装备对比\n\n## 推荐清单\n\n### 第1款：轻便帐篷\n\n### 第2款：折叠炊具\n'
        _, issues = prepare(original, '科普类', strict=True)
        self.assertIn('标题写 3 款，正文名单核对为 2 款', issues[0])

    def test_revision_is_bound_to_source_and_checks_its_own_content(self):
        from . import runtime

        source = '# 原标题\n\n正文。\n'
        revised = '# 新标题\n\n正文。\n'
        digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest()
        data = {'source_sha256': digest(source), 'revision_sha256': digest(revised), 'markdown': revised}
        with patch.object(runtime, 'read', return_value=data):
            self.assertEqual(editorial_revision(Path('approved/day/category/01'), source), data)
            self.assertIsNone(editorial_revision(Path('approved/day/category/01'), source + '追加。'))
            data['markdown'] += '未核对的新增内容。'
            self.assertIsNone(editorial_revision(Path('approved/day/category/01'), source))


if __name__ == '__main__':
    unittest.main()
