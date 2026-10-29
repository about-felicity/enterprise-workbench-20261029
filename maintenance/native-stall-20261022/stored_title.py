import sys,json,sqlite3
sys.path[:0]=['/home/user/redroid-yuanbao']
from native_storage import databases,open_readonly,app_directory
out=[]
for path in databases():
 with open_readonly(path) as db:
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table' and (lower(name) like '%conv%' or lower(name) like '%session%')")]
  row=db.execute('select conversation_id,title from ChatConversationDetail where conversation_id=?',('0RRX0UA4Ogq',)).fetchone()
  out.append({'path':str(path),'tables':tables,'row':dict(row) if row else None,'recent':[dict(r) for r in db.execute('select conversation_id,title from ChatConversationDetail limit 5')]})
print(json.dumps(out,ensure_ascii=False))
for path in app_directory().glob('files/dtmp/Users/*/Database/history_conversation.db'):
 with open_readonly(path) as db:
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
  row=db.execute('select id,title,deleted_at,last_replied_at from conversation_list where id=?',('0RRX0UA4Ogq',)).fetchone()
  print(json.dumps({'path':str(path),'row':dict(row) if row else None,'duplicate_titles':db.execute('select count(*) from conversation_list where title=?',(row['title'],)).fetchone()[0] if row else None},ensure_ascii=False))
