"""Verify schema gates and that opening native stores cannot write to them."""
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_storage import REQUIRED, StorageError, databases, open_readonly, schema

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.path=self.root/'chat.db'
        with closing(sqlite3.connect(self.path)) as db, db:
            for table,columns in REQUIRED.items():
                db.execute('create table "'+table+'" ('+','.join('"'+name+'" text' for name in columns)+')')

    def tearDown(self):self.temp.cleanup()

    def test_discovery_skips_other_databases_and_non_sqlite(self):
        (self.root/'encrypted.db').write_bytes(b'not a sqlite file')
        with closing(sqlite3.connect(self.root/'metrics.db')) as db, db:db.execute('create table metrics (x text)')
        self.assertEqual(databases(self.root),[self.path])

    def test_readonly_rejects_writes(self):
        with closing(open_readonly(self.path)) as db:
            self.assertTrue(schema(db))
            with self.assertRaises(sqlite3.OperationalError):db.execute('delete from ChatMessages')

    def test_changed_native_schema_blocks(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('alter table ChatMessages rename column raw_data to unsupported')
        with self.assertRaises(StorageError):databases(self.root)

if __name__=='__main__':unittest.main()
