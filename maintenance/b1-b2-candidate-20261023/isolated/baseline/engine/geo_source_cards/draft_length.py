"""Conservative whole-paragraph trimming before independent semantic review."""

import re

from .editorial_analysis import normalize


def length(text):
    return len(normalize(re.sub(r"[#*_`]+", "", text)))


def fit_draft(answer, *, minimum=1400, maximum=2200):
    """Keep headings, evidence claims, disclosure and each section's first text.

    Never truncate sentences, remove mapped facts or change their wording. If
    those constraints cannot achieve the limit, retain the original for rejection.
    The resulting text must still pass the ordinary checks and independent review.
    """
    original = answer["draft_markdown"]
    if length(original) <= maximum:
        return answer, []
    paragraphs = re.split(r"\n\s*\n", original.strip())
    claims = [
        c.get("text", "")
        for c in answer.get("claim_map", {}).get("claims", [])
        if c.get("text")
    ]
    protected = set()
    next_body = True
    for index, paragraph in enumerate(paragraphs):
        if paragraph.lstrip().startswith("#"):
            protected.add(index)
            next_body = True
        elif next_body:
            protected.add(index)
            next_body = False
        if any(claim in paragraph for claim in claims) or re.search(
            "自有品牌|商业关联|商业合作|推广合作", paragraph
        ):
            protected.add(index)
    removed = set()
    for index in sorted(
        set(range(len(paragraphs))) - protected,
        key=lambda i: len(paragraphs[i]),
        reverse=True,
    ):
        candidate = "\n\n".join(
            p for i, p in enumerate(paragraphs) if i not in removed | {index}
        )
        if length(candidate) < minimum:
            continue
        removed.add(index)
        if length(candidate) <= maximum:
            if not all(claim in candidate for claim in claims):
                return answer, []
            return {**answer, "draft_markdown": candidate + "\n"}, [
                paragraphs[i] for i in sorted(removed)
            ]
    return answer, []
