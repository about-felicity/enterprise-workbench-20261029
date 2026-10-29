import sqlite3,json
p='/home/user/redroid-doubao/hpe14-acceptance/tasks.sqlite';db=sqlite3.connect(p);db.row_factory=sqlite3.Row
for r in db.execute("select task_id,event,detail,time from events where event='send_uncertain'"):
 print(json.dumps(dict(r)))
