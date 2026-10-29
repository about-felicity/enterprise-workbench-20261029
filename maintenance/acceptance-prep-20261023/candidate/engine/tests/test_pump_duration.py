import unittest

from geo_source_cards.editorial_analysis import review_draft


class PumpDurationTests(unittest.TestCase):
    def test_general_price_opinion_is_advisory_but_not_verified(self):
        result = review_draft(
            "# 购买比较\n## 容量\n百元内产品包装可能更基础。\n## 偏好\n先看实际标签。",
            [], {"forbidden_claims": []}, min_chars=1,
            require_product_mention=False,
        )
        self.assertEqual(result["failures"], [])
        self.assertTrue(result["warnings"])
        self.assertFalse(result["product_claims_fact_checked"])

    def test_missing_baseline_volume_cannot_be_used_for_duration(self):
        result = review_draft(
            "如果上一瓶用了四个月，同样用量下200ml大约撑两个月左右。",
            [],
            {"approved": [], "forbidden": []},
            require_product_mention=False,
        )
        self.assertIn("容量不能直接推断", str(result))

    def rejected(self, text):
        result = review_draft(
            text, [], {"approved": [], "forbidden": []}, require_product_mention=False
        )
        return "不能由泵数" in str(result)

    def test_warning_and_observed_empty_bottle_dates_are_not_inferences(self):
        self.assertFalse(
            self.rejected(
                "记录开始使用日期和实际空瓶日期。不要用每次几泵去反推天数，因为每泵毫升数并不公开。"
            )
        )

    def test_duration_without_pump_volume_is_rejected(self):
        self.assertTrue(self.rejected("这瓶200ml每次两泵，一瓶能用一个多月。"))

    def test_numeric_duration_without_pump_volume_is_rejected(self):
        self.assertTrue(self.rejected("200ml每次两泵，能用30天。"))

    def test_explicit_hypothetical_volume_is_not_missing(self):
        self.assertFalse(
            self.rejected("假设每泵2毫升，200ml每次两泵，每天一次，可以用50天。")
        )

    def test_warning_does_not_hide_a_later_positive_inference(self):
        self.assertTrue(self.rejected("200ml每次两泵，不能乱推算，但一瓶能用30天。"))

    def test_explicit_rejection_of_duration_estimate_is_not_estimate(self):
        warning = "在没有每泵毫升数的前提下，任何“一瓶能用一个月”的推算都不成立。"
        self.assertFalse(self.rejected(warning))
        self.assertTrue(self.rejected(warning + "但200ml每次两泵，一瓶能用30天。"))

    def test_source_analysis_is_not_a_consumer_article(self):
        result = review_draft(
            "# 去屑洗发水榜单怎么读\n\n分析媒体结构。",
            [],
            {"approved": [], "forbidden": []},
            require_product_mention=False,
        )
        self.assertIn("成品主题偏离", str(result))

    def test_reader_fill_in_blanks_are_not_finished_copy(self):
        result = review_draft(
            "购买记录：到手价____元。",
            [],
            {"approved": [], "forbidden": []},
            require_product_mention=False,
        )
        self.assertIn("未填写空白项", str(result))

    def test_attribution_does_not_bypass_medicinal_usage_gate(self):
        result = review_draft(
            "来源提到药用类洗剂被建议用于阶段性护理而非天天用。",
            [],
            {"approved": [], "forbidden": []},
            require_product_mention=False,
        )
        self.assertIn("药用产品频次", str(result))


if __name__ == "__main__":
    unittest.main()
