import unittest
from geo_source_cards.genre_length import hanzi, body, policy, validate


class LongFormTests(unittest.TestCase):
    def test_english_roster_and_headings_cannot_pad_body_length(self):
        text = '# ' + '题' * 1000 + '\n## Brand Name\n正文ABC123。'
        self.assertEqual(2, hanzi(body(text)))

    def test_ranking_needs_substantial_context_before_first_product(self):
        design = {'version':'two-genre-v1', 'genre':'ranking', 'products':[],'owned_product':{'name':'科熙本'}}
        direct = '# 标题\n\n## 1 科熙本\n' + '正' * 3000
        self.assertTrue(any('名单前' in v for v in validate(direct, design)))
        developed = '# 标题\n\n' + '引' * 600 + '\n\n## 1 科熙本\n' + '正' * 2400
        self.assertEqual([], validate(developed, design))

    def test_science_length_does_not_count_headings(self):
        design = {'version':'two-genre-v1', 'genre':'science'}
        text = '# 科普\n\n' + '引' * 220 + '\n## ' + '题' * 3000 + '\n短正文'
        self.assertTrue(any('正文汉字不足' in v for v in validate(text, design)))

    def test_legacy_contract_is_unchanged(self):
        self.assertIsNone(policy({'genre':'numbered_product_roundup'}))
        self.assertEqual([], validate('旧稿', {'genre':'ranking'}))
