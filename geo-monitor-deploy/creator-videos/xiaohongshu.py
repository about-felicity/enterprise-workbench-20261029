"""Read the requested Xiaohongshu note from the public document response."""
from decimal import Decimal
import json
import re
from urllib.parse import urlsplit

from collector import (CheckError, XHS_HOSTS, XHS_SHORT_HOSTS, canonical_link,
                       publication_time, rate_limit_error, xhs_post_id)


INITIAL_STATE = re.compile(r"<script\b[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*(.*?)</script\s*>", re.S)
JS_UNDEFINED = re.compile(r'("(?:[^"\\]|\\.)*")|\bundefined\b')
COUNT = re.compile(r"([0-9]{1,15}(?:\.[0-9]{1,6})?)\s*([万亿wWkK]?)\s*(\+?)")
UNITS = {"": 1, "万": 10_000, "w": 10_000, "k": 1_000, "亿": 100_000_000}
FIELDS = {"likes": "likedCount", "comments": "commentCount", "favorites": "collectedCount", "shares": "shareCount"}


def note_from_html(html, post_id):
    match = INITIAL_STATE.search(html)
    if not match:
        return None
    try:
        payload = json.loads(JS_UNDEFINED.sub(lambda item: item[1] or "null", match[1].strip().removesuffix(";")))
        note = payload["note"]["noteDetailMap"][post_id]["note"]
    except (KeyError, TypeError, ValueError):
        return None
    if (isinstance(note, dict) and note.get("noteId") == post_id
            and isinstance(note.get("user"), dict) and note["user"].get("userId")
            and note.get("type") in {"normal", "video"}):
        return note
    return None


def note_metrics(note):
    stats = note.get("interactInfo")
    if not isinstance(stats, dict):
        return {}
    result, labels = {}, {}
    for name, key in FIELDS.items():
        value = stats.get(key)
        if type(value) is int and 0 <= value < 2**53:
            result[name] = value
        elif isinstance(value, str) and (match := COUNT.fullmatch(value.strip().replace(",", ""))):
            number, unit, plus = match.groups()
            count = Decimal(number) * UNITS[unit.lower()]
            if count == count.to_integral_value() and 0 <= count < 2**53:
                result[name] = int(count)
                if unit or plus:
                    labels[name] = value.strip()
    if labels:
        result["metric_labels"] = labels
    return result


def note_snapshot(page, link, expected_post_id=None):
    from playwright.sync_api import Error, TimeoutError

    expected_post_id = expected_post_id or xhs_post_id(link)
    responses = []

    def track(response):
        if (response.request.is_navigation_request() and urlsplit(response.url).hostname in XHS_HOSTS | XHS_SHORT_HOSTS
                and response.request.frame == page.main_frame):
            responses.append(response)

    def restrict(route):
        request = route.request
        parts = urlsplit(request.url)
        if (request.is_navigation_request() and parts.scheme == "https"
                and parts.netloc.lower() in XHS_HOSTS | XHS_SHORT_HOSTS):
            route.continue_()
        else:
            route.abort()

    page.on("response", track)
    page.route("**/*", restrict)
    try:
        page.goto(link, wait_until="commit", timeout=18000)
        if not any(xhs_post_id(item.url) or item.status == 429 for item in responses):
            try:
                page.wait_for_url(lambda url: xhs_post_id(url) is not None, wait_until="commit", timeout=5000)
            except TimeoutError:
                pass
        for response in responses:
            if response.status == 429:
                raise rate_limit_error(response, "小红书")
            post_id = xhs_post_id(response.url)
            if not post_id:
                continue
            if expected_post_id and post_id != expected_post_id:
                raise CheckError("小红书跳转到其他笔记，待确认", category="navigation")
            if response.status in (404, 410):
                raise CheckError(f"小红书笔记页返回 HTTP {response.status}", "unavailable",
                                 category="page_unavailable", post_id=post_id)
            if response.status >= 500:
                raise CheckError(f"小红书笔记页返回 HTTP {response.status}，待确认", category="transport")
            if response.status != 200:
                continue
            note = note_from_html(response.text(), post_id)
            if note is not None:
                user = note["user"]
                return {"post_id": post_id, "url": canonical_link(response.url),
                        "author": str(user.get("nickname") or "")[:100],
                        "creator_id": str(user["redId"])[:100] if user.get("redId") else None,
                        "creator_uid": str(user["userId"])[:100],
                        "title": str(note.get("title") or note.get("desc") or "")[:400],
                        "published_at": publication_time(note.get("time")), **note_metrics(note)}
        raise CheckError("小红书未返回对应笔记详情，可能需要登录或新的分享链接，待确认", category="detail")
    except TimeoutError as exc:
        raise CheckError("小红书读取超时，待确认", category="timeout") from exc
    except Error as exc:
        raise CheckError("小红书页面连接失败，待确认", category="transport") from exc
