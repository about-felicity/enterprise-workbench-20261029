"""Deny every outbound socket and unmocked HTTP call in replay processes."""
import os,socket
blocked=[]
connect=socket.socket.connect
connect_ex=socket.socket.connect_ex
create=socket.create_connection
def deny(*args,**kwargs):
 blocked.append('network_attempt')
 raise AssertionError('OFFLINE VALIDATION: network access forbidden')
def local(address):return os.environ.get('GEO_OFFLINE_ALLOW_LOOPBACK')=='1' and isinstance(address,tuple) and address[0] in {'127.0.0.1','::1'}
def guarded_connect(self,address):return connect(self,address) if local(address) else deny()
def guarded_connect_ex(self,address):return connect_ex(self,address) if local(address) else deny()
def guarded_create(address,*args,**kwargs):return create(address,*args,**kwargs) if local(address) else deny()
socket.socket.connect=guarded_connect
socket.socket.connect_ex=guarded_connect_ex
socket.create_connection=guarded_create
try:
 import requests
 requests.sessions.Session.request=deny
except ImportError:pass
