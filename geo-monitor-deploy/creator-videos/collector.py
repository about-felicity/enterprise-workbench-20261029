from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import json
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit


POST = re.compile(r"/(note|video)/(\d{15,24})/?")
SHORT = re.compile(r"/[a-zA-Z0-9_-]{3,40}/?")
DOUYIN_SHARE_POST = re.compile(r"/share/(note|video)/(\d{15,24})/?")
URL = re.compile(r"https://[^\s<>，。；、\]\)]+")
XHS_HOSTS = {"www.xiaohongshu.com", "xiaohongshu.com", "m.xiaohongshu.com"}
XHS_SHORT_HOSTS = {"xhslink.com", "www.xhslink.com"}
XHS_POST = re.compile(r"/(?:explore|discovery/item)/([0-9a-fA-F]{24})/?")
XHS_SHORT = re.compile(r"/(?:[a-zA-Z]/)?[a-zA-Z0-9_-]{3,40}/?")
FIELDS = {
    "likes": "diggCount",
    "comments": "commentCount",
    "favorites": "collectCount",
    "shares": "shareCount",
}
PLAYER_COUNTERS = {
    "likes": "video-player-digg",
    "comments": "feed-comment-icon",
    "favorites": "video-player-collect",
    "shares": "video-player-share",
}
EMPTY_COUNTER_LABELS = {
    "likes": "赞",
    "comments": "抢首评",
    "favorites": "收藏",
    "shares": "分享",
}
VERIFICATION_TITLES = {"验证码中间页", "抖音安全验证", "安全验证 - 抖音"}
UNAVAILABLE = re.compile(
    r"(?:你要观看的|您要观看的|该)?(?:作品|视频|图文)(?:已被删除|已删除|不存在|已下架|已失效|已设为私密|仅作者可见|仅自己可见|已不可见)[。！!]?"
)
CHINA = timezone(timedelta(hours=8))


class CheckError(ValueError):
    def __init__(self, message, availability="unknown", *, category=None, retry_after=None, post_id=None, post_url=None):
        super().__init__(message)
        self.availability = availability
        self.category = category
        self.retry_after = retry_after
        self.post_id = post_id
        self.post_url = post_url


def rate_limit_error(response, label="抖音"):
    value = response.headers.get("retry-after", "").strip()
    try:
        if re.fullmatch(r"[0-9]{1,9}", value):
            seconds = int(value)
        else:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            seconds = retry_at.timestamp() - time.time()
    except (ValueError, TypeError, OverflowError, OSError):
        seconds = 0
    return CheckError(f"{label}限流，待恢复后核查", category="rate_limit", retry_after=max(60, seconds))


def canonical_link(value):
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme != "https":
        return None
    if parts.netloc == "v.douyin.com" and SHORT.fullmatch(parts.path):
        return f"https://v.douyin.com/{parts.path.strip('/')}/"
    post = POST.fullmatch(parts.path)
    if parts.netloc == "www.douyin.com" and post:
        return f"https://www.douyin.com/{post[1]}/{post[2]}"
    host = parts.netloc.lower()
    if host in XHS_SHORT_HOSTS and XHS_SHORT.fullmatch(parts.path):
        return f"https://xhslink.com/{parts.path.strip('/')}"
    note = XHS_POST.fullmatch(parts.path)
    if host in XHS_HOSTS and note:
        # Keep the share credentials needed to open a note. Tracking fields
        # are irrelevant and would give the same note multiple URL identities.
        query = dict(parse_qsl(parts.query, max_num_fields=100)) if parts.query.count("&") < 100 else {}
        share = {key: query[key] for key in ("xsec_token", "xsec_source") if query.get(key)}
        path = "discovery/item" if parts.path.startswith("/discovery/") else "explore"
        url = f"https://www.xiaohongshu.com/{path}/{note[1].lower()}"
        return f"{url}?{urlencode(share)}" if share else url
    return None


def links_from_text(text):
    text = re.sub(r"\\(?=[:/.?&=_-])", "", text)
    return list(dict.fromkeys(
        link for raw in URL.findall(text) if (link := canonical_link(raw.rstrip(".,;!?}'\"")))
    ))


def platform_from_link(link):
    return "xiaohongshu" if urlsplit(link).netloc.lower() in XHS_HOSTS | XHS_SHORT_HOSTS else "douyin"


def xhs_post_id(link):
    parts = urlsplit(link)
    note = XHS_POST.fullmatch(parts.path) if parts.netloc.lower() in XHS_HOSTS else None
    return note[1].lower() if note else None


def xhs_has_token(link):
    return urlsplit(link).query.startswith("xsec_token=")


def work_props(scripts, post_id):
    for script in scripts:
        script = script.lstrip()
        if not script.startswith("self.__pace_f.push("):
            continue
        try:
            chunk = json.JSONDecoder().raw_decode(script.removeprefix("self.__pace_f.push("))[0]
        except ValueError:
            continue
        if not isinstance(chunk, list) or len(chunk) < 2 or not isinstance(chunk[1], str):
            continue
        for line in chunk[1].splitlines():
            try:
                element = json.loads(line.partition(":")[2])
            except ValueError:
                continue
            if not isinstance(element, list) or len(element) != 4:
                continue
            props = element[3]
            if not isinstance(props, dict) or props.get("awemeId") != post_id:
                continue
            aweme = props.get("aweme")
            detail = aweme.get("detail") if isinstance(aweme, dict) else None
            if isinstance(detail, dict) and detail.get("awemeId") == post_id:
                return detail
    return {}


def video_detail_request(request):
    url = urlsplit(request.url)
    return url.netloc.endswith(".douyin.com") and url.path.rstrip("/") == "/aweme/v1/web/aweme/detail"


def work_metrics(props):
    stats = props.get("stats") or {}
    return {name: stats[key] for name, key in FIELDS.items()
            if type(stats.get(key)) is int and 0 <= stats[key] < 2**63}


def player_metrics(page, post_id):
    counts = page.evaluate(r"""({selectors, emptyLabels, postId}) => {
        const visible = (node) => node.getClientRects().length > 0 && getComputedStyle(node).visibility === 'visible';
        const controlsIn = (scope) => Object.entries(selectors).map(([name, selector]) =>
            [name, [...scope.querySelectorAll(`[data-e2e="${selector}"]`)].filter(visible)]);
        const countsFrom = (nodes) => Object.fromEntries(
            nodes.map(([name, [node]]) => [name, node.innerText.trim()]));
        const textCountsIn = (scope) => {
            const normalized = (text) => text.replace(/\s+/g, "");
            const title = normalized(document.title.replace(/ - 抖音$/, ""));
            if (title.length < 6) return {};
            const lines = scope.innerText.split("\n").map(line => line.trim()).filter(Boolean);
            const dates = lines.map((line, index) =>
                /^发布时间[：:]\s*\d{4}-\d\d-\d\d \d\d:\d\d(?::\d\d)?$/.test(line) ? index : -1
            ).filter(index => index >= 6);
            if (dates.length !== 1) return {};
            const date = dates[0];
            if (lines[date - 1] !== "举报" ||
                !normalized(lines.slice(0, date - 5).join("")).includes(title.slice(0, 48))) return {};
            const entries = Object.keys(selectors).map((name, index) => [name, lines[date - 5 + index]]);
            return entries.every(([name, value]) => value === emptyLabels[name] ||
                /^[0-9][0-9,]*(?:\.\d+)?[万亿]?\+?$/.test(value)) ? Object.fromEntries(entries) : {};
        };
        const details = [...document.querySelectorAll('[data-e2e="video-detail"]')];
        const matchingDetails = details.filter(scope =>
            scope.querySelector(`[data-e2e="player-container"].video_${postId}`));
        if (matchingDetails.length === 1) {
            const nodes = controlsIn(matchingDetails[0]);
            if (nodes.every(([, controls]) => controls.length === 1)) return countsFrom(nodes);
            const textCounts = textCountsIn(matchingDetails[0]);
            if (Object.keys(textCounts).length) return textCounts;
        }
        const playerNodes = [...document.querySelectorAll('[data-xgplayerid]')].filter(visible);
        const players = playerNodes.filter(player => {
            const container = player.closest('[data-e2e="player-container"]');
            const knownId = [...(container?.classList || [])].find(name => /^video_\d+$/.test(name));
            return (!knownId || knownId === `video_${postId}`) &&
                !playerNodes.some(other => other !== player && other.contains(player));
        });
        const matches = [];
        for (const player of players) {
            let scope = player;
            for (let depth = 0; depth < 3 && scope && scope !== document.body; depth++, scope = scope.parentElement) {
                if (players.some(other => other !== player && scope.contains(other))) break;
                const nodes = controlsIn(scope);
                if (nodes.some(([, controls]) => controls.length > 1)) break;
                if (nodes.every(([, controls]) => controls.length === 1)) {
                    matches.push(countsFrom(nodes));
                    break;
                }
            }
        }
        return matches.length === 1 ? matches[0] : {};
    }""", {"selectors": PLAYER_COUNTERS, "emptyLabels": EMPTY_COUNTER_LABELS, "postId": post_id})
    return parse_player_metrics(counts)


def parse_player_metrics(counts):
    if not isinstance(counts, dict):
        return {}, {}
    metrics, labels = {}, {}
    for name in PLAYER_COUNTERS:
        label = counts.get(name, "")
        if label == EMPTY_COUNTER_LABELS[name]:
            metrics[name] = 0
            continue
        match = re.fullmatch(r"(\d{1,15}(?:\.\d{1,4})?)\s*([万亿]?)\s*(\+?)", label.replace(",", ""))
        if match:
            number, unit, plus = match.groups()
            value = Decimal(number) * {"": 1, "万": 10_000, "亿": 100_000_000}[unit]
            if value == value.to_integral_value() and 0 <= value < 2**53:
                metrics[name] = int(value)
                if unit or plus:
                    labels[name] = label
    return metrics, labels


def publication_time(value):
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,13}", value):
        value = int(value)
    if type(value) is not int or not 0 < value < 10**13:
        return None
    if value >= 10**12:
        value //= 1000
    if value >= 10**10:
        return None
    return datetime.fromtimestamp(value, CHINA).isoformat(timespec="seconds")


def video_props(page, requests, post_id):
    from playwright.sync_api import Error, TimeoutError

    deadline = time.monotonic() + 12
    read = 0
    fallback = {}
    while (remaining := deadline - time.monotonic()) > 0:
        if read == len(requests):
            try:
                page.wait_for_event("requestfinished", predicate=video_detail_request,
                                    timeout=max(1, int(remaining * 1000)))
            except TimeoutError:
                break
            continue
        response = requests[read].response()
        read += 1
        if not response:
            continue
        if response.status == 429:
            raise rate_limit_error(response)
        try:
            payload = response.json()
        except (Error, ValueError):
            continue
        detail = payload.get("aweme_detail") if isinstance(payload, dict) else None
        if not isinstance(detail, dict) or detail.get("aweme_id") != post_id:
            continue
        stats = detail.get("statistics") or {}
        status = detail.get("status") or {}
        props = {
            "desc": detail.get("desc"), "authorInfo": detail.get("author"),
            "video": detail.get("video"),
            "createTime": detail.get("create_time"),
            "stats": {
                "diggCount": stats.get("digg_count"), "commentCount": stats.get("comment_count"),
                "collectCount": stats.get("collect_count"), "shareCount": stats.get("share_count"),
            },
            "status": {"isDelete": status.get("is_delete"), "isPrivate": status.get("is_private")},
        }
        if status.get("is_delete") is True or status.get("is_private") is True or len(work_metrics(props)) == len(FIELDS):
            return props
        if props["video"]:
            fallback = props
    return fallback


def post_from_url(url):
    return POST.fullmatch(urlsplit(canonical_link(url) or "").path)


def douyin_redirect(response):
    if response.status not in (301, 302, 303, 307, 308):
        return None
    target = response.headers.get("location", "")
    if post_from_url(target):
        return canonical_link(target)
    try:
        url = urlsplit(target)
    except ValueError:
        return None
    shared = DOUYIN_SHARE_POST.fullmatch(url.path)
    if url.scheme == "https" and url.netloc == "www.iesdouyin.com" and shared:
        return f"https://www.douyin.com/{shared[1]}/{shared[2]}"
    return None


def resolve_douyin_short(context, link):
    """Read the short link's first redirect without loading the destination page."""
    from playwright.sync_api import Error

    try:
        response = context.request.get(link, max_redirects=0, timeout=5000)
    except Error:
        return None
    try:
        if response.status == 429:
            raise rate_limit_error(response)
        return douyin_redirect(response)
    finally:
        response.dispose()


def dismiss_douyin_login(page):
    from playwright.sync_api import TimeoutError

    header = page.locator("#login-panel-new #douyin_login_comp_flat_panel_header:visible").filter(
        has_text="登录后免费畅享高清视频"
    )
    close = header.locator("div:has(> svg):visible")
    for attempt in range(2):
        if close.count() != 1:
            return bool(attempt and not header.is_visible())
        try:
            close.click(timeout=1500)
            header.wait_for(state="hidden", timeout=1500)
            return True
        except TimeoutError:
            continue
    return False


def snapshot(page, link, expected_post_id=None):
    if platform_from_link(link) == "xiaohongshu":
        from xiaohongshu import note_snapshot

        return note_snapshot(page, link, expected_post_id)
    from playwright.sync_api import Error, TimeoutError

    redirected_url = None
    if urlsplit(link).netloc == "v.douyin.com":
        def record_redirect(response):
            nonlocal redirected_url
            if canonical_link(response.url) != link or not response.request.is_navigation_request():
                return
            if response.request.frame != page.main_frame:
                return
            target = douyin_redirect(response)
            if target and (not expected_post_id or post_from_url(target)[2] == expected_post_id):
                redirected_url = target

        page.on("response", record_redirect)
    try:
        detail_requests = []
        page.on("requestfinished", lambda request: detail_requests.append(request) if video_detail_request(request) else None)
        response = page.goto(link, wait_until="commit", timeout=22000)
        if (response and response.status == 429
                and urlsplit(response.url).hostname in {"www.douyin.com", "v.douyin.com"}):
            raise rate_limit_error(response)
        post = post_from_url(page.url)
        if not post:
            try:
                page.wait_for_url(lambda url: post_from_url(url) is not None, wait_until="commit", timeout=5000)
            except TimeoutError as exc:
                raise CheckError("抖音页面暂未定位到作品，待确认", category="navigation") from exc
            post = post_from_url(page.url)
            if not post:
                raise CheckError("抖音页面暂未定位到作品，待确认", category="navigation")
        final = canonical_link(page.url)
        requested_post = post_from_url(redirected_url or link)
        expected_post_id = expected_post_id or (requested_post[2] if requested_post else None)
        if expected_post_id and post[2] != expected_post_id:
            raise CheckError("抖音跳转到其他作品，待确认", category="navigation")
        if response and canonical_link(response.url) == final and response.status >= 400:
            message = f"抖音作品页返回 HTTP {response.status}"
            if response.status in (404, 410):
                raise CheckError(message, "unavailable", category="page_unavailable", post_id=post[2])
            category = "transport" if response.status >= 500 or response.status == 403 else None
            raise CheckError(f"{message}，待确认", category=category)
        try:
            page.locator("body").wait_for(state="attached", timeout=7000)
        except TimeoutError as exc:
            raise CheckError("抖音已响应，作品正文加载超时，待复查", category="timeout") from exc
        dismiss_douyin_login(page)
        page_title = page.title().strip()
        script_selector = "script:not([src])"
        read_scripts = "(nodes) => nodes.map(n => n.textContent.trimStart()).filter(s => s.startsWith('self.__pace_f.push(') && s.includes('awemeId'))"
        props = work_props(page.locator(script_selector).evaluate_all(read_scripts), post[2])
        if len(work_metrics(props)) != len(FIELDS) and page_title not in VERIFICATION_TITLES:
            try:
                page.get_by_text(UNAVAILABLE).or_(page.locator('[data-e2e="video-player-digg"]')).first.wait_for(timeout=8000)
            except TimeoutError:
                pass
            dismiss_douyin_login(page)
            props = work_props(page.locator(script_selector).evaluate_all(read_scripts), post[2]) or props
            page_title = page.title().strip()
        metrics = work_metrics(props)
        visible, labels = player_metrics(page, post[2]) if len(metrics) != len(FIELDS) else ({}, {})
        if page_title in VERIFICATION_TITLES and not props and len(visible) != len(FIELDS):
            raise CheckError("抖音要求安全验证，互动数据待复查", category="verification", post_id=post[2], post_url=final)
        if (not props and len(visible) != len(FIELDS) and (post[1] == "video" or detail_requests)):
            props = video_props(page, detail_requests, post[2])
            metrics = work_metrics(props)
            if len(metrics) != len(FIELDS):
                dismiss_douyin_login(page)
                visible, labels = player_metrics(page, post[2])
        if any(key not in metrics and key not in visible for key in FIELDS):
            labels = {}
        else:
            labels = {key: label for key, label in labels.items() if key not in metrics}
            metrics = {**visible, **metrics}
        current = post_from_url(page.url)
        if not current or current[2] != post[2]:
            raise CheckError("抖音跳转到其他作品，待确认", category="navigation")
        status = props.get("status") or {}
        if status.get("isDelete") is True or status.get("isDeleted") is True:
            raise CheckError("抖音返回作品已删除", "unavailable")
        if props.get("isPrivate") is True or status.get("isPrivate") is True:
            raise CheckError("抖音返回作品为私密", "unavailable")
        if len(metrics) != len(FIELDS):
            if not (props.get("video") or props.get("images")):
                body = page.locator("body").inner_text(timeout=4000)
                for line in body.splitlines():
                    if UNAVAILABLE.fullmatch(line.strip()):
                        raise CheckError(line.strip(), "unavailable", category="page_unavailable", post_id=post[2])
                raise CheckError("抖音未返回作品详情，待确认", category="detail")
            metrics = {}
        author = props.get("authorInfo") or {}
        account = author.get("uniqueId") or author.get("unique_id") or author.get("shortId") or author.get("short_id")
        uid = author.get("uid")
        title = props.get("desc") or (page_title.removesuffix(" - 抖音") if page_title not in VERIFICATION_TITLES else "")
        return {
            "post_id": post[2], "url": final, "title": title[:400],
            "published_at": publication_time(props.get("createTime")),
            "author": (author.get("nickname") or "")[:100],
            "creator_id": str(account)[:100] if account and str(account) != "0" else None,
            "creator_uid": str(uid)[:100] if uid and str(uid) != "0" else None,
            **({"metric_labels": labels} if labels else {}),
            **metrics,
        }
    except CheckError as exc:
        if not exc.post_url:
            exc.post_url = redirected_url
        raise
    except TimeoutError as exc:
        raise CheckError("无头浏览器读取超时，待确认", category="timeout", post_url=redirected_url) from exc
    except Error as exc:
        network_error = re.search(r"\bnet::(ERR_[A-Z0-9_]+)\b", str(exc).partition("\n")[0])
        if network_error:
            raise CheckError(f"抖音页面连接失败（{network_error[1]}），待确认", category="transport", post_url=redirected_url) from exc
        raise CheckError("无头浏览器读取失败，待确认", category="transport", post_url=redirected_url) from exc
