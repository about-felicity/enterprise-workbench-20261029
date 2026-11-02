"""Produce a salted password verifier from stdin; never print the credential."""
import hashlib,secrets,sys,tempfile
from pathlib import Path
password=sys.stdin.readline().rstrip('\r\n')
if not password:raise SystemExit('Password input required')
salt=secrets.token_bytes(16);iterations=600000
digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,iterations).hex()
path=Path(tempfile.gettempdir())/'geo-performance-superadmin-20261031.verifier'
path.write_text('pbkdf2_sha256$'+str(iterations)+'$'+salt.hex()+'$'+digest,encoding='ascii')
print('Generated salted verifier in temporary storage; password not saved')
