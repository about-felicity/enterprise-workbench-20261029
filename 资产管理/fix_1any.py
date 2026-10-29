import sys
sys.path.insert(0, 'backend')
from database import SessionLocal
from models import User, Employee, Device, Assignment
from auth import hash_password
from datetime import datetime

db = SessionLocal()

# 检查 1any
u = db.query(User).filter(User.username == '1any').first()
if not u:
    print("1any 不存在，重新创建...")
    emp = Employee(name='一安', phone='13800000001', department='管理部', position='系统管理员')
    db.add(emp)
    db.flush()
    u = User(username='1any', password_hash=hash_password('REDACTED_CONFIGURE_LOCALLY'),
             role='admin', is_active=1, can_register=1, employee_id=emp.id)
    db.add(u)
    db.commit()
    print("1any 已创建，密码: REDACTED_CONFIGURE_LOCALLY")
else:
    print(f"1any 存在: employee_id={u.employee_id}")

# 把 9860BED5-2417-48B9-82FE-DEC63543B5E6 分配给 1any
d = db.query(Device).filter(Device.device_code == '9860BED5-2417-48B9-82FE-DEC63543B5E6').first()
if d and d.status == '空闲':
    # 先检查是否已有活跃分配
    active = db.query(Assignment).filter(
        Assignment.device_id == d.id,
        Assignment.returned_at.is_(None)
    ).first()
    if not active:
        a = Assignment(
            device_id=d.id,
            employee_id=u.employee_id,
            assigned_by=u.id,
            event_type='分配',
            notes='补充分配'
        )
        db.add(a)
        d.status = '使用中'
        db.commit()
        print(f"设备 {d.device_code} 已分配给 1any")
    else:
        print("设备已有活跃分配")
else:
    print("设备不存在或非空闲状态")

# 同时把其他空闲设备也分配给 1any
for dev in db.query(Device).filter(Device.status == '空闲').all():
    active = db.query(Assignment).filter(
        Assignment.device_id == dev.id,
        Assignment.returned_at.is_(None)
    ).first()
    if not active:
        a = Assignment(
            device_id=dev.id,
            employee_id=u.employee_id,
            assigned_by=u.id,
            event_type='分配',
            notes='补充分配'
        )
        db.add(a)
        dev.status = '使用中'
        db.commit()
        print(f"设备 {dev.device_code} 已分配给 1any")

print("\n=== 1any 当前持有设备 ===")
for a in db.query(Assignment).filter(
    Assignment.employee_id == u.employee_id,
    Assignment.returned_at.is_(None)
).all():
    dev = db.query(Device).filter(Device.id == a.device_id).first()
    if dev:
        print(f"  {dev.device_code} | {dev.device_type} | {dev.brand} {dev.model}")

db.close()
