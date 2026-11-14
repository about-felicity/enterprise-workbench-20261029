from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing, nullcontext
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import service
from collector import links_from_text, rate_limit_error, snapshot
from xiaohongshu import note_from_html, note_metrics, share_error


class VideoServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = patch.object(service, "DB", Path(self.directory.name) / "videos.sqlite")
        self.mode = patch.object(service, "EMPLOYEE_MODE", False)
        self.database.start()
        self.mode.start()
        service.initialize()
        service.add("https://www.douyin.com/video/1234567890123456789", "3")
        self.row = self.work()

    def tearDown(self):
        service.CLAIMED.clear()
        self.mode.stop()
        self.database.stop()
        self.directory.cleanup()

    def work(self):
        with closing(service.connect()) as db:
            return dict(db.execute("SELECT * FROM works ORDER BY id DESC LIMIT 1").fetchone())

    def delete(self, actor="superadmin"):
        service.delete_work(self.row["id"], self.row["record_key"], actor)

    def check(self, at, **outcome):
        with patch.object(service, "now", return_value=at):
            service.save(self.row, **outcome)

    def accessible_result(self):
        return {"post_id": "1234567890123456789", "url": self.row["input_url"], "title": "测试作品",
                "author": "测试作者", "likes": 10, "comments": 3, "favorites": 2, "shares": 0}

    def test_xiaohongshu_share_text_preserves_token_and_deduplicates_by_note_id(self):
        note_id = "6acd9cc7000000001500aee2"
        escaped = rf"笔记链接 https\://www\.xiaohongshu.com/discovery/item/{note_id}?source=webshare&xsec_token=token%2Bvalue=&xsec_source=pc_share。"
        note_url = f"https://www.xiaohongshu.com/discovery/item/{note_id}?xsec_token=token%2Bvalue%3D&xsec_source=pc_share"
        self.assertEqual(links_from_text(escaped), [note_url])
        service.add(escaped)
        service.add(f"https://www.xiaohongshu.com/explore/{note_id}", "1.50")
        note, douyin = service.works()["works"]
        self.assertEqual((note["platform"], note["post_id"], note["input_url"], note["fee_cents"]),
                         ("xiaohongshu", note_id, note_url, 150))
        self.assertEqual(douyin["platform"], "douyin")
        self.assertEqual(links_from_text("https://xhslink.com/a/AbCd https://www.xiaohongshu.com.evil/explore/" + note_id),
                         ["https://xhslink.com/a/AbCd"])

    def test_xiaohongshu_snapshot_preserves_rounded_labels_and_nullable_counts(self):
        note_id = "6acd9cc7000000001500aee2"
        service.add(f"https://www.xiaohongshu.com/explore/{note_id}")
        row = self.work()
        raw = {"noteId": note_id, "type": "normal", "desc": "undefined inside a string",
               "user": {"userId": "someone"}, "interactInfo": {"likedCount": "2.5万", "commentCount": "0", "collectedCount": "2.6万"}}
        payload = json.dumps({"note": {"noteDetailMap": {note_id: {"note": raw}}}}, ensure_ascii=False)
        html = '<script>window.__INITIAL_STATE__=' + payload[:-1] + ',"optional":undefined}</script>'
        self.assertEqual(note_from_html(html, note_id), raw)
        self.assertIsNone(note_from_html(html, "0" * 24))
        at = datetime.fromisoformat("2026-11-11T10:00:00+08:00")
        with patch.object(service, "now", return_value=at):
            service.save(row, result={"post_id": note_id, "url": row["input_url"], "author": "作者", "title": "笔记", **note_metrics(raw)})
        note = service.works(day=at.date().isoformat())["works"][0]
        data = note["day_snapshot"]
        self.assertEqual((data["likes"], data["favorites"], data["comments"], data["shares"]), (25000, 26000, 0, None))
        self.assertEqual(data["metric_labels"], {"likes": "2.5万", "favorites": "2.6万"})
        self.assertEqual(note["availability"], "available")
        self.assertEqual(self.work()["next_check_at"], int((at + timedelta(minutes=15)).timestamp()))

    def test_xiaohongshu_cooldown_does_not_block_douyin(self):
        service.add("https://xhslink.com/a/AbCd")
        budget = service.CheckBudget()
        with patch.object(service, "BROWSER_BUDGET", budget):
            budget.pause(60, "xiaohongshu")
            self.assertEqual(service.claim_work()["id"], self.row["id"])
            self.assertIsNone(service.claim_work())

    def test_xiaohongshu_uses_zero_for_explicit_empty_counts_only(self):
        self.assertEqual(note_metrics({"interactInfo": {"likedCount": "1", "commentCount": "",
                                                       "collectedCount": "", "shareCount": ""}}),
                         {"likes": 1, "comments": 0, "favorites": 0, "shares": 0})
        self.assertEqual(note_metrics({"interactInfo": {"likedCount": "", "shareCount": None}}), {"likes": 0})
        self.assertEqual(note_metrics({}), {})

    def test_xiaohongshu_share_error_is_scoped_and_preserves_unknown_availability(self):
        note_id = '6acd9cc7000000001500aee2'
        url = f'https://www.xiaohongshu.com/404?source=note&noteId={note_id}&errorCode=-510001'
        error = share_error(url, note_id)
        self.assertEqual((error.availability, error.category, error.post_id), ('unknown', 'share_unavailable', note_id))
        self.assertIn('重新复制分享链接', str(error))
        self.assertEqual(share_error(url, '0' * 24).category, 'navigation')
        self.assertIsNone(share_error(url.replace('source=note', 'source=other'), note_id))
        self.assertIsNone(share_error(url.replace('xiaohongshu.com', 'xiaohongshu.com.example.org'), note_id))
        row = {**self.row, 'platform': 'xiaohongshu', 'url': None, 'post_id': 'xhs:' + note_id}
        with patch.object(service, 'read_work', side_effect=error) as read:
            with self.assertRaises(service.CheckError):
                service.check_work(row, Mock())
            read.assert_called_once()

    def test_browser_watchdog_detects_stalled_checks_and_browser_cleanup(self):
        with patch.object(service, 'BROWSER_PROGRESS', {1: (100, 262), 2: (170, None), 3: (200, 12)}):
            self.assertEqual(service.stalled_browser_work(219), [])
            self.assertEqual(service.stalled_browser_work(220), [262])
            self.assertEqual(service.stalled_browser_work(290), [262, None])

    def test_transient_failure_preserves_last_verified_state_and_daily_result(self):
        confirmed = datetime.fromisoformat("2026-11-11T11:30:00+08:00")
        failed = confirmed + timedelta(minutes=15)
        self.check(confirmed, result=self.accessible_result())
        self.check(failed, error="浏览器读取失败")
        row = self.work()
        self.assertEqual(row["availability"], "available")
        self.assertEqual(row["last_check_status"], "unknown")
        self.assertEqual(row["last_confirmed_at"], confirmed.isoformat())
        self.assertEqual(row["last_attempt"], failed.isoformat())
        summary = service.works()["failure_rates"]["check"][0]
        self.assertEqual((summary["available"], summary["unresolved"]), (1, 0))
        with patch.object(service, "now", return_value=failed + timedelta(minutes=4, seconds=59)):
            self.assertIsNone(service.next_work())
        with patch.object(service, "now", return_value=failed + timedelta(minutes=5)):
            self.assertEqual(service.next_work()["id"], self.row["id"])

    def test_confirmation_can_change_in_both_directions_after_read_failure(self):
        at = datetime.fromisoformat("2026-11-11T11:30:00+08:00")
        self.check(at, result=self.accessible_result())
        self.check(at + timedelta(minutes=15), error="抖音返回作品为私密", availability="unavailable")
        self.check(at + timedelta(minutes=30), error="网络连接失败")
        self.assertEqual(self.work()["availability"], "unavailable")
        self.check(at + timedelta(minutes=35), result=self.accessible_result())
        self.assertEqual(self.work()["availability"], "available")
        self.assertEqual(self.work()["last_check_status"], "available")
        with patch.object(service, "now", return_value=at + timedelta(minutes=49)):
            self.assertIsNone(service.next_work())
        with patch.object(service, "now", return_value=at + timedelta(minutes=50)):
            self.assertEqual(service.next_work()["id"], self.row["id"])

    def test_failed_check_without_prior_evidence_is_unknown(self):
        at = datetime.fromisoformat("2026-11-11T11:30:00+08:00")
        self.check(at, error="读取失败")
        self.assertEqual(self.work()["availability"], "unknown")
        self.assertIsNone(self.work()["last_confirmed_at"])

    def test_legacy_unknown_row_uses_existing_confirmation_evidence(self):
        confirmed = datetime.fromisoformat("2026-11-10T11:30:00+08:00")
        unavailable = confirmed + timedelta(days=1)
        failed = unavailable + timedelta(days=1)
        self.check(confirmed, result=self.accessible_result())
        self.check(unavailable, error="作品已删除", availability="unavailable")
        self.check(failed, error="读取失败")
        with closing(service.connect()) as db, db:
            db.execute("ALTER TABLE works DROP COLUMN last_check_status")
            db.execute("ALTER TABLE works DROP COLUMN last_confirmed_at")
            db.execute("UPDATE works SET availability = 'unknown' WHERE id = ?", (self.row["id"],))
        service.initialize()
        row = self.work()
        self.assertEqual(row["availability"], "unavailable")
        self.assertEqual(row["last_check_status"], "unknown")
        self.assertEqual(row["last_confirmed_at"], unavailable.isoformat())

    def test_known_work_retries_share_link_after_navigation_or_detail_failure(self):
        row = {**self.row, "post_id": "1234567890123456789", "url": self.row["input_url"],
               "input_url": "https://v.douyin.com/original/"}
        context, retry_context = Mock(), Mock()
        context.browser.new_context.return_value = nullcontext(retry_context)
        for category in ("navigation", "detail"):
            with self.subTest(category=category), patch.object(service.time, "sleep"):
                result = self.accessible_result()
                error = service.CheckError("temporary failure", category=category)
                with patch.object(service, "read_work", side_effect=[error, result]) as read:
                    self.assertEqual(service.check_work(row, context), result)
                self.assertEqual([call.args for call in read.call_args_list],
                                 [(context, row["url"], row["post_id"]), (retry_context, row["input_url"], row["post_id"])])

    def test_transport_timeout_and_rate_limit_do_not_immediately_open_another_page(self):
        for category in ("transport", "timeout", "rate_limit"):
            with self.subTest(category=category), patch.object(service, "read_work", side_effect=
                    service.CheckError("temporary failure", category=category)) as read:
                with self.assertRaises(service.CheckError):
                    service.check_work(self.row, Mock())
                read.assert_called_once()

    def test_single_unavailable_page_uses_the_share_link_before_changing_status(self):
        row = {**self.row, "availability": "available", "pending": 0, "post_id": "1234567890123456789",
               "url": self.row["input_url"], "input_url": "https://v.douyin.com/original/"}
        context, retry_context = Mock(), Mock()
        context.browser.new_context.return_value = nullcontext(retry_context)
        unavailable = service.CheckError("你要观看的图文不存在", "unavailable", category="page_unavailable")
        result = self.accessible_result()
        with patch.object(service.time, "sleep"), patch.object(service, "read_work", side_effect=[unavailable, result]) as read:
            self.assertEqual(service.check_work(row, context), result)
        self.assertEqual([call.args for call in read.call_args_list],
                         [(context, row["url"], row["post_id"]), (retry_context, row["input_url"], row["post_id"])])

    def test_only_the_fallback_saying_unavailable_keeps_the_last_confirmation(self):
        row = {**self.row, "availability": "available", "pending": 0}
        context = Mock()
        context.browser.new_context.return_value = nullcontext(Mock())
        incomplete = service.CheckError("抖音未返回作品详情", category="detail")
        unavailable = service.CheckError("你要观看的图文不存在", "unavailable", category="page_unavailable")
        with patch.object(service.time, "sleep"), patch.object(service, "read_work", side_effect=[incomplete, unavailable]):
            with self.assertRaises(service.CheckError) as caught:
                service.check_work(row, context)
        self.assertEqual(caught.exception.availability, "unknown")

    def test_confirmed_unavailable_works_keep_one_regular_page_check(self):
        row = {**self.row, "availability": "unavailable", "pending": 0}
        unavailable = service.CheckError("你要观看的图文不存在", "unavailable", category="page_unavailable")
        with patch.object(service, "read_work", side_effect=unavailable) as read:
            with self.assertRaises(service.CheckError) as caught:
                service.check_work(row, Mock())
        self.assertIs(caught.exception, unavailable)
        read.assert_called_once()

    def test_two_unavailable_pages_confirm_the_change(self):
        row = {**self.row, "availability": "available", "pending": 0}
        context = Mock()
        context.browser.new_context.return_value = nullcontext(Mock())
        unavailable = service.CheckError("你要观看的图文不存在", "unavailable", category="page_unavailable")
        with patch.object(service.time, "sleep"), patch.object(service, "read_work", side_effect=[unavailable, unavailable]) as read:
            with self.assertRaises(service.CheckError) as caught:
                service.check_work(row, context)
        self.assertEqual(caught.exception.availability, "unavailable")
        self.assertEqual(read.call_count, 2)

    def test_platform_cooldown_leaves_a_single_unavailable_page_unconfirmed(self):
        row = {**self.row, "availability": "available", "pending": 0}
        unavailable = service.CheckError("你要观看的图文不存在", "unavailable", category="page_unavailable")
        with patch.object(service.time, "sleep"), patch.object(service.BROWSER_BUDGET, "paused_until", return_value=float("inf")):
            with patch.object(service, "read_work", side_effect=unavailable) as read:
                with self.assertRaises(service.CheckError) as caught:
                    service.check_work(row, Mock())
        self.assertEqual(caught.exception.availability, "unknown")
        read.assert_called_once()

    def test_matched_photo_metadata_proves_access_without_metrics(self):
        page = Mock()
        page.url = "https://www.douyin.com/note/1234567890123456789"
        page.goto.return_value = Mock(status=200, url=page.url)
        with patch("collector.work_props", return_value={"images": [{}], "desc": "测试图文"}):
            result = snapshot(page, page.url)
        self.assertEqual(result["post_id"], "1234567890123456789")
        self.assertNotIn("likes", result)
        self.assertFalse(any(call.args == ("body",) for call in page.locator.call_args_list))

    def test_rate_limit_uses_retry_after_with_safe_default(self):
        self.assertEqual(rate_limit_error(Mock(headers={"retry-after": "180"})).retry_after, 180)
        self.assertEqual(rate_limit_error(Mock(headers={"retry-after": "invalid"})).retry_after, 60)

    def test_manual_refresh_leads_new_entries_but_yields_to_overdue_works(self):
        at = datetime.fromisoformat("2026-11-11T10:00:00+08:00")
        self.check(at, result=self.accessible_result())
        with patch.object(service, "now", return_value=at + timedelta(minutes=17)):
            service.add("https://v.douyin.com/new-fixture/")
            fresh = self.work()
            service.add("https://v.douyin.com/manual-fixture/")
            manual = self.work()
            service.refresh(manual["id"])
            self.assertEqual(service.next_work()["id"], self.row["id"])
            self.assertEqual(service.next_work((self.row["id"],))["id"], manual["id"])
            self.assertEqual(service.next_work((self.row["id"], manual["id"]))["id"], fresh["id"])

    def test_unknown_checks_back_off_to_15_minutes_and_reset_on_confirmation(self):
        at = datetime.fromisoformat("2026-11-11T10:00:00+08:00")
        self.check(at, result=self.accessible_result())
        for index, delay in enumerate((5, 10, 15, 15), 1):
            self.check(at, error="读取失败")
            work = self.work()
            self.assertEqual(work["availability"], "available")
            self.assertEqual(work["check_failures"], min(index, 3))
            at += timedelta(minutes=delay)
            self.assertEqual(work["next_check_at"], int(at.timestamp()))
        self.check(at, error="已设为私密", availability="unavailable")
        self.assertEqual(self.work()["check_failures"], 0)
        self.assertEqual(self.work()["next_check_at"], int((at + service.CHECK_INTERVAL).timestamp()))

    def test_migration_preserves_due_time_for_existing_works(self):
        checked = datetime.fromisoformat("2026-11-11T10:00:00+08:00")
        self.check(checked, result=self.accessible_result())
        with closing(service.connect()) as db, db:
            db.execute("DROP INDEX works_by_check_time")
            db.execute("ALTER TABLE works DROP COLUMN next_check_at")
            db.execute("ALTER TABLE works DROP COLUMN check_failures")
        at = checked + timedelta(minutes=12)
        with patch.object(service, "now", return_value=at):
            service.initialize()
            self.assertIsNone(service.next_work())
        self.assertEqual(self.work()["next_check_at"], int((checked + service.CHECK_INTERVAL).timestamp()))

    def test_shared_budget_reserves_a_slot_and_preserves_the_longest_cooldown(self):
        budgets = [service.CheckBudget(self.directory.name, name) for name in ("creator", "employee", "paid-media")]
        with ExitStack() as sessions:
            for budget in (budgets[0], budgets[0], budgets[0], budgets[1], budgets[1], budgets[2]):
                self.assertTrue(sessions.enter_context(budget.browser_slot()))
            for budget in budgets:
                self.assertFalse(sessions.enter_context(budget.browser_slot()))
        with budgets[2].browser_slot() as slot:
            self.assertTrue(slot)
        with patch.object(service.time, "time", return_value=100):
            budgets[0].pause(200)
            budgets[1].pause(60)
            self.assertEqual(budgets[2].paused_until(), 300)
            with patch.object(service, "BROWSER_BUDGET", budgets[2]):
                self.assertIsNone(service.claim_work())

    def test_browser_retains_page_and_detail_requests_without_heavy_assets(self):
        for resource in ("image", "media", "font", "document", "stylesheet", "script", "xhr", "fetch"):
            route = Mock()
            route.request.resource_type = resource
            service.route_check_request(route)
            if resource in {"image", "media", "font"}:
                route.abort.assert_called_once()
                route.continue_.assert_not_called()
            else:
                route.continue_.assert_called_once()
                route.abort.assert_not_called()

    def test_transport_cooldown_pauses_new_checks_and_resumes_without_discarding_work(self):
        cooldown = service.TransportCooldown()
        self.assertFalse(cooldown.record_failure(1, 10))
        self.assertFalse(cooldown.record_failure(2, 120))
        self.assertFalse(cooldown.record_failure(2, 125))
        self.assertFalse(cooldown.record_failure(3, 130))
        self.assertTrue(cooldown.record_failure(4, 135))
        self.assertFalse(cooldown.record_failure(5, 136))
        with patch.object(service, "TRANSPORT_COOLDOWN", cooldown):
            with patch.object(service.time, "monotonic", return_value=194):
                self.assertIsNone(service.claim_work())
            self.assertEqual(self.work(), self.row)
            with patch.object(service.time, "monotonic", return_value=195):
                self.assertEqual(service.claim_work()["id"], self.row["id"])

    def test_isolated_page_timeouts_do_not_pause_the_ledger(self):
        cooldown = service.TransportCooldown()
        with patch.object(service, "TRANSPORT_COOLDOWN", cooldown):
            for work_id in (1, 2, 3):
                service.save_check_error({**self.row, "id": work_id},
                                         service.CheckError("读取超时", category="timeout"))
        self.assertEqual(cooldown.until, 0)
        self.assertFalse(cooldown.record_failure(1, 10))
        self.assertFalse(cooldown.record_failure(2, 15))
        cooldown.record_success()
        self.assertFalse(cooldown.record_failure(3, 20))

    def test_only_superadmin_can_delete(self):
        for actor in ("", "geo_admin", "xuyan", "fengyuan"):
            with self.subTest(actor=actor), self.assertRaises(PermissionError):
                self.delete(actor)
        self.assertEqual(self.work(), self.row)

    def test_delete_archives_and_removes_linked_records(self):
        with closing(service.connect()) as db, db:
            db.execute("INSERT INTO snapshots(work_id, day, captured_at, likes, comments, favorites, shares) VALUES (?, '2026-11-11', 'now', 10, 3, 2, 0)", (self.row["id"],))
            db.execute("INSERT INTO availability_checks VALUES (?, '2026-11-11', 'now', 'available')", (self.row["id"],))
            db.execute("INSERT INTO work_imports VALUES ('test.xlsx', 'sheet', 1, '2026-11-11', ?, ?, '{}')", (self.row["input_url"], self.row["id"]))
        self.delete()
        with closing(service.connect()) as db:
            for table in ("works", "snapshots", "availability_checks", "work_imports"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            archive = db.execute("SELECT deleted_by, record_json FROM deleted_works").fetchone()
        self.assertEqual(archive["deleted_by"], "superadmin")
        self.assertEqual(json.loads(archive["record_json"])["work"]["record_key"], self.row["record_key"])

    def test_retry_and_stale_collector_preserve_reused_id(self):
        self.delete()
        service.add("https://www.douyin.com/video/9876543210987654321", "8")
        replacement = self.work()
        self.assertEqual(replacement["id"], self.row["id"])
        self.assertNotEqual(replacement["record_key"], self.row["record_key"])
        self.delete()
        service.save(self.row, error="late collection")
        service.save(self.row, result={"post_id": "1234567890123456789"})
        self.assertEqual(self.work(), replacement)
        with self.assertRaises(ValueError):
            service.delete_work(replacement["id"], "0" * 32, "superadmin")

    def test_concurrent_deletes_are_idempotent(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.delete(), range(2)))
        with closing(service.connect()) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM deleted_works").fetchone()[0], 1)

    def test_legacy_rows_get_stable_record_keys(self):
        legacy = Path(self.directory.name) / "legacy.sqlite"
        with closing(sqlite3.connect(legacy)) as db, db:
            db.execute("CREATE TABLE works (id INTEGER PRIMARY KEY, input_url TEXT UNIQUE, post_id TEXT UNIQUE, url TEXT, author TEXT, title TEXT, pending INTEGER DEFAULT 1, last_attempt TEXT, last_error TEXT)")
            db.execute("INSERT INTO works(input_url) VALUES ('https://v.douyin.com/legacy/')")
        with patch.object(service, "DB", legacy):
            service.initialize()
            key = self.work()["record_key"]
            self.assertRegex(key, r"^[0-9a-f]{32}$")
            service.initialize()
            self.assertEqual(self.work()["record_key"], key)

    def test_employee_mode_deletion(self):
        with patch.object(service, "EMPLOYEE_MODE", True):
            service.initialize()
            service.add("https://v.douyin.com/employee/", uploader="xuyan")
            employee = self.work()
            self.assertEqual(employee["uploader"], "xuyan")
            service.delete_work(employee["id"], employee["record_key"], "superadmin")
            self.assertEqual(self.work()["record_key"], self.row["record_key"])

    def test_http_permission_and_record_version_checks(self):
        server = service.ThreadingHTTPServer(("127.0.0.1", 0), service.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/works"
        payload = json.dumps({"delete_work_id": self.row["id"], "record_key": self.row["record_key"]}).encode()
        try:
            for actor in ("geo_admin", "xuyan", "fengyuan"):
                headers = {"X-Geo-User": actor, "Content-Type": "application/json"}
                with urlopen(Request(endpoint, headers=headers)) as response:
                    self.assertFalse(json.load(response)["can_delete"])
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(endpoint, data=payload, headers=headers))
                self.assertEqual(error.exception.code, 403)
            headers = {"X-Geo-User": "superadmin", "Content-Type": "application/json"}
            with urlopen(Request(endpoint, headers=headers)) as response:
                self.assertTrue(json.load(response)["can_delete"])
            with urlopen(Request(endpoint, data=payload, headers=headers)) as response:
                self.assertEqual(json.load(response)["works"], [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
