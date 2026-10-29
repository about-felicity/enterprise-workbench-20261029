"""Durable capture journal; uncertain submissions are never silently repeated."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from .runtime import atomic_write


class Journal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("pragma journal_mode=WAL")
        self.db.execute("pragma synchronous=FULL")
        self.db.executescript("""
        create table if not exists batches(batch text primary key, fingerprint text not null);
        create table if not exists captures(
          task_id text primary key, batch text not null, ordinal integer not null,
          model text not null, question text not null, round integer not null,
          output text not null, state text not null default 'pending',
          started real, finished real, result text, error text);
        create table if not exists read_recoveries(
          task_id text primary key, recovered real not null, previous_state text not null,
          previous_error text, previous_result text, reason text not null);
        """)

    def recover_read_failures(self, batch):
        """One explicit recovery of diagnosed read-only Baidu page failures.

        DeepSeek submissions, interrupted operations, verification challenges and
        unknown errors are never reset by this path.
        """
        count = 0
        with self.db:
            for row in self.db.execute(
                "select * from captures where batch=? and state='needs_attention'",
                (batch,),
            ).fetchall():
                known_read_error = any(
                    value in (row["error"] or "")
                    for value in (
                        "百度 AI 卡片未完整呈现",
                        "Page.evaluate: Execution context was destroyed",
                        "Page.goto: Timeout",
                    )
                )
                if (
                    row["model"] not in {"baidu_ai", "wenxin_card"}
                    or not known_read_error
                ):
                    continue
                if self.db.execute(
                    "select 1 from read_recoveries where task_id=?", (row["task_id"],)
                ).fetchone():
                    continue
                self.db.execute(
                    "insert into read_recoveries values(?,?,?,?,?,?)",
                    (
                        row["task_id"],
                        time.time(),
                        row["state"],
                        row["error"],
                        row["result"],
                        "Diagnosed read-only result-page failure; fixed snapshot/navigation handling; one operator-authorized reload",
                    ),
                )
                self.db.execute(
                    "update captures set state='pending',error=null,result=null where task_id=?",
                    (row["task_id"],),
                )
                count += 1
        return count

    def plan(self, batch, model, questions, rounds, output):
        output = str(Path(output).resolve())
        fingerprint = json.dumps([model, questions, rounds, output], ensure_ascii=False)
        with self.db:
            old = self.db.execute(
                "select fingerprint from batches where batch=?", (batch,)
            ).fetchone()
            if old and old[0] != fingerprint:
                raise ValueError("Existing batch parameters cannot change")
            self.db.execute(
                "insert or ignore into batches values(?,?)", (batch, fingerprint)
            )
            for ordinal, question in enumerate(questions):
                for round_number in range(1, rounds + 1):
                    task = hashlib.sha256(
                        f"{batch}:{ordinal}:{round_number}".encode()
                    ).hexdigest()
                    self.db.execute(
                        "insert or ignore into captures(task_id,batch,ordinal,model,question,round,output) values(?,?,?,?,?,?,?)",
                        (task, batch, ordinal, model, question, round_number, output),
                    )
            self.db.execute(
                "update captures set state='needs_attention',error='Previous capture interrupted; submission outcome unknown' where batch=? and state='capturing'",
                (batch,),
            )
        return list(
            self.db.execute(
                "select * from captures where batch=? order by ordinal,round", (batch,)
            )
        )

    def start(self, task):
        with self.db:
            changed = self.db.execute(
                "update captures set state='capturing',started=? where task_id=? and state='pending'",
                (time.time(), task),
            ).rowcount
            if changed != 1:
                raise RuntimeError("Task is not pending")

    def unsubmitted(self, task):
        """Only called after a live collector proves no Enter/send was attempted."""
        with self.db:
            self.db.execute(
                "update captures set state='pending',started=null,error=null where task_id=? and state='capturing'",
                (task,),
            )

    def complete(self, task, record):
        with self.db:
            changed = self.db.execute(
                "update captures set state='completed',finished=?,result=?,error=null where task_id=? and state='capturing'",
                (time.time(), json.dumps(record, ensure_ascii=False), task),
            ).rowcount
            if changed != 1:
                raise RuntimeError("Task is not capturing")

    def fail(self, task, error, partial_result=None):
        with self.db:
            self.db.execute(
                "update captures set state='needs_attention',error=?,result=? where task_id=? and state='capturing'",
                (
                    str(error),
                    json.dumps(partial_result, ensure_ascii=False)
                    if partial_result is not None
                    else None,
                    task,
                ),
            )

    def export(self, output):
        rows = self.db.execute(
            "select result from captures where output=? and state='completed' order by rowid",
            (str(Path(output).resolve()),),
        )
        atomic_write(Path(output), "".join(row[0] + "\n" for row in rows))

    def close(self):
        self.db.close()
