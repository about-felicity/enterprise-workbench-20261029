"""Local daily article research -> writing brief -> draft checks -> Word handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .editorial_analysis import (
    analyze_daily,
    build_prompt,
    review_draft,
    validate_product,
)
from .runtime import atomic_json, atomic_write, process_lock


def digest(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def prepare(
    input_path,
    product_path,
    output_dir,
    date,
    *,
    previous=None,
    scrapling_source=None,
    fetcher=None,
):
    from .article_fetch import ScraplingArticleFetcher, check_article_relevance
    from .source_analysis import analyze_records, load_records

    product = validate_product(
        json.loads(Path(product_path).read_text(encoding="utf-8-sig"))
    )
    records = load_records(input_path)
    if not records:
        raise ValueError("No platform observations supplied")
    original = json.dumps(records, ensure_ascii=False, sort_keys=True)
    job_id = digest(
        date
        + "\n"
        + original
        + "\n"
        + json.dumps(product, ensure_ascii=False, sort_keys=True)
    )[:24]
    output_dir = Path(output_dir)
    with process_lock(output_dir / "pipeline.lock"):
        path = output_dir / "writing_job.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf8"))
            if existing["job_id"] != job_id:
                raise ValueError(
                    "Output directory belongs to different observations/product; use another directory"
                )
            if existing["status"] in {
                "waiting_writer",
                "needs_revision",
                "ready_for_editorial_review",
            }:
                return existing
        atomic_json(output_dir / "observations.json", records)
        atomic_json(output_dir / "product.json", product)
        job = {
            "job_id": job_id,
            "date": date,
            "status": "fetching_articles",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "demo": bool(product.get("demo")),
        }
        atomic_json(path, job)
        fetcher = fetcher or ScraplingArticleFetcher(source=scrapling_source)
        analyzed = list(
            analyze_records(
                records, fetcher=fetcher, cache_dir=output_dir / "article_cache"
            )
        )
        for original_record, record in zip(records, analyzed):
            if "wire_question" in original_record:
                record["wire_question"] = original_record["wire_question"]
            for source in record["sources"]:
                source["article"] = check_article_relevance(
                    source["article"], source.get("title", "")
                )
        atomic_write(
            output_dir / "articles.jsonl",
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in analyzed),
        )
        prior = (
            json.loads(Path(previous).read_text(encoding="utf8")) if previous else None
        )
        report = analyze_daily(analyzed, date, prior)
        atomic_json(output_dir / "analysis.json", report)
        if not report["counts"]["fetched_articles"]:
            job.update(status="blocked_no_article_text", counts=report["counts"])
            atomic_json(path, job)
            return job
        prompt = build_prompt(report, product, job_id=job_id)
        atomic_write(output_dir / "writing_prompt.md", prompt)
        job.update(
            status="waiting_writer",
            prompt_sha256=digest(prompt),
            counts=report["counts"],
            prompt_file="writing_prompt.md",
            expected_reply="draft.md",
            writer_instruction="Read writing_prompt.md in this directory; write the complete article to draft.md. Preserve this job directory.",
        )
        atomic_write(
            output_dir / "writing_task.txt",
            (
                "使用本地电脑完成一次写作任务。只在以下工作目录读写，不操作其他项目：\n"
                + str(output_dir.resolve())
                + "\n"
                + "先读取 writing_prompt.md 与 writing_job.json，按提示词生成完整文章。\n"
                + "将 UTF-8 Markdown 正文保存为 draft.md；同一篇正文排版输出完整 Word，保存为 article.docx。\n"
                + "不要覆盖 writing_prompt.md、observations.json、articles.jsonl、analysis.json 或 writing_job.json。\n"
                + "示例产品必须明确标记示例，不得补造真实产品资料。\n"
                + "写完文件后，最后创建 writer_done.json，内容为：\n"
                + json.dumps(
                    {
                        "job_id": job_id,
                        "prompt_sha256": digest(prompt),
                        "status": "completed",
                        "draft_file": "draft.md",
                        "word_file": "article.docx",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n发生错误就报告错误，不得创建完成标记。\n"
            ),
        )
        atomic_json(path, job)
        return job


def finish(job_dir, draft_path, *, export_word=True):
    from .source_analysis import load_records

    root = Path(job_dir)
    with process_lock(root / "pipeline.lock"):
        job = json.loads((root / "writing_job.json").read_text(encoding="utf8"))
        prompt = (root / "writing_prompt.md").read_text(encoding="utf8")
        if digest(prompt) != job["prompt_sha256"]:
            raise ValueError("Writing prompt changed after preparation")
        draft_path = Path(draft_path)
        if draft_path.suffix.lower() != ".md":
            raise ValueError(
                "Expected a UTF-8 Markdown article, not a copied chat screenshot"
            )
        draft = draft_path.read_text(encoding="utf-8-sig")
        product = json.loads((root / "product.json").read_text(encoding="utf8"))
        records = load_records(root / "articles.jsonl")
        articles = {
            source["url"]: {**source["article"], "url": source["url"]}
            for row in records
            for source in row["sources"]
            if source["article"]["status"] == "fetched"
        }
        review = review_draft(draft, list(articles.values()), product)
        atomic_write(root / "draft.md", draft)
        atomic_json(root / "draft_review.json", review)
        status = (
            "needs_revision" if review["failures"] else "ready_for_editorial_review"
        )
        if review["failures"]:
            atomic_write(
                root / "revision_prompt.md",
                prompt
                + "\n请修订上一版文章，必须解决以下问题：\n"
                + "\n".join("- " + reason for reason in review["failures"])
                + "\n只输出修订后的完整文章。\n",
            )
        if export_word:
            from .word_export import export_docx

            filename = (
                "draft-needs-review.docx" if review["failures"] else "article.docx"
            )
            export_docx(draft, root / filename, demo=bool(product.get("demo")))
            job["word_file"] = filename
        job.update(
            status=status,
            draft_sha256=digest(draft),
            review_file="draft_review.json",
            publication_approved=False,
        )
        atomic_json(root / "writing_job.json", job)
        return job


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Daily source research, local Doubao writing brief, draft checks and Word export"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    prepare_cmd.add_argument("--input", type=Path, required=True)
    prepare_cmd.add_argument("--product", type=Path, required=True)
    prepare_cmd.add_argument("--output-dir", type=Path, required=True)
    prepare_cmd.add_argument(
        "--date", default=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    )
    prepare_cmd.add_argument("--previous", type=Path)
    prepare_cmd.add_argument("--scrapling-source", type=Path)
    finish_cmd = commands.add_parser("finish")
    finish_cmd.add_argument("--job-dir", type=Path, required=True)
    finish_cmd.add_argument("--draft", type=Path, required=True)
    finish_cmd.add_argument("--no-word", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        job = prepare(
            args.input,
            args.product,
            args.output_dir,
            args.date,
            previous=args.previous,
            scrapling_source=args.scrapling_source,
        )
    else:
        job = finish(args.job_dir, args.draft, export_word=not args.no_word)
    print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0 if job["status"] in {"waiting_writer", "ready_for_editorial_review"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
