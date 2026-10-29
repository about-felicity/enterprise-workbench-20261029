import unittest
from geo_source_cards.desktop_logs import summarize_logs


class DesktopLogTests(unittest.TestCase):
    def test_recovery_displays_actual_reason_and_verification(self):
        row = summarize_logs([{'phase':'capture_recovery','model':'baidu_ai','kind':'verification','attempt':1,'attempt_limit':20,'error':'检测到百度安全验证'}])[0]
        self.assertIn('验证页面', row['text'])
        self.assertIn('当前上限20次', row['text'])
        self.assertIn('原因：检测到百度安全验证', row['text'])

    def test_summary_links_ticket_without_exposing_internal_fields(self):
        rows = summarize_logs([
            {'epoch': 1, 'phase': 'writer', 'ticket': 'internal-id', 'category': '选购', 'number': 2, 'message': '开始 API 阶段'},
            {'epoch': 2, 'phase': 'writer', 'ticket': 'internal-id', 'state': 'needs_attention', 'error': 'Draft checks rejected: 章节映射未覆盖完整提纲'},
        ])
        self.assertIn('选购 · 第2篇', rows[1]['text'])
        self.assertIn('文章章节与提纲不一致', rows[1]['text'])
        self.assertNotIn('internal-id', rows[1]['text'])
        self.assertTrue(rows[1]['failed'])

    def test_stage_acceptance_is_not_publication_and_cost_is_estimate(self):
        rows = summarize_logs([
            {'phase': 'research', 'state': 'accepted'},
            {'phase': 'cost', 'estimated_cny': .018, 'task': {'stage': 'writer', 'category': '选购', 'article': 1}},
        ])
        self.assertIn('信源分析阶段已通过检查', rows[0]['text'])
        self.assertIn('文章写作估算费用 ¥0.0180', rows[1]['text'])

    def test_capture_progress_and_failure_are_readable(self):
        rows = summarize_logs([
            {'phase':'capture','model':'deepseek','ordinal':2,'total':16,'question':'头屑怎么选','sources':12,'message':'本题采集完成'},
            {'phase':'capture_error','model':'wenxin_card','question':'头屑怎么选','error_type':'SecurityVerification','message':'本题暂停'},
        ])
        self.assertIn('DeepSeek · 第2/16题', rows[0]['text'])
        self.assertIn('取得信源 12 条', rows[0]['text'])
        self.assertTrue(rows[1]['failed'])
        self.assertIn('未知发送状态不会自动重发', rows[1]['text'])
