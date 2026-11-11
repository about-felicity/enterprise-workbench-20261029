"""Add scoped employee-video accounts to the existing workbench edge auth service."""

import sys
from pathlib import Path


def update(source: str) -> str:
    replacements = (
        ('import json\n', 'import json\nimport re\n'),
        ('USERS_FILE = Path("/etc/geo-ifbcy-edge/users")', '''USERS_FILE = Path("/etc/geo-ifbcy-edge/users")
VIDEO_STAFF_FILE = Path("/etc/geo-ifbcy-edge/video-staff")
VIDEO_STAFF_HOME = "/geo_monitor/employee-videos"
VIDEO_STAFF_API = "/geo_monitor/api/geo-capture/employee-videos"'''),
        ('''def users():
    result = {}
    for line in USERS_FILE.read_text(encoding="utf-8").splitlines():''', '''def users(path=USERS_FILE):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        if path == VIDEO_STAFF_FILE:
            return {}
        raise
    result = {}
    for line in lines:'''),
        ('    digest = users().get(username, "")',
         '    digest = users().get(username) or users(VIDEO_STAFF_FILE).get(username, "")'),
        ('''        return read_token(morsel.value) if morsel else None''', '''        username = read_token(morsel.value) if morsel else None
        if username and (username in users() or username in users(VIDEO_STAFF_FILE)):
            return username
        return None'''),
        ('''            self.send_response(204)
            self.send_header("X-Geo-User", username)''', '''            if username in users(VIDEO_STAFF_FILE):
                requested = self.headers.get("X-Original-URI", "").split("?", 1)[0]
                allowed = {"/geo_monitor", "/geo_monitor/", VIDEO_STAFF_HOME, VIDEO_STAFF_HOME + "/", VIDEO_STAFF_API,
                           "/geo_monitor/workbench-theme.css"}
                static = re.fullmatch(r"/geo_monitor/assets/[a-zA-Z0-9_.-]+\.(?:css|js|woff2?|png|svg)", requested)
                if requested not in allowed and not static:
                    self.send_response(403); self.end_headers(); return
            self.send_response(204)
            self.send_header("X-Geo-Video-Only", "1" if username in users(VIDEO_STAFF_FILE) else "0")
            self.send_header("X-Geo-User", username)'''),
        ('''            if self.session_user():
                self.redirect(safe_next(urllib.parse.parse_qs(parsed.query).get("next", [""])[0])); return''', '''            username = self.session_user()
            if username:
                target = safe_next(urllib.parse.parse_qs(parsed.query).get("next", [""])[0])
                self.redirect(VIDEO_STAFF_HOME if username in users(VIDEO_STAFF_FILE) else target); return'''),
        ('''        self.redirect(target, cookie)''', '''        self.redirect(VIDEO_STAFF_HOME if username in users(VIDEO_STAFF_FILE) else target, cookie)'''),
    )
    for original, replacement in replacements:
        if source.count(original) != 1:
            raise ValueError(f"Auth source did not match expected anchor {original.splitlines()[0]!r}")
        source = source.replace(original, replacement, 1)
    compile(source, "auth.py", "exec")
    return source


if __name__ == "__main__":
    auth = Path(sys.argv[1]).read_text(encoding="utf-8")
    sys.stdout.buffer.write(update(auth).encode("utf-8"))
