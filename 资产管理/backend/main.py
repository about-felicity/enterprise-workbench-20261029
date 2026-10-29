from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os

from database import engine, get_db, Base
from models import User, Employee, Device, Assignment, DeviceStatus, DeviceType
from schemas import DashboardStats, AssignmentOut, DeviceOut
from auth import hash_password, get_current_user
from routers import auth, employees, devices, assignments, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield


app = FastAPI(title="企业资产管理系统", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(devices.router)
app.include_router(assignments.router)
app.include_router(export.router)


def seed_data():
    db = next(get_db())
    try:
        if db.query(User).filter(User.role == "admin").first():
            return

        # Create admin
        admin_emp = Employee(name="系统管理员", phone="13800000000", department="技术部", position="管理员")
        db.add(admin_emp)
        db.flush()

        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=1,
            can_register=1,
            employee_id=admin_emp.id,
        )
        db.add(admin)

        # Create demo employee
        demo_emp = Employee(name="张三", phone="13900001111", department="研发部", position="工程师")
        db.add(demo_emp)
        db.flush()

        demo_user = User(
            username="zhangsan",
            password_hash=hash_password("123456"),
            role="employee",
            is_active=1,
            can_register=0,
            employee_id=demo_emp.id,
        )
        db.add(demo_user)

        # Create demo devices
        devices_data = [
            Device(device_code="PC-001", device_type=DeviceType.DESKTOP.value, brand="Dell", model="OptiPlex 7080", specs="i7-10700/16GB/512GB SSD", status=DeviceStatus.IDLE.value, purchase_date="2024-01-15"),
            Device(device_code="PC-002", device_type=DeviceType.LAPTOP.value, brand="ThinkPad", model="X1 Carbon Gen9", specs="i7-1165G7/16GB/512GB SSD", status=DeviceStatus.IDLE.value, purchase_date="2024-02-20"),
            Device(device_code="MN-001", device_type=DeviceType.MONITOR.value, brand="Dell", model="U2723QE", specs="27英寸 4K IPS", status=DeviceStatus.IDLE.value, purchase_date="2024-01-15"),
            Device(device_code="MN-002", device_type=DeviceType.MONITOR.value, brand="LG", model="27UP850N", specs="27英寸 4K IPS", status=DeviceStatus.IDLE.value, purchase_date="2024-03-10"),
            Device(device_code="PR-001", device_type=DeviceType.PRINTER.value, brand="HP", model="LaserJet Pro M404dn", specs="黑白激光打印机", status=DeviceStatus.IDLE.value, purchase_date="2024-01-20"),
        ]
        for d in devices_data:
            db.add(d)

        db.commit()
        print("[系统] 初始化数据创建完成")
        print("[系统] 管理员账号: admin / admin123")
        print("[系统] 员工账号: zhangsan / 123456")
    finally:
        db.close()


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_devices = db.query(Device).count()
    idle_devices = db.query(Device).filter(Device.status == DeviceStatus.IDLE.value).count()
    in_use_devices = db.query(Device).filter(Device.status == DeviceStatus.IN_USE.value).count()
    repairing_devices = db.query(Device).filter(Device.status == DeviceStatus.REPAIRING.value).count()
    scrapped_devices = db.query(Device).filter(Device.status == DeviceStatus.SCRAPPED.value).count()
    total_employees = db.query(Employee).count()
    active_employees = db.query(Employee).filter(Employee.status == "在职").count()

    recent = (
        db.query(Assignment)
        .order_by(Assignment.assigned_at.desc())
        .limit(10)
        .all()
    )
    recent_out = []
    for a in recent:
        device = db.query(Device).filter(Device.id == a.device_id).first()
        employee = db.query(Employee).filter(Employee.id == a.employee_id).first()
        assigner = db.query(User).filter(User.id == a.assigned_by).first()
        recent_out.append(
            AssignmentOut(
                id=a.id, device_id=a.device_id, employee_id=a.employee_id,
                assigned_by=a.assigned_by, event_type=a.event_type, notes=a.notes,
                assigned_at=a.assigned_at, returned_at=a.returned_at,
                device_code=device.device_code if device else None,
                device_type=device.device_type if device else None,
                employee_name=employee.name if employee else None,
                assigner_name=assigner.username if assigner else None,
            )
        )

    # Device type distribution
    type_dist = {}
    for dt in DeviceType:
        count = db.query(Device).filter(Device.device_type == dt.value).count()
        type_dist[dt.value] = count

    return DashboardStats(
        total_devices=total_devices,
        idle_devices=idle_devices,
        in_use_devices=in_use_devices,
        repairing_devices=repairing_devices,
        scrapped_devices=scrapped_devices,
        total_employees=total_employees,
        active_employees=active_employees,
        recent_assignments=recent_out,
        device_type_distribution=type_dist,
    )


# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
