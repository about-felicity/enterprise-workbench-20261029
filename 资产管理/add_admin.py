import sys
sys.path.insert(0, r'c:\Users\AMD\Desktop\资产管理\backend')
from database import SessionLocal
from models import User, Employee
from auth import hash_password

db = SessionLocal()

# 恢复 1any
if not db.query(User).filter(User.username == '1any').first():
    emp = Employee(name='一安', phone='', department='管理部', position='系统管理员')
    db.add(emp)
    db.flush()
    user = User(username='1any', password_hash=hash_password('REDACTED_CONFIGURE_LOCALLY'),
                role='admin', is_active=1, can_register=1, employee_id=emp.id)
    db.add(user)
    db.commit()
    print('1any 已恢复')

print('\n=== 当前用户 ===')
for u in db.query(User).all():
    emp = db.query(Employee).filter(Employee.id == u.employee_id).first()
    print(f"  {u.username} | {u.role} | {emp.name if emp else '?'}")

db.close()
