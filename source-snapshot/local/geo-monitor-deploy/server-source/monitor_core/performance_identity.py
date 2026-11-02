"""Verify short-lived performance identity asserted by the public login gateway."""
import base64,hashlib,hmac,json,os,time
from http.cookies import SimpleCookie
from pathlib import Path

def key():
    return Path(os.environ.get('MONITOR_PERFORMANCE_AUTH_KEY',str(Path(__file__).resolve().parents[1]/'secrets/performance-auth.key'))).read_bytes()

def session_hash(headers):
    jar=SimpleCookie(headers.get('Cookie',''));session=jar.get('geo_monitor_session')
    if not session or not session.value:raise PermissionError('请从公网主站登录后操作')
    return hashlib.sha256(session.value.encode()).hexdigest()

def identity(headers,*,now=None):
    now=time.time() if now is None else now
    try:
        proof=headers.get('X-Geo-Performance-Identity','')
        if len(proof)>2048:raise ValueError('oversized')
        encoded,signature=proof.split('.',1)
        expected=base64.urlsafe_b64encode(hmac.new(key(),b'performance-v1:'+encoded.encode(),hashlib.sha256).digest()).decode().rstrip('=')
        if not hmac.compare_digest(signature,expected):raise ValueError('signature')
        payload=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if type(payload.get('e')) is not int or not now<=payload['e']<=now+90:raise ValueError('expired')
        if not hmac.compare_digest(str(payload.get('s','')),session_hash(headers)):raise ValueError('session')
        username=payload.get('u')
        if not isinstance(username,str) or not username or len(username)>64:raise ValueError('username')
        return username
    except (ValueError,TypeError,KeyError,OSError):raise PermissionError('登录身份校验失败，请从公网主站重新登录') from None

def csrf(headers):
    return hmac.new(key(),('performance-csrf-v1:'+session_hash(headers)).encode(),hashlib.sha256).hexdigest()

def authorize_write(headers):
    user=identity(headers)
    if user!='superadmin':raise PermissionError('仅superadmin可以录入绩效数据')
    authorize_session_write(headers)
    return user

def authorize_session_write(headers):
    user=identity(headers)
    if headers.get('Origin')!='https://1any.top' or headers.get('Sec-Fetch-Site') not in (None,'','same-origin'):
        raise PermissionError('请求来源校验失败，请从公网主站填写')
    if not hmac.compare_digest(headers.get('X-CSRF-Token',''),csrf(headers)):
        raise PermissionError('页面校验已失效，请重新载入后保存')
    return user
