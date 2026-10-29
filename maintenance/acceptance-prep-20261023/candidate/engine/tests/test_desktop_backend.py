import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_source_cards.desktop_backend import articles, refresh


class DesktopStatusTests(unittest.TestCase):
    def test_changed_archive_is_visible_but_not_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            article = root / "articles/2026-10-07/类别/01"
            article.mkdir(parents=True)
            (article / "draft.md").write_text("# 标题\n正文", encoding="utf8")
            (article / "article.docx").write_bytes(b"original")
            hashes = {
                name: hashlib.sha256((article / name).read_bytes()).hexdigest()
                for name in ("draft.md", "article.docx")
            }
            (article / "receipt.json").write_text(
                json.dumps(
                    {
                        "status": "accepted_for_user_review",
                        "date": "2026-10-07",
                        "category": "类别",
                        "number": 1,
                        "files": hashes,
                        "word_sha256": hashes["article.docx"],
                    }
                ),
                encoding="utf8",
            )
            self.assertEqual(articles(root)[0]["integrity"], "verified")
            (article / "draft.md").write_text("# 修改后的标题", encoding="utf8")
            self.assertEqual(articles(root)[0]["integrity"], "changed")
            (article / "withdrawal.json").write_text(
                json.dumps({"word_sha256": hashes["article.docx"]}),
                encoding="utf8",
            )
            self.assertEqual(articles(root), [])

    def test_failed_ssh_never_claims_cached_status_is_live(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            config.write_text(json.dumps({"local_root": str(root)}), encoding="utf8")
            (root / "desktop_server_cache.json").write_text(
                '{"checked_epoch":1}', encoding="utf8"
            )
            with patch(
                "geo_source_cards.desktop_backend.server_snapshot",
                side_effect=OSError("connection refused"),
            ):
                result = refresh(config)
            self.assertEqual(result["connection"], "unverified")
            self.assertEqual(result["server"]["checked_epoch"], 1)
            self.assertEqual(result["connection_error"], "OSError")
