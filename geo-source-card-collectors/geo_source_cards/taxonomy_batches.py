"""Durable bounded classification with exact per-batch source coverage."""

import hashlib
import json
from pathlib import Path

from .api_prompts import QUALITY, evidence_spans
from .daily_editorial import safe_name
from .deepseek_api import APIError
from .editorial_analysis import cosine, tfidf_vectors
from .prompt_compaction import compact_input
from .runtime import atomic_json

VERSION = "taxonomy-batches-v1"


def validate_assignments(result, expected, ids):
    rows = result.get("assignments", [])
    if not isinstance(rows, list):
        raise APIError("invalid_taxonomy_batch_assignment")
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise APIError("invalid_taxonomy_batch_assignment")
        source, category, quote = (
            item.get(k) for k in ("source_id", "category_id", "quote_id")
        )
        if (
            source not in expected
            or source in seen
            or category not in ids
            or quote not in expected[source]
        ):
            raise APIError("invalid_taxonomy_batch_assignment")
        seen.add(source)
    if seen != set(expected):
        raise APIError("taxonomy_batch_coverage_incomplete")
    return rows


def classify(client, run, meta, *, batch_size=12):
    run = Path(run)
    raw = json.loads((run / "input.json").read_text("utf8"))
    binding = hashlib.sha256(
        (VERSION + json.dumps(raw, sort_keys=True, ensure_ascii=False)).encode()
    ).hexdigest()
    folder = run / "call"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / "batch_manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text())["input_sha256"] != binding:
            raise APIError("taxonomy_batch_input_changed")
    else:
        atomic_json(
            manifest,
            {
                "input_sha256": binding,
                "kind": "local_batch_orchestration",
                "batch_size": batch_size,
            },
        )
    data = compact_input("taxonomy", raw)
    spans = evidence_spans(data, "taxonomy")
    atomic_json(run / "evidence_spans.json", spans)
    articles = data["articles"]
    vectors = tfidf_vectors(
        [
            a["article"]["title"]
            + " ".join(s["text"] for s in a["article"]["evidence_spans"])
            for a in articles
        ]
    )
    chosen = [0]
    while len(chosen) < min(16, len(articles)):
        chosen.append(
            max(
                (i for i in range(len(articles)) if i not in chosen),
                key=lambda i: min(1 - cosine(vectors[i], vectors[j]) for j in chosen),
            )
        )
    representatives = [
        {
            "title": articles[i]["article"]["title"],
            "evidence": [s["text"] for s in articles[i]["article"]["evidence_spans"]],
        }
        for i in chosen
    ]
    plan_prompt = (
        QUALITY
        + "\n根据全部标题和差异较大的代表原文，拟定当日动态类别。类别按内容主题与体裁，不按域名或平台。分析过程不作为消费者正文。不要输出具体来源归属，后续分批归类。返回JSON categories，每项包含id(C1等)、label(18字内)、description(70字内)、writing_angles(每项22字内，最多3项且不超过max_per_category)。类别不超过10个，不为凑数分裂。\n"
        + json.dumps(
            {
                "titles": [a["article"]["title"] for a in articles],
                "representatives": representatives,
                "max_per_category": raw["max_per_category"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    plan = client.complete(
        plan_prompt, folder / "plan", max_tokens=2600, meta=meta, stage="taxonomy"
    )
    categories = plan.get("categories", [])
    if not categories or len(categories) > 10:
        raise APIError("invalid_taxonomy_plan")
    ids, labels = set(), set()
    for category in categories:
        identity = category.get("id")
        label = category.get("label", "")
        if (
            not isinstance(identity, str)
            or identity in ids
            or not identity
            or safe_name(label) != label
            or label in labels
            or not category.get("description")
            or not category.get("writing_angles")
        ):
            raise APIError("invalid_taxonomy_plan")
        ids.add(identity)
        labels.add(label)
    output = {
        c["id"]: {k: c[k] for k in ("label", "description", "writing_angles")}
        | {"sources": []}
        for c in categories
    }
    for start in range(0, len(articles), batch_size):
        batch = articles[start : start + batch_size]
        inputs = [
            {
                "source_id": f"S{start + i + 1}",
                "title": a["article"]["title"],
                "spans": [[s["id"], s["text"]] for s in a["article"]["evidence_spans"]],
            }
            for i, a in enumerate(batch)
        ]
        expected = {item["source_id"]: {s[0] for s in item["spans"]} for item in inputs}
        if any(not values for values in expected.values()):
            raise APIError("taxonomy_source_has_no_literal_evidence")
        prompt = (
            QUALITY
            + '\n将本批每篇文章分配到一个最合适的已有类别。每个source_id恰好出现一次，不遗漏、不添加。quote_id必须属于该source_id的spans。返回JSON {"assignments":[{"source_id":"S1","category_id":"C1","quote_id":"E1_1"}]}。只处理本批，不生成新类别，不输出正文或URL。\n'
            + json.dumps(
                {"categories": categories, "sources": inputs},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        result = client.complete(
            prompt,
            folder / f"batch-{start // batch_size:03d}",
            max_tokens=1600,
            meta=meta,
            stage="taxonomy",
        )
        try:
            assignments = validate_assignments(result, expected, ids)
        except APIError as error:
            # The complete response is known and cached. Correct this group once;
            # never replace its evidence or replay an unknown network request.
            correction = (
                "\n上次本组归属未通过严格校验，请仅纠正本组。类别ID只能从以下集合选取："
                + json.dumps(sorted(ids))
                + "。逐项核对source_id和quote_id，覆盖本组全部来源。上次响应："
                + json.dumps(result, ensure_ascii=False)
                + "\n"
            )
            head, payload = prompt.rsplit("\n", 1)
            atomic_json(
                folder / f"batch-{start // batch_size:03d}-validation.json",
                {"error": error.code, "allowed_categories": sorted(ids)},
            )
            corrected = client.complete(
                head + correction + payload,
                folder / f"batch-{start // batch_size:03d}-repair",
                max_tokens=1600,
                meta=meta,
                stage="taxonomy",
            )
            assignments = validate_assignments(corrected, expected, ids)
        for assignment in assignments:
            source_id, category_id, quote_id = (
                assignment.get(k) for k in ("source_id", "category_id", "quote_id")
            )
            output[category_id]["sources"].append(
                {"quote_id": quote_id, "duplicate_of": ""}
            )
        atomic_json(
            folder / "batch_progress.json",
            {
                "validated_sources": start + len(batch),
                "total_sources": len(articles),
                "completed_batches": start // batch_size + 1,
            },
        )
    # Exact duplicate bodies share an identity regardless of model assignment.
    body_hashes, duplicate_of = {}, {}
    for source in raw["articles"]:
        digest = hashlib.sha256(
            "".join(source["article"]["text"].split()).encode()
        ).hexdigest()
        if digest in body_hashes:
            duplicate_of[source["url"]] = body_hashes[digest]
        else:
            body_hashes[digest] = source["url"]
    for category in output.values():
        for source in category["sources"]:
            source["duplicate_of"] = duplicate_of.get(
                spans[source["quote_id"]]["url"], ""
            )
    answer = {"categories": [c for c in output.values() if c["sources"]]}
    atomic_json(folder / "response.json", answer)
    atomic_json(
        folder / "api_state.json",
        {
            "state": "RESPONDED",
            "kind": "local_batch_aggregate",
            "input_sha256": binding,
        },
    )
    return answer
