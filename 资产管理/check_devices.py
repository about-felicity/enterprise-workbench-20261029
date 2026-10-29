import sys
sys.path.insert(0, 'backend')
from database import SessionLocal
from models import User, Employee, Device, Assignment

db = SessionLocal()

# 查 1any 关联的员工
u = db.query(User).filter(User.username == '1any').first()
if u:
    emp = db.query(Employee).filter(Employee.id == u.employee_id).first()
    print(f"1any → employee_id={u.employee_id}, 姓名={emp.name if emp else '?'}")
else:
    print("1any 不存在！")

# 查这个设备
d = db.query(Device).filter(Device.device_code == '9860BED5-2417-48B9-82FE-DEC63543B5E6').first()
if d:
    print(f"\n设备: {d.device_code} | 类型={d.device_type} | 状态={d.status}")
    # 查分配记录
    for a in db.query(Assignment).filter(Assignment.device_id == d.id).all():
        emp = db.query(Employee).filter(Employee.id == a.employee_id).first()
        print(f"  分配记录: 分配给={emp.name if emp else '?'}(ID={a.employee_id}) | 类型={a.event_type} | 归还={a.returned_at}")
else:
    print("\n设备不存在！")

db.close()
