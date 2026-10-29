from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable
from urllib.parse import urlsplit

from geo_source_cards.session_watch import LoginRequiredError, SessionReporter

from .browser import SitePage, launch_browser, session_cookies, storage_env_name
from .config import SiteConfig, site_config

_PROVIDER_NAVIGATION_MARKER = re.compile(
    r"^(?:近期对话|最近对话|历史对话|全部对话|对话历史|我的对话|"
    r"历史会话|最近会话|我的会话|新对话|新建对话|新会话|新建会话|"
    r"recent\s+chats?|chat\s+history|new\s+chat)\s*$",
    re.I,
)


class PreSubmissionPageError(RuntimeError):
    """Readiness failed before any question could be submitted."""


def _clean_answer_body(question: str, body: str) -> str:
    question_key = re.sub(r"\s+", "", str(question or "")).casefold()
    output: list[str] = []
    skip_prompt_after_role = False
    for raw_line in str(body or "").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if _PROVIDER_NAVIGATION_MARKER.fullmatch(line):
            break
        line_key = re.sub(r"\s+", "", line).casefold()
        if not output and line_key in {"用户", "user"}:
            skip_prompt_after_role = True
            continue
        if skip_prompt_after_role and question_key and line_key == question_key:
            skip_prompt_after_role = False
            continue
        if not output and line_key in {"助手", "assistant"}:
            continue
        if not output and question_key and line_key == question_key:
            continue
        output.append(line)
    return "\n".join(output).strip()


def _js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def conversation_id(url: str) -> str:
    parsed = urlsplit(str(url or ""))
    match = re.fullmatch(r"/a/chat/s/([a-zA-Z0-9_-]+)", parsed.path)
    return match[1] if parsed.hostname == "chat.deepseek.com" and match else ""


class BrowserCollector:
    def __init__(self, model: str, *, headless: bool = True):
        self.site: SiteConfig = site_config(model)
        self.browser = launch_browser(self.site, headless=headless)
        self.session_reporter = SessionReporter()
        self._next_session_check = 0.0
        self._last_session_save = 0.0
        try:
            self.page = SitePage(self.site)
            self.page.call("Page.enable")
            self.page.call("Runtime.enable")
            if self.site.id == 'deepseek':
                from .session_store import restore
                restore(self.page)
            raw_storage = str(
                os.environ.get(storage_env_name(self.site.id)) or ""
            ).strip()
            if raw_storage:
                # A freshly launched tab can still be about:blank or its error page.
                # Wait for the provider origin before accessing origin-bound storage.
                self.page.call("Page.navigate", {"url": self.site.home_url})
                storage_deadline = time.monotonic() + 30
                while time.monotonic() < storage_deadline:
                    if (
                        self.page.evaluate("location.origin")
                        == "https://chat.deepseek.com"
                    ):
                        break
                    time.sleep(0.25)
                else:
                    raise RuntimeError(
                        "DeepSeek origin did not load before session migration"
                    )
                try:
                    storage = json.loads(raw_storage)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"{storage_env_name(self.site.id)} 不是有效的 JSON"
                    ) from exc
                if isinstance(storage, dict):
                    self.page.evaluate(rf"""
(()=>{{
  const state={_js(storage)};
  for(const [key,value] of Object.entries(state.local_storage||{{}}))localStorage.setItem(key,String(value));
  for(const [key,value] of Object.entries(state.session_storage||{{}}))sessionStorage.setItem(key,String(value));
  return true;
}})()
""")
            cookies = session_cookies(self.site)
            # DeepSeek uses a dedicated persistent local profile so a
            # successful manual login survives worker/browser restarts.  Their
            # readiness is proved from the live page below; an exported cookie
            # environment variable is only required for incognito collectors.
            self.has_session_cookies = bool(cookies) or self.site.id == "deepseek"
            if self.has_session_cookies:
                self.page.call("Network.enable")
                self.page.call("Network.setCookies", {"cookies": cookies})
        except Exception:
            self.browser.close()
            raise

    def close(self) -> None:
        try:
            if self.site.id == 'deepseek' and self.page.ws is not None:
                try:
                    state=self.session_status()
                    if state.get('ok'):
                        from .session_store import checkpoint
                        checkpoint(self.page)
                except Exception:
                    pass  # Browser shutdown must still complete; periodic checkpoint remains.
            if self.page.ws is not None:
                self.page.ws.close()
                self.page.ws = None
        finally:
            self.browser.close()

    def navigate_home(self) -> None:
        self.page.call("Page.navigate", {"url": self.site.home_url}, timeout=30)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = self.page.evaluate("document.readyState")
            if state in {"interactive", "complete"}:
                return
            time.sleep(0.5)
        raise TimeoutError(f"{self.site.name} 网页加载超时")

    def _input_state(self, *, focus: bool = True) -> dict[str, Any]:
        return (
            self.page.evaluate(rf"""
(()=>{{
  const selectors={_js(self.site.input_selectors)};
  const shouldFocus={_js(focus)};
  const visible=(el)=>{{if(el===document)return true;if(!el?.getBoundingClientRect)return false;const r=el.getBoundingClientRect();const s=getComputedStyle(el);return r.width>8&&r.height>8&&s.display!=='none'&&s.visibility!=='hidden';}};
  for(const selector of selectors){{
    for(const el of document.querySelectorAll(selector)){{
      if(!visible(el)||el.disabled||el.getAttribute('aria-disabled')==='true')continue;
      const r=el.getBoundingClientRect();
      if(shouldFocus){{el.scrollIntoView({{block:'center'}});el.focus();}}
      return {{ok:true,tag:el.tagName,url:location.href,x:r.left+r.width/2,y:r.top+r.height/2}};
    }}
  }}
  return {{ok:false,url:location.href,title:document.title,text:String(document.body?.innerText||'').slice(0,1000)}};
}})()
""")
            or {}
        )

    def session_status(self) -> dict[str, Any]:
        """Observe authentication controls without navigating or stealing focus."""
        state = (
            self.page.evaluate(rf"""
(()=>{{
 const visible=e=>{{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'}};
 const selectors={_js(self.site.input_selectors)};
 const hosts={_js(self.site.internal_hosts)};
 const hostOk=hosts.some(h=>location.hostname===h||location.hostname.endsWith('.'+h));
 const loginPath=/\/(?:login|sign[-_]?in|auth)(?:\/|$)/i.test(location.pathname);
 const controls=[...document.querySelectorAll('button,[role=button],[role=dialog] a,a[href*="/login"]')];
 const loginControl=controls.some(e=>visible(e)&&!e.closest('.ds-markdown,article')&&
   /^(登录|立即登录|重新登录|登录\/注册|Sign in|Log in|Sign in to DeepSeek)$/i.test(String(e.innerText||e.getAttribute('aria-label')||'').trim()));
 const composer=[...document.querySelectorAll('textarea,[contenteditable=true]')].some(visible)||selectors.some(s=>[...document.querySelectorAll(s)].some(visible));
 return {{hostOk,loginRequired:hostOk&&(loginPath||loginControl),composer,readyState:document.readyState}};
}})()
""")
            or {}
        )
        if state.get("loginRequired"):
            if self.site.id == 'deepseek':
                from .session_store import invalidate
                invalidate()
            return {
                "ok": False,
                "status": "login_required",
                "message": "检测到 DeepSeek 登录入口，请重新登录",
            }
        if (
            state.get("hostOk")
            and state.get("composer")
            and state.get("readyState") == "complete"
        ):
            if self.site.id == 'deepseek' and time.monotonic()-getattr(self,'_last_session_save',0)>60:
                from .session_store import checkpoint
                checkpoint(self.page)
                self._last_session_save=time.monotonic()
            return {"ok": True, "status": "ready", "message": "DeepSeek 网页会话可用"}
        return {
            "ok": False,
            "status": "unknown",
            "message": "页面未就绪或输入区不可用，无法核验登录状态",
        }

    def assert_session(self) -> None:
        state = self.session_status()
        self.session_reporter.publish(state)
        self._next_session_check = time.monotonic() + 60
        if state["status"] == "login_required":
            raise LoginRequiredError(state["message"])
        if not state["ok"]:
            raise RuntimeError(state["message"])

    def _probe_session_if_due(self) -> None:
        if time.monotonic() >= self._next_session_check:
            self.assert_session()

    def check_ready(self) -> dict[str, Any]:
        if not self.has_session_cookies:
            from .browser import cookie_env_name

            return {
                "ok": False,
                "status": "login_required",
                "message": f"隐身会话需要临时设置 {cookie_env_name(self.site.id)}",
                "web": {},
                "location": "local",
            }
        state = {"ok": False, "status": "unknown", "message": "页面未就绪"}
        # Retry only the idle login/readiness page, never a submitted question.
        for attempt in range(3):
            self.navigate_home()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                state = self.session_status()
                if state["status"] in {"ready", "login_required"}:
                    break
                time.sleep(1)
            if state["status"] in {"ready", "login_required"}:
                break
            if attempt < 2:
                time.sleep(2)
        self.session_reporter.publish(state)
        return state

    def wait_for_login_cookies(
        self, *, timeout: int = 600, progress: Callable[[str], None] | None = None
    ) -> list[dict[str, Any]]:
        """Wait for a manual login and return cookies without persisting them."""
        self.page.call("Network.enable")
        self.navigate_home()
        time.sleep(1.5)

        def cookies() -> list[dict[str, Any]]:
            payload = self.page.call("Network.getAllCookies") or {}
            values = payload.get("cookies") if isinstance(payload, dict) else []
            output = []
            for item in values or []:
                if not isinstance(item, dict) or not str(item.get("name") or ""):
                    continue
                output.append(
                    {
                        key: item[key]
                        for key in (
                            "name",
                            "value",
                            "domain",
                            "path",
                            "secure",
                            "httpOnly",
                            "expires",
                            "sameSite",
                        )
                        if key in item
                    }
                )
            return output

        deadline = time.monotonic() + max(30, timeout)
        next_progress = 0.0
        consecutive_ready = 0
        while time.monotonic() < deadline:
            # Never steal focus from phone/code fields in the active login dialog.
            state = self.session_status()
            current = cookies()
            consecutive_ready = (
                consecutive_ready + 1 if state.get("ok") and current else 0
            )
            if consecutive_ready >= 2:
                self.session_reporter.publish(state)
                return current
            moment = time.monotonic()
            if progress and moment >= next_progress:
                remaining = max(0, int(deadline - moment))
                progress(
                    f"等待你在本机 {self.site.name} 隐身窗口完成登录（剩余 {remaining} 秒）"
                )
                next_progress = moment + 3
            time.sleep(1)
        raise TimeoutError(f"{self.site.name} 登录等待超时，请重新发起登录")

    def _snapshot(self) -> dict[str, Any]:
        return (
            self.page.evaluate(rf"""
(()=>{{
  const siteId={_js(self.site.id)};
  const selectors={_js(self.site.answer_selectors)};
  const internal={_js(self.site.internal_hosts)};
  const visible=(el)=>{{if(el===document)return true;if(!el?.getBoundingClientRect)return false;const r=el.getBoundingClientRect();const s=getComputedStyle(el);if(s.display==='none'||s.visibility==='hidden')return false;if(s.display==='contents')return [...el.children].some(visible);return r.width>8&&r.height>8;}};
  let nodes=[];
  if(!nodes.length)for(const selector of selectors)nodes.push(...document.querySelectorAll(selector));
  nodes=[...new Set(nodes)].filter(el=>visible(el)&&String(el.innerText||'').trim().length>=20);
  if(!nodes.length)nodes=[...document.querySelectorAll('main article, main [class*=answer], main [class*=markdown], main [class*=message]')].filter(el=>visible(el)&&String(el.innerText||'').trim().length>=20);
  const node=nodes[nodes.length-1]||null;
  let body=String(node?.innerText||'').replace(/\n{{3,}}/g,'\n\n').trim();
  if(siteId==='deepseek'){{
    // DeepSeek can render one answer as several sibling `.ds-markdown`
    // fragments. Taking only the last fragment silently saved a short closing
    // tip while discarding the main answer. A diagnosis opens a fresh chat, so
    // all visible final-answer fragments belong to the current response.
    const fragments=[...document.querySelectorAll('.ds-markdown,[class*=ds-markdown]')]
      .filter(el=>visible(el)&&String(el.innerText||'').trim().length>0);
    const unique=[];
    for(const fragment of fragments){{
      const text=String(fragment.innerText||'').replace(/\n{{3,}}/g,'\n\n').trim();
      if(text&&!unique.some(value=>value===text||value.includes(text)))unique.push(text);
    }}
    if(unique.length)body=unique.join('\n\n');
  }}
  const bodyRaw=body;
  if(siteId==='deepseek'){{
    const render=n=>{{
      if(n.nodeType===3)return n.textContent||'';
      if(n.nodeType!==1)return '';
      if(n.matches('.ds-markdown-cite')){{const number=String(n.textContent||'').replace(/[^0-9]/g,'');return /^\d{{1,3}}$/.test(number)?'['+number+']':'';}}
      const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return '';
      if(n.tagName==='BR')return '\n';
      const content=[...n.childNodes].map(render).join('');
      return /^(P|DIV|LI|H[1-6]|TR|UL|OL|BLOCKQUOTE)$/.test(n.tagName)?'\n'+content+'\n':content;
    }};
    const roots=[...document.querySelectorAll('.ds-markdown')].filter(e=>visible(e)&&!e.parentElement?.closest('.ds-markdown'));
    const rendered=roots.map(e=>render(e).replace(/\n{{3,}}/g,'\n\n').trim()).filter(e=>e.length>0);
    if(rendered.length)body=[...new Set(rendered)].join('\n\n');
  }}
  const scope=node?.closest('[class*=message],[class*=answer],[class*=assistant],article')||node||document.querySelector('main')||document;
  const scopes=[scope,...document.querySelectorAll('[role=dialog],[class*=popover],[class*=tooltip]')].filter(visible);
  const anchors=scopes.flatMap(el=>[...el.querySelectorAll('a[href],a[data-href],a[data-url]')]);
  if(siteId==='deepseek')anchors.push(...[...document.querySelectorAll('a[href]')].filter(a=>visible(a)&&!a.closest('nav,header,footer,[role=navigation]')));
  for(const card of scope.querySelectorAll('[class*=source],[class*=citation],[class*=reference],[data-testid*=source],[data-testid*=citation]')){{
    anchors.push(...card.querySelectorAll('a[href],a[data-href],a[data-url]'));
  }}
  const seen=new Set(),sources=[],sourceEntries=[];
  for(const a of anchors){{
    try{{
      let raw=a.getAttribute('data-url')||a.getAttribute('data-href')||a.getAttribute('href')||a.href;
      let u=new URL(raw,location.href);
      for(let depth=0;depth<3;depth++){{
        const host=u.hostname.replace(/^www\./,'').toLowerCase();
        if(!internal.some(x=>host===x||host.endsWith('.'+x)))break;
        const target=['url','target','redirect','redirect_url','dest','destination'].map(k=>u.searchParams.get(k)).find(Boolean);
        if(!target)break;
        try{{u=new URL(decodeURIComponent(target),location.href);}}catch{{break;}}
      }}
      const host=u.hostname.replace(/^www\./,'').toLowerCase();
      if(!/^https?:$/.test(u.protocol)||internal.some(x=>host===x||host.endsWith('.'+x)))continue;
      u.hash='';
      let title=String(a.innerText||a.title||a.getAttribute('aria-label')||host).replace(/\s+/g,' ').trim();
      if(String(a.innerText||'').length>30){{
        const entry=String(a.innerText||'').split('\n').map(s=>s.trim()).find(s=>/^\d{{1,3}}$/.test(s));
        if(entry&&!sourceEntries.some(s=>s.index===Number(entry)))sourceEntries.push({{index:Number(entry),url:u.href}});
      }}
      if(!title||/^[-–—\s]*\d+$/.test(title)||(a.querySelector('.ds-markdown-cite')&&title.length<20))title=host;
      if(!title)continue;
      if(seen.has(u.href)){{const old=sources.find(s=>s.url===u.href);if(old&&old.title===host&&title!==host)old.title=title;continue;}}
      seen.add(u.href);sources.push({{title,url:u.href,href:u.href}});
    }}catch{{}}
  }}
  const text=String(document.body?.innerText||'');
  const busy=[...document.querySelectorAll('button,[role=button]')].some(el=>visible(el)&&
    [el.innerText,el.getAttribute('aria-label'),el.getAttribute('title'),el.getAttribute('data-tooltip')]
      .some(label=>/^(停止生成|停止回答|Stop generating|Stop response)$/i.test(String(label||'').trim())));
  // An answer discussing rate limits is not a provider failure. Only system
  // alerts/toasts outside the answer contribute to this error signal.
  const alerts=[...document.querySelectorAll('[role=alert],.ds-toast,.ds-message--error')]
    .filter(el=>visible(el)&&!el.closest('.ds-markdown')).map(el=>el.innerText||'').join('\n');
  const providerError=/请求过于频繁|服务繁忙|服务器繁忙|Rate limit|Server busy/i.test(alerts)
    ? 'DeepSeek service is busy or rate limited' : '';
  return {{url:location.href,title:document.title,body,bodyRaw,busy,providerError,readyState:document.readyState,sources,sourceEntries,pageText:text.slice(-3000)}};
}})()
""")
            or {}
        )

    def _submit(self, question: str) -> None:
        self.assert_session()
        state = self._input_state()
        if not state.get("ok"):
            raise RuntimeError(
                f"{self.site.name} 网页没有找到可用输入框，请先登录或更新网页适配器"
            )
        self.page.call(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": "a", "code": "KeyA", "modifiers": 2},
        )
        self.page.call(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "a", "code": "KeyA", "modifiers": 2},
        )
        self.page.call(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": "Backspace", "code": "Backspace"},
        )
        self.page.call(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "Backspace", "code": "Backspace"},
        )
        self.page.call("Input.insertText", {"text": question})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            control = self._send_state()
            if control.get('text') == question and control.get('button'):
                break
            time.sleep(0.5)
        else:
            raise PreSubmissionPageError('输入内容或发送按钮尚未就绪，问题未发送')
        self.assert_session()
        if getattr(self, "before_send", None):
            self.before_send()
        # Input auto-sizing / composer hydration can move the send button after
        # insertText. Re-read its position after settling, rather than clicking
        # a stale point. This is still before the sole send attempt.
        time.sleep(1.0)
        control = self._send_state()
        if control.get('text') != question or not control.get('button'):
            raise PreSubmissionPageError('发送前输入或按钮发生变化，问题未发送')
        self._save_failure_evidence(question, 'before_single_send_click', control)
        if getattr(self,'on_send_intent',None):self.on_send_intent(control)
        self.submission_started = True
        point = control['button']
        self.page.click(int(point['x']), int(point['y']))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            receipt = self._send_state()
            if (conversation_id(receipt.get('url', '')) and not receipt.get('text')
                    and question in receipt.get('conversationText', '')):
                if getattr(self,'on_send_receipt',None):self.on_send_receipt(receipt)
                return
            time.sleep(0.5)
        self._save_failure_evidence(question, 'submission_unconfirmed', receipt)
        raise RuntimeError('未确认 DeepSeek 接收问题；已保存发送状态，禁止自动重发')

    def _send_state(self) -> dict[str, Any]:
        return self.page.evaluate(r"""(()=>{
          const visible=e=>{const r=e.getBoundingClientRect();return r.width>8&&r.height>8};
          const input=[...document.querySelectorAll('textarea')].find(visible);
          const buttons=[...document.querySelectorAll('[role=button].ds-button--primary.ds-button--filled.ds-button--circle')]
            .filter(e=>visible(e)&&!e.classList.contains('ds-button--disabled')&&e.getAttribute('aria-disabled')!=='true');
          const r=buttons.length===1?buttons[0].getBoundingClientRect():null;
          const root=(document.querySelector('.layout-content-main')||document.querySelector('main')||document.body).cloneNode(true);
          root.querySelectorAll('textarea,input,[contenteditable],nav,aside').forEach(e=>e.remove());
          return {url:location.href,text:input?.value||'',button:r?{x:r.x+r.width/2,y:r.y+r.height/2}:null,conversationText:String(root.textContent||'').slice(-20000)};
        })()""") or {}

    def _save_failure_evidence(self, question, phase, snapshot):
        if getattr(self,'submission_started',False) and getattr(self,'on_send_receipt',None):
            self.on_send_receipt(snapshot)
        from geo_source_cards.runtime import runtime_root, atomic_json
        atomic_json(runtime_root() / 'diagnostics' / f'deepseek-{time.time_ns()}.json',
                    {'question': question, 'phase': phase, 'snapshot': snapshot,
                     'submission_started': getattr(self, 'submission_started', False)})

    def _wait_current_answer(
        self,
        question: str,
        *,
        timeout: int,
        stable_seconds: int,
        baseline_body: str = "",
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(30, timeout)
        stable_since: float | None = None
        previous = ""
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            time.sleep(1.5)
            self._probe_session_if_due()
            last = self._snapshot()
            if last.get("providerError"):
                raise RuntimeError(str(last["providerError"]))
            body = str(last.get("body") or "").strip()
            changed = bool(body and body != baseline_body)
            current_text = str(
                self.page.evaluate(
                    "(()=>{const root=(document.querySelector('.layout-content-main')||document.querySelector('main')||document.body).cloneNode(true);root.querySelectorAll('textarea,input,[contenteditable],nav,aside').forEach(e=>e.remove());return String(root.textContent||'').slice(-20000)})()"
                )
                or ""
            )
            question_seen = " ".join(question.split()) in " ".join(current_text.split())
            if (
                changed
                and question_seen
                and not last.get("busy")
                and last.get("readyState") == "complete"
            ):
                current = time.monotonic()
                stable_since = (
                    (stable_since or current) if body == previous else current
                )
                if body == previous and current - stable_since >= stable_seconds:
                    return last
            else:
                stable_since = None
            previous = body
        self._save_failure_evidence(question, 'answer_timeout', last)
        raise TimeoutError(
            f"{self.site.name} 回答等待超时：正文 {len(str(last.get('body') or ''))} 字"
        )

    def _capture_result(self, last: dict[str, Any], question: str) -> dict[str, Any]:
        body = _clean_answer_body(question, str(last.get("body") or ""))
        if not body.strip():
            raise RuntimeError(f"{self.site.name} 未抓到完整回答正文，请核对任务状态")
        sources = [
            item
            for item in last.get("sources") or []
            if isinstance(item, dict)
            and str(item.get("url") or item.get("href") or "").startswith(
                ("http://", "https://")
            )
        ]
        expected = last.get("expected_source_count")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
            expected = None
        entries = last.get("sourceEntries") or []
        indexes = {e.get("index") for e in entries if isinstance(e, dict)}
        complete = (
            (
                set(range(1, expected + 1)).issubset(indexes)
                if indexes
                else len(sources) >= expected
            )
            if expected is not None
            else None
        )
        return {
            "body": body,
            "body_raw": str(last.get("bodyRaw") or body),
            "sources": sources,
            "url": str(last.get("url") or ""),
            "expected_source_count": expected,
            "source_entries": entries,
            "source_capture_complete": complete,
            "source_capture_status": (
                "unknown"
                if complete is None
                else "complete"
                if complete
                else "incomplete"
            ),
            "body_capture_complete": True,
            "completion_evidence": "current_question_present_and_dom_stable",
            "capture_mode": "deepseek_web",
        }

    def _wait_answer_with_refresh(self, question, **kwargs):
        try:
            return self._wait_current_answer(question, **kwargs)
        except TimeoutError:
            # Refresh only an identified submitted conversation, never the home
            # page. This retries reading the answer, not sending the question.
            state = self._send_state()
            identity = conversation_id(state.get('url', ''))
            if not identity or question not in state.get('conversationText', ''):
                raise
            self._save_failure_evidence(question, 'refresh_original_conversation', state)
            if os.environ.get('GEO_PIPELINE_ROOT'):
                from geo_source_cards.pipeline_control import event
                event(os.environ['GEO_PIPELINE_ROOT'], 'capture',
                      '回答等待超时，刷新原会话后补读一次；不会重复发送问题',
                      model='deepseek', question=question)
            self.page.call('Page.reload', {}, timeout=30)
            time.sleep(2)
            result = self._wait_current_answer(question, **kwargs)
            if conversation_id(result.get('url', '')) != identity:
                raise RuntimeError('刷新后会话发生变化，拒绝保存其他会话的回答')
            return result

    def _start_fresh_chat(self) -> dict[str, Any]:
        point = self.page.evaluate(r"""
(()=>{
 const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
 const button=[...document.querySelectorAll('button,[role=button]')].find(e=>
   visible(e)&&/^(新对话|开启新对话|新建对话|New chat)$/i.test(String(e.innerText||e.getAttribute('aria-label')||'').trim()));
 if(!button)return null;const r=button.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
})()
""")
        if point:
            self.page.click(int(point["x"]), int(point["y"]))
            time.sleep(0.8)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            snapshot = self._snapshot()
            parsed = urlsplit(str(snapshot.get("url") or ""))
            if (
                parsed.hostname == "chat.deepseek.com"
                and parsed.path == "/"
                and not parsed.query
                and snapshot.get("readyState") == "complete"
                and not snapshot.get("body")
                and not snapshot.get("busy")
            ):
                return {
                    "empty_chat_url": snapshot["url"],
                    "verified_epoch": time.time(),
                }
            time.sleep(0.5)
        raise RuntimeError(
            "Cannot confirm a fresh DeepSeek conversation; question was not sent"
        )

    def _expand_source_panel(self) -> int | None:
        point = self.page.evaluate(r"""
(()=>{
 const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
 for(const e of document.querySelectorAll('button,[role=button],span')){
   if(!visible(e))continue;const text=String(e.innerText||e.getAttribute('aria-label')||'').trim();
   const match=text.match(/(?:搜索到|已搜索|参考|来源)\s*(\d+)\s*(?:个|篇|条)?\s*(?:网页|资料|来源|信源)|(?:Found\s+)?(\d+)\s+web\s+pages/i);
   if(match&&text.length<100){e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
     const opened=[...document.querySelectorAll('a[href]')].some(a=>String(a.innerText||'').length>30&&String(a.innerText||'').split('\n').some(line=>/^\d{1,3}$/.test(line.trim())));
     return {x:r.x+r.width/2,y:r.y+r.height/2,count:Number(match[1]||match[2]),opened};}
 }return null;
})()
""")
        if not point:
            return None
        if point.get("opened"):
            return int(point["count"])
        self.page.click(int(point["x"]), int(point["y"]))
        time.sleep(1)
        return int(point["count"])

    def _ensure_search_enabled(self) -> None:
        expression = r"""(()=>{
          const controls=[...document.querySelectorAll('[aria-pressed]')].filter(e=>/^(智能搜索|联网搜索|Search)$/.test(String(e.innerText||'').trim()));
          const e=controls.find(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});
          if(!e)return null;const r=e.getBoundingClientRect();return {selected:e.getAttribute('aria-pressed')==='true',x:r.x+r.width/2,y:r.y+r.height/2};
        })()"""
        control = self.page.evaluate(expression)
        if not control:
            raise RuntimeError(
                "Cannot verify DeepSeek search control; question was not sent"
            )
        if not control["selected"]:
            self.page.click(int(control["x"]), int(control["y"]))
            time.sleep(0.5)
            control = self.page.evaluate(expression)
            if not control or not control["selected"]:
                raise RuntimeError(
                    "DeepSeek search did not enable; question was not sent"
                )

    def collect(
        self, question: str, *, timeout: int = 240, stable_seconds: int = 6
    ) -> dict[str, Any]:
        self.submission_started = False
        ready = self.check_ready()
        if not ready.get("ok"):
            if ready.get("status") == "login_required":
                raise LoginRequiredError(str(ready["message"]))
            raise PreSubmissionPageError(str(ready.get("message") or "网页暂未就绪，问题未发送"))
        fresh_chat = self._start_fresh_chat()
        self._ensure_search_enabled()
        baseline = self._snapshot()
        baseline_body = str(baseline.get("body") or "")
        # Monitor the actual customer question, without requesting links or
        # adding identifiers. A verified fresh chat separates repeated rounds.
        wire = question
        self._submit(wire)
        last = self._wait_answer_with_refresh(
            wire,
            timeout=timeout,
            stable_seconds=stable_seconds,
            baseline_body=baseline_body,
        )
        return self._finish_capture(question,last,fresh_chat,stable_seconds=stable_seconds)

    def resume(self,question,url,*,timeout=240,stable_seconds=6):
        """Read the exact original conversation; this method has no send path."""
        identity=conversation_id(url)
        if not identity:raise RuntimeError('Original conversation identity unavailable')
        self.submission_started=True
        self.page.call('Page.navigate',{'url':url},timeout=30)
        time.sleep(5)
        # Navigation returns before the composer mounts. Observe the original
        # page until ready; a loading page is not an authentication failure.
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=self.session_status()
            if state.get('status')=='login_required':
                self.session_reporter.publish(state)
                raise LoginRequiredError(state['message'])
            if state.get('ok'):
                self.session_reporter.publish(state)
                self._next_session_check=time.monotonic()+60
                break
            time.sleep(0.5)
        else:raise TimeoutError('Original conversation page did not become ready')
        last=self._wait_answer_with_refresh(question,timeout=timeout,stable_seconds=stable_seconds)
        if conversation_id(last.get('url'))!=identity:raise RuntimeError('Original conversation changed')
        result=self._finish_capture(question,last,{'recovered_original_conversation':url},stable_seconds=stable_seconds)
        if conversation_id(result['url'])!=identity:raise RuntimeError('Recovered answer identity changed')
        return result

    def _finish_capture(self,question,last,fresh_chat,*,stable_seconds=6):
        expected = self._expand_source_panel()
        # Give lazily rendered references time to settle, without treating a
        # missing source count as evidence that zero sources were expected.
        previous = None
        stable_since = time.monotonic()
        end = stable_since + 20
        while time.monotonic() < end:
            self._probe_session_if_due()
            current = self._snapshot()
            signature = json.dumps(
                [current.get("body"), current.get("sources")],
                ensure_ascii=False,
                sort_keys=True,
            )
            if signature != previous:
                stable_since = time.monotonic()
            previous = signature
            last = current
            if (
                not current.get("busy")
                and time.monotonic() - stable_since >= stable_seconds
            ):
                break
            time.sleep(1)
        else:
            raise TimeoutError("Answer/source panel did not settle")
        last["expected_source_count"] = expected
        result = self._capture_result(last, question)
        current_id = conversation_id(result["url"])
        used_ids = getattr(self, "_used_conversation_ids", set())
        if not current_id or current_id in used_ids:
            raise RuntimeError(
                "DeepSeek conversation identity is missing or reused; refusing mixed answers"
            )
        used_ids.add(current_id)
        self._used_conversation_ids = used_ids
        result["conversation_id"] = current_id
        result["fresh_conversation"] = fresh_chat
        result["wire_question"] = question
        result["search_enabled"] = True
        return result


def create_collector(model: str, *, headless: bool = True):
    return BrowserCollector(model, headless=headless)
