"""Read-only selection of regenerable content artifacts; no production actions."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
relative = lambda p: p.relative_to(BASE).as_posix()
plan = {}

def add(path, reason, canonical=None):
    path = path.resolve()
    if not path.is_relative_to(BASE) or path.is_symlink() or not path.is_file():
        raise ValueError("Unsafe cleanup path")
    if not (path.is_relative_to(BASE / "outputs") or path.is_relative_to(BASE / "geo-source-card-collectors/geo_source_cards/__pycache__")):
        raise ValueError("Outside cleanup scope")
    canonical = canonical.resolve() if canonical else None
    if canonical and (not canonical.is_relative_to(BASE) or not canonical.is_file() or canonical == path):
        raise ValueError("Missing preserved original")
    plan[relative(path)] = {"path": str(path), "relative_path": relative(path),
        "bytes": path.stat().st_size, "sha256": sha(path), "reason": reason,
        "preserved_source": str(canonical) if canonical else None,
        "source_sha256": sha(canonical) if canonical else None}

for name in ("brow-qa", "brow-qa-v3", "eye-qa"):
    root = BASE / "outputs" / name
    for image in root.glob("pages/*/page-*.png"):
        source = root / (image.parent.name + ".docx")
        if source.is_file():
            add(image, "regenerable_word_page_png", source)
    for image in root.glob("contacts/*.png"):
        source = root / (re.sub(r"-\d+$", "", image.stem) + ".docx")
        if source.is_file():
            add(image, "regenerable_word_contact_sheet", source)

layout = BASE / "outputs/api-editorial/diagnostics/layout-v2"
rows = json.loads((layout / "render_manifest.json").read_text(encoding="utf-8"))
all_layout_sources_exist = True
for row in rows:
    source = Path(row["file"])
    if not source.is_file():
        all_layout_sources_exist = False
        continue
    for image in (layout / "pages" / f'{row["index"]:02d}').glob("page-*.png"):
        add(image, "regenerable_word_page_png", source)
if all_layout_sources_exist:
    for image in layout.glob("sheet-*.png"):
        add(image, "regenerable_word_contact_sheet", layout / "render_manifest.json")
for image in (layout / "render").glob("page-*.png"):
    if (layout / "sample.docx").is_file():
        add(image, "regenerable_word_page_png", layout / "sample.docx")

for image in (BASE / "outputs").rglob("page-*.png"):
    if relative(image) in plan:
        continue
    pdfs = list(image.parent.glob("*.pdf"))
    if len(pdfs) == 1 and pdfs[0].read_bytes().startswith(b"%PDF-"):
        add(image, "regenerable_pdf_page_png", pdfs[0])

cache = BASE / "geo-source-card-collectors/geo_source_cards/__pycache__"
for path in cache.glob("*.pyc"):
    source = cache.parent / (path.name.split(".")[0] + ".py")
    if source.is_file():
        add(path, "regenerable_python_bytecode", source)

for archive, original in [
    ("outputs/brow-qa-v3/brow-final.zip", "outputs/brow-e2e-20261020.zip"),
    ("outputs/eye-qa/input.zip", "outputs/eye-e2e-20261020.zip"),
]:
    path, source = BASE / archive, BASE / original
    if path.is_file() and source.is_file() and sha(path) == sha(source):
        add(path, "byte_identical_duplicate_archive", source)

# Only generated wheel-build copies with a byte-identical preserved source.
canonical = {}
for root in (BASE / "source-snapshot", BASE / "geo-source-card-collectors/geo_source_cards"):
    for source in root.rglob("*.py"):
        canonical.setdefault(sha(source), source)
for build_name in ("provenance-wheel-build", "build-daily-source-20261010"):
    for source in (BASE / "outputs/api-editorial/intermediates" / build_name).rglob("*.py"):
        retained = canonical.get(sha(source))
        if retained:
            add(source, "byte_identical_generated_build_source", retained)

# Never delete an artifact needed to regenerate another selected artifact.
for row in plan.values():
    if row["preserved_source"] and relative(Path(row["preserved_source"])) in plan:
        raise ValueError("Plan would remove a canonical source")

roots = [BASE / "outputs", BASE / "maintenance", BASE / "source-snapshot",
         BASE / "geo-source-card-collectors", BASE / "geo-monitor-deploy/creation"]
protected = {}
for root in roots:
    for path in root.rglob("*"):
        if (not path.is_file() or path.is_symlink() or ".git" in path.parts
                or path.is_relative_to(OUT) or relative(path) in plan):
            continue
        protected[relative(path)] = sha(path)

git_before = {}
for name in (".", "geo-source-card-collectors", "multi-agent-content-studio", "writing-agent", "Scrapling"):
    result = subprocess.run(["git", "-C", str(BASE / name), "status", "--porcelain=v1", "-z"], capture_output=True)
    git_before[name] = {"returncode": result.returncode, "status_utf8": result.stdout.decode("utf-8", "replace")}
counts = Counter(row["reason"] for row in plan.values())
record = {"workspace": str(BASE), "actions": list(plan.values()),
    "file_count": len(plan), "bytes": sum(row["bytes"] for row in plan.values()),
    "by_reason": dict(counts), "protected_file_count": len(protected),
    "notes": ["All frozen candidates, real responses, ledgers, manuscripts, source documents and browser profiles retained", "No runtime business code or tests selected for deletion"]}
(OUT / "cleanup-plan.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "protected-before.json").write_text(json.dumps(protected, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "git-before.json").write_text(json.dumps(git_before, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: record[k] for k in ("file_count", "bytes", "by_reason", "protected_file_count")}, ensure_ascii=False))
