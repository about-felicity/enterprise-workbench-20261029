import unittest
from geo_source_cards.source_contract import bind, validate
from geo_source_cards.genre_pools import classify_source

class DailySourceTests(unittest.TestCase):
    def setUp(self):
        self.source = {"url":"today", "article":{"title":"油头怎么选", "text":"当天采集的完整正文"}}
        self.blueprint = bind({"primary_url":"today"}, [self.source], "2026-10-09")

    def test_replay_keeps_capture_batch_date(self):
        validate(self.blueprint, [{"sources":[self.source]}])
        self.assertEqual("2026-10-09", self.blueprint["source_contract"]["batch_date"])

    def test_old_or_foreign_source_cannot_be_added(self):
        with self.assertRaises(ValueError):
            validate(self.blueprint, [{"sources":[self.source, {**self.source, "url":"yesterday"}]}])

    def test_body_and_title_are_immutable(self):
        for key in ("title", "text"):
            changed = {**self.source, "article":{**self.source["article"], key:"替换的内容"}}
            with self.assertRaises(ValueError):
                validate(self.blueprint, [{"sources":[changed]}])

    def test_missing_primary_is_rejected(self):
        with self.assertRaises(ValueError):
            bind({"primary_url":"old"}, [self.source], "2026-10-09")

    def test_overlapping_forms_and_audience_are_separate(self):
        result = classify_source({"url":"x", "article":{"title":"男士洗发水怎么选：4款成分对比自用分享", "text":"一、甲洗发水。配方。二、乙洗发水。配方。"}})
        self.assertEqual("体验分享", result["article_type"])
        self.assertIn("成分解析", result["structure_tags"])
        self.assertIn("男士", result["topic_tags"])
        self.assertEqual("排行类", result["genre"])

    def test_single_promotional_guide_is_not_pure_science(self):
        result = classify_source({"url":"x", "article":{"title":"油头怎么选", "text":"代表案例：某品牌，购买时参考。"}})
        self.assertEqual("选购指南", result["article_type"])
        self.assertEqual("needs_review", result["status"])
