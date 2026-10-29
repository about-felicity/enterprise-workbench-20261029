() => {
  const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
  const composer=Array.from(document.querySelectorAll('textarea,[contenteditable=true]')).some(visible);
  const path=location.pathname;
  const login=/^\/(?:sign_in|login)(?:\/|$)/.test(path)||Array.from(document.querySelectorAll('input')).some(e=>visible(e)&&/手机号|手机号码|验证码|phone number|verification code/i.test(e.placeholder||''));
  const riskPattern=/因违反用户使用规范|账号.{0,20}(已被禁言|已被封禁|禁止使用)|账户.{0,20}(已被禁言|已被封禁)|操作频繁|异常请求|安全验证|verify you are human/i;
  const risk=Array.from(document.querySelectorAll('[role=alert],[role=dialog],.ds-toast,.ds-modal')).some(e=>visible(e)&&riskPattern.test(e.innerText||''))||
    Array.from(document.querySelectorAll('p,span,div')).some(e=>visible(e)&&!e.children.length&&!e.closest('.ds-assistant-message-main-content,.ds-message,[data-message-id],[data-role=assistant]')&&(e.innerText||'').length<220&&/因违反用户使用规范|账号已被禁言|账号已被封禁/.test(e.innerText||''))||
    (!composer&&/Just a moment|请稍候|Security Verification|安全验证/i.test(document.title));
  return {login,risk,composer,title:document.title};
}
