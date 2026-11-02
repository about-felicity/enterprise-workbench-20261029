"""GEO gateway identity assertions for the performance input API only."""
import base64,hashlib,hmac,json,time
from http.cookies import SimpleCookie
from pathlib import Path

KEY_FILE=Path('/opt/geo-monitor-auth/performance-auth.key')

def respond(handler,username):
    jar=SimpleCookie(handler.headers.get('Cookie',''));session=jar.get('geo_monitor_session')
    if not session:
        handler.send_response(401);handler.send_header('Content-Length','0');handler.end_headers();return
    value={'u':username,'e':int(time.time())+60,'s':hashlib.sha256(session.value.encode()).hexdigest()}
    encoded=base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')
    signature=base64.urlsafe_b64encode(hmac.new(KEY_FILE.read_bytes(),b'performance-v1:'+encoded.encode(),hashlib.sha256).digest()).decode().rstrip('=')
    handler.send_response(204)
    handler.send_header('X-Geo-Performance-Identity',encoded+'.'+signature)
    handler.send_header('Cache-Control','no-store');handler.send_header('Content-Length','0');handler.end_headers()

def verify_password(digest,password):
    try:
        method,iterations,salt,expected=digest.split('$')
        rounds=int(iterations)
        if method!='pbkdf2_sha256' or not 100000<=rounds<=2000000:return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),rounds).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError):return False
