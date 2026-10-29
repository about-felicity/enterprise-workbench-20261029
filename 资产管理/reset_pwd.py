import sys
sys.path.insert(0, 'backend')
from database import SessionLocal
from models import User, Employee
from auth import hash_password

db = SessionLocal()

# 确保 zhizhi 存在
u = db.query(User).filter(User.username == 'zhizhi').first()
if not u:
    emp = Employee(name='知知', phone='', department='管理部', position='系统管理员')
    db.add(emp)
    db.flush()
    u = User(username='zhizhi', password_hash=hash_password('REDACTED_CONFIGURE_LOCALLY'),
             role='admin', is_active=1, can_register=1, employee_id=emp.id)
    db.add(u)
    db.commit()
    print('zhizhi 已重新创建，密码: REDACTED_CONFIGURE_LOCALLY')
else:
    u.password_hash = hash_password('REDACTED_CONFIGURE_LOCALLY')
    db.commit()
    print('zhizhi 密码已重置为: REDACTED_CONFIGURE_LOCALLY')

# 重置 1any 密码
u2 = db.query(User).filter(User.username == '1any').first()
if u2:
    u2.password_hash = hash_password('REDACTED_CONFIGURE_LOCALLY')
    db.commit()
    print('1any 密码已重置为: REDACTED_CONFIGURE_LOCALLY')

print()
print('=== 当前所有用户 ===')
for user in db.query(User).all():
    emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
    print(f"  {user.username} | 角色={user.role} | 姓名={emp.name if emp else '?'} | 密码=REDACTED_CONFIGURE_LOCALLY" if user.role=='admin' else f"  {user.username} | 角色={user.role}")

db.close()
